import os
import json
from maya import cmds
from avalon import api
from avalon.vendor import requests
import pyblish.api
import pype.maya.lib as lib
import appdirs
import platform
# from pypeapp.lib.config import get_presets

from pprint import pprint


def get_renderer_variables(renderlayer=None):
    """Retrieve the extension which has been set in the VRay settings

    Will return None if the current renderer is not VRay
    For Maya 2016.5 and up the renderSetup creates renderSetupLayer node which
    start with `rs`. Use the actual node name, do NOT use the `nice name`

    Args:
        renderlayer (str): the node name of the renderlayer.

    Returns:
        dict
    """

    renderer = lib.get_renderer(renderlayer or lib.get_current_renderlayer())
    render_attrs = lib.RENDER_ATTRS.get(renderer, lib.RENDER_ATTRS["default"])

    padding = cmds.getAttr("{}.{}".format(render_attrs["node"],
                                          render_attrs["padding"]))

    filename_0 = cmds.renderSettings(fullPath=True, firstImageName=True)[0]

    if renderer == "vray":
        # Maya's renderSettings function does not return V-Ray file extension
        # so we get the extension from vraySettings
        extension = cmds.getAttr("vraySettings.imageFormatStr")

        # When V-Ray image format has not been switched once from default .png
        # the getAttr command above returns None. As such we explicitly set
        # it to `.png`
        if extension is None:
            extension = "png"

        filename_prefix = "<Scene>/<Scene>_<Layer>/<Layer>"
    else:
        # Get the extension, getAttr defaultRenderGlobals.imageFormat
        # returns an index number.
        filename_base = os.path.basename(filename_0)
        extension = os.path.splitext(filename_base)[-1].strip(".")
        filename_prefix = "<Scene>/<RenderLayer>/<RenderLayer>"

    return {"ext": extension,
            "filename_prefix": filename_prefix,
            "padding": padding,
            "filename_0": filename_0}


def preview_fname(folder, scene, layer, padding, ext):
    """Return output file path with #### for padding.

    Deadline requires the path to be formatted with # in place of numbers.
    For example `/path/to/render.####.png`

    Args:
        folder (str): The root output folder (image path)
        scene (str): The scene name
        layer (str): The layer name to be rendered
        padding (int): The padding length
        ext(str): The output file extension

    Returns:
        str

    """

    # Following hardcoded "<Scene>/<Scene>_<Layer>/<Layer>"
    output = "{scene}/{layer}/{layer}.{number}.{ext}".format(
        scene=scene,
        layer=layer,
        number="#" * padding,
        ext=ext
    )

    return os.path.join(folder, output)


class MayaSubmitMuster(pyblish.api.InstancePlugin):
    """Submit available render layers to Muster

    Renders are submitted to a Muster via HTTP API as
    supplied via the environment variable ``MUSTER_REST_URL``.

    Also needed is ``MUSTER_USER`` and ``MUSTER_PASSWORD``.
    """

    label = "Submit to Muster"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["maya"]
    families = ["renderlayer"]
    optional = True
    icon = "satellite-dish"

    _token = None
    _user = None
    _password = None

    def _load_credentials(self):
        """
        Load Muster credentials from file and set `MUSTER_USER`,
        `MUSTER_PASSWORD`, `MUSTER_REST_URL` is loaded from presets.
        """
        app_dir = os.path.normpath(
            appdirs.user_data_dir('pype-app', 'pype')
        )
        file_name = 'muster_cred.json'
        fpath = os.path.join(app_dir, file_name)
        file = open(fpath, 'r')
        muster_json = json.load(file)
        self.MUSTER_USER = muster_json.get('username', None)
        self.MUSTER_PASSWORD = muster_json.get('password', None)
        file.close()
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not self.MUSTER_REST_URL:
            raise Exception("Muster REST API url not set")

    def _authenticate(self):
        """
        Authenticate user with Muster and get authToken from server.
        """
        params = {
                    'username': self.MUSTER_USER,
                    'password': self.MUSTER_PASSWORD
               }
        api_entry = '/api/login'
        response = requests.post(
            self.MUSTER_REST_URL + api_entry, params=params)
        if response.status_code != 200:
            self.log.error(
                'Cannot log into Muster: {}'.format(response.status_code))
            raise Exception('Cannot login into Muster.')

        try:
            self._token = response.json()['ResponseData']['authToken']
        except ValueError as e:
            self.log.error('Invalid response from Muster server {}'.format(e))
            raise Exception('Invalid response from Muster while logging in.')

        return self._token

    def _get_templates(self):
        """
        Get Muster templates from server.
        """
        params = {
            "authToken": self._token,
            "select": "name"
        }
        api_entry = '/api/templates/list'
        response = requests.post(
            self.MUSTER_REST_URL + api_entry, params=params)
        if response.status_code != 200:
            self.log.error(
                'Cannot get templates from Muster: {}'.format(
                    response.status_code))
            raise Exception('Cannot get templates from Muster.')

        try:
            response_templates = response.json()["ResponseData"]["templates"]
        except ValueError as e:
            self.log.error(
                'Muster server returned unexpected data {}'.format(e)
            )
            raise Exception('Muster server returned unexpected data')

        templates = {}
        for t in response_templates:
            templates[t.get("name")] = t.get("id")

        self._templates = templates

    def _resolve_template(self, renderer):
        """
        Returns template ID based on renderer string.

        :param renderer: Name of renderer to match against template names
        :type renderer: str
        :returns: ID of template
        :rtype: int
        :raises: Exception if template ID isn't found
        """
        try:
            self.log.info("Trying to find template for [{}]".format(renderer))
            return self._templates.get(renderer)
        except ValueError:
            raise Exception('Unimplemented renderer {}'.format(renderer))

    def _submit(self, payload):
        """
        Submit job to Muster

        :param payload: json with job to submit
        :type payload: str
        :returns: response
        :raises: Exception status is wrong
        """
        params = {
            "authToken": self._token,
            "name": "submit"
        }
        api_entry = '/api/queue/actions'
        response = requests.post(
            self.MUSTER_REST_URL + api_entry, params=params, json=payload)

        if response.status_code != 200:
            self.log.error(
                'Cannot submit job to Muster: {}'.format(response.text))
            raise Exception('Cannot submit job to Muster.')

        return response

    def process(self, instance):
        """
        Authenticate with Muster, collect all data, prepare path for post
        render publish job and submit job to farm.
        """
        # setup muster environment
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL",
                                              "https://localhost:9891")
        self._load_credentials()
        self._authenticate()
        self._get_templates()

        context = instance.context
        workspace = context.data["workspaceDir"]

        filepath = None

        allInstances = []
        for result in context.data["results"]:
            if ((result["instance"] is not None) and
               (result["instance"] not in allInstances)):
                allInstances.append(result["instance"])

        for inst in allInstances:
            print(inst)
            if inst.data['family'] == 'scene':
                filepath = inst.data['destination_list'][0]

        if not filepath:
            filepath = context.data["currentFile"]

        self.log.debug(filepath)

        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        scene = os.path.splitext(filename)[0]
        dirname = os.path.join(workspace, "renders")
        renderlayer = instance.data['setMembers']       # rs_beauty
        renderlayer_name = instance.data['subset']      # beauty
        renderlayer_globals = instance.data["renderGlobals"]
        legacy_layers = renderlayer_globals["UseLegacyRenderLayers"]
        # deadline_user = context.data.get("deadlineUser", getpass.getuser())
        jobname = "%s - %s" % (filename, instance.name)

        # Get the variables depending on the renderer
        render_variables = get_renderer_variables(renderlayer)
        output_filename_0 = preview_fname(folder=dirname,
                                          scene=scene,
                                          layer=renderlayer_name,
                                          padding=render_variables["padding"],
                                          ext=render_variables["ext"])

        instance.data["outputDir"] = os.path.dirname(output_filename_0)
        # build path for metadata file
        metadata_filename = "{}_metadata.json".format(instance.data["subset"])
        output_dir = instance.data["outputDir"]
        metadata_path = os.path.join(output_dir, metadata_filename)

        # TODO: set correct path
        pype_command = "pype.bat"
        if platform.system().lower() == "linux":
            pype_command = "pype"
        postjob_command = "{} --publish --paths {}".format(
            os.path.join(os.environ.get('PYPE_ROOT'), pype_command),
            metadata_path
            )

        try:
            # Ensure render folder exists
            os.makedirs(dirname)
        except OSError:
            pass

        env = self.clean_environment()

        payload = {
            "RequestData": {
                "platform": 0,
                "job": {
                    "jobName": jobname,
                    "templateId": self._resolve_template(
                        instance.data["renderer"]),
                    "camera": "",
                    "chunksInterleave": 2,
                    "chunksPriority": "0",
                    "chunksTimeoutValue": 320,
                    "department": "",
                    "dependIds": [""],
                    "dependLinkMode": 0,
                    "dependMode": 0,
                    "emergencyQueue": False,
                    "excludedPools": [""],
                    "exitCodesErrorCheckType": 0,
                    "includedPools": [""],
                    "logsErrorCheckType": 0,
                    "mailNotificationsAtChunkLevelType": "1",
                    "mailNotificationsAtJobLevelType": "1",
                    "maximumInstances": 0,
                    "mobileNotificationsAtChunkLevelType": "1",
                    "mobileNotificationsAtJobLevelType": "1",
                    "notificatorNotificationsAtChunkLevelType": "1",
                    "notificatorNotificationsAtJobLevelType": "1",
                    "overrideChunksTimeout": False,
                    "overrideErrorExitCodes": False,
                    "overrideErrorExitCodesValue": "",
                    "overrideMailNotificationsAtChunkLevel": False,
                    "overrideMailNotificationsAtJobLevel": False,
                    "overrideMaximumChunksRequeue": False,
                    "overrideMaximumChunksRequeueValue": 0,
                    "overrideMinimumCores": False,
                    "overrideMinimumCoresValue": 0,
                    "overrideMinimumDiskSpace": False,
                    "overrideMinimumDiskSpaceValue": 0,
                    "overrideMinimumPhysical": False,
                    "overrideMinimumPhysicalValue": 0,
                    "overrideMinimumRam": False,
                    "overrideMinimumRamValue": 0,
                    "overrideMinimumSpeed": False,
                    "overrideMinimumSpeedValue": 0,
                    "overrideMinimumThreads": False,
                    "overrideMinimumThreadsValue": 0,
                    "overrideMobileNotificationsAtChunkLevel": False,
                    "overrideMobileNotificationsAtJobLevel": False,
                    "overrideNotificatorNotificationsAtChunkLevel": False,
                    "overrideNotificatorNotificationsAtJobLevel": False,
                    "overrideStartMailNotificationsAtChunkLevel": False,
                    "overrideStartMailNotificationsAtJobLevel": False,
                    "overrideStartMobileNotificationsAtChunkLevel": False,
                    "overrideStartMobileNotificationsAtJobLevel": False,
                    "overrideStartNotificatorNotificationsAtChunkLevel": False,
                    "overrideStartNotificatorNotificationsAtJobLevel": False,
                    "overrideValidExitCodes": False,
                    "overrideValidExitCodesValue": "",
                    "overrideWarningExitCodes": False,
                    "overrideWarningExitCodesValue": "",
                    "packetSize": 4,
                    "packetType": 1,
                    "priority": 1,
                    "project": "test",
                    "sequence": "",
                    "shot": "",
                    "startMailNotificationsAtChunkLevelType": "1",
                    "startMailNotificationsAtJobLevelType": "1",
                    "startMobileNotificationsAtChunkLevelType": "1",
                    "startMobileNotificationsAtJobLevelType": "1",
                    "startNotificatorNotificationsAtChunkLevelType": "1",
                    "startNotificatorNotificationsAtJobLevelType": "1",
                    "startOn": 0,
                    "templateVersion": "",

                    "jobId": -1,
                    "startOn": 0,
                    "parentId": -1,
                    "dependMode": 0,
                    "packetSize": 4,
                    "packetType": 1,
                    "priority": 1,
                    "maximumInstances": 0,
                    "assignedInstances": 0,
                    "attributes": {
                        # "environmental_variables": {
                        #     "value": ", ".join("{!s}={!r}".format(k, v)
                        #                        for (k, v) in env.iteritems())
                        # },
                        "memo": {
                            "value": comment,
                            "state": True,
                            "subst": False
                        },
                        "frames_range": {
                            "value": "{start}-{end}".format(
                                start=int(instance.data["startFrame"]),
                                end=int(instance.data["endFrame"])),
                            "state": True,
                            "subst": False
                        },
                        "job_file": {
                            "value": filepath,
                            "state": True,
                            "subst": True
                        },
                        "output_folder": {
                            "value": dirname.replace("\\", "/"),
                            "state": True,
                            "subst": True
                        },
                        "post_job_action": {
                            "value": postjob_command,
                            "state": True,
                            "subst": True
                        },
                        "overridestatus": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "frame_check": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "fc_recursion": {
                          "value": "1",
                          "state": True,
                          "subst": False
                        },
                        "fc_check_file": {
                          "value": "1",
                          "state": True,
                          "subst": False
                        },
                        "fc_file_low": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "fc_file_high": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "fc_open_image": {
                          "value": "1",
                          "state": True,
                          "subst": False
                        },
                        "fc_render_layer_mode": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "fc_check_image_dimensions": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "fc_image_width": {
                          "value": "1920",
                          "state": True,
                          "subst": False
                        },
                        "fc_image_height": {
                          "value": "1080",
                          "state": True,
                          "subst": False
                        },
                        "movie_assembler": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "movie_assembler_output": {
                          "value": "",
                          "state": True,
                          "subst": True
                        },
                        "movie_assembler_framerate": {
                          "value": "30",
                          "state": True,
                          "subst": False
                        },
                        "movie_assembler_template": {
                          "value": "48",
                          "state": True,
                          "subst": False
                        },
                        "movie_assembler_input_flags": {
                          "value": "",
                          "state": False,
                          "subst": False
                        },
                        "movie_assembler_output_flags": {
                          "value": "",
                          "state": False,
                          "subst": False
                        },
                        "pre_job_action": {
                          "value": "",
                          "state": False,
                          "subst": True
                        },
                        "pre_job_action_check_retcode": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "pre_job_action_timeout": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "post_job_action_check_retcode": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "post_job_action_timeout": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "pre_chunk_action": {
                          "value": "",
                          "state": False,
                          "subst": True
                        },
                        "pre_chunk_action_check_retcode": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "pre_chunk_action_timeout": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "post_chunk_action": {
                          "value": "",
                          "state": False,
                          "subst": True
                        },
                        "post_chunk_action_check_retcode": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "post_chunk_action_timeout": {
                          "value": 0,
                          "state": False,
                          "subst": False
                        },
                        "ARNOLDMODE": {
                          "value": "0",
                          "state": True,
                          "subst": False
                        },
                        "job_project": {
                          "value": "D:\\D001_projectx\\maya\\work",
                          "state": True,
                          "subst": True
                        },
                        "MAYADIGITS": {
                          "value": 1,
                          "state": True,
                          "subst": False
                        },
                        "ABORTRENDER": {
                          "value": "0",
                          "state": True,
                          "subst": True
                        },
                        "ARNOLDLICENSE": {
                          "value": "0",
                          "state": False,
                          "subst": False
                        },
                        "ADD_FLAGS": {
                          "value": "",
                          "state": True,
                          "subst": True
                        }
                    }
                }
            }
        }

        self.preflight_check(instance)

        self.log.info("Submitting ...")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        response = self._submit(payload)
        # response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store output dir for unified publisher (filesequence)

        instance.data["musterSubmissionJob"] = response.json()

    def clean_environment(self):
        # Include critical environment variables with submission
        keys = [
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have accesss to these paths, such as if slaves are
            # running Linux and the submitter is on Windows.
            "PYTHONPATH",
            "PATH",

            "MTOA_EXTENSIONS_PATH",
            "MTOA_EXTENSIONS",
            "DYLD_LIBRARY_PATH",
            "MAYA_RENDER_DESC_PATH",
            "MAYA_MODULE_PATH",
            "ARNOLD_PLUGIN_PATH",
            "AVALON_SCHEMA",
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "PYBLISHPLUGINPATH",

            # todo: This is a temporary fix for yeti variables
            "PEREGRINEL_LICENSE",
            "SOLIDANGLE_LICENSE",
            "ARNOLD_LICENSE"
            "MAYA_MODULE_PATH",
            "TOOL_ENV"
        ]
        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)
        # self.log.debug("enviro: {}".format(pprint(environment)))
        for path in os.environ:
            if path.lower().startswith('pype_'):
                environment[path] = os.environ[path]

        environment["PATH"] = os.environ["PATH"]
        # self.log.debug("enviro: {}".format(environment['PYPE_SCRIPTS']))
        clean_environment = {}
        for key in environment:
            clean_path = ""
            self.log.debug("key: {}".format(key))
            to_process = environment[key]
            if key == "PYPE_STUDIO_CORE_MOUNT":
                clean_path = environment[key]
            elif "://" in environment[key]:
                clean_path = environment[key]
            elif os.pathsep not in to_process:
                try:
                    path = environment[key]
                    path.decode('UTF-8', 'strict')
                    clean_path = os.path.normpath(path)
                except UnicodeDecodeError:
                    print('path contains non UTF characters')
            else:
                for path in environment[key].split(os.pathsep):
                    try:
                        path.decode('UTF-8', 'strict')
                        clean_path += os.path.normpath(path) + os.pathsep
                    except UnicodeDecodeError:
                        print('path contains non UTF characters')

            if key == "PYTHONPATH":
                clean_path = clean_path.replace('python2', 'python3')
            clean_path = clean_path.replace(
                os.path.normpath(environment['PYPE_STUDIO_CORE_MOUNT']),
                os.path.normpath(environment['PYPE_STUDIO_CORE_PATH']))
            clean_environment[key] = clean_path

        return clean_environment

    def preflight_check(self, instance):
        """Ensure the startFrame, endFrame and byFrameStep are integers"""

        for key in ("startFrame", "endFrame", "byFrameStep"):
            value = instance.data[key]

            if int(value) == value:
                continue

            self.log.warning(
                "%f=%d was rounded off to nearest integer"
                % (value, int(value))
            )
