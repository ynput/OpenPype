import os
import json
import getpass
import platform

import appdirs

from maya import cmds

from avalon import api

import pyblish.api
from openpype.lib import requests_post
from openpype.hosts.maya.api import lib
from openpype.api import get_system_settings


# mapping between Maya renderer names and Muster template ids
def _get_template_id(renderer):
    """
    Return muster template ID based on renderer name.

    :param renderer: renderer name
    :type renderer: str
    :returns: muster template id
    :rtype: int
    """

    templates = get_system_settings()["modules"]["muster"]["templates_mapping"]
    if not templates:
        raise RuntimeError(("Muster template mapping missing in "
                            "pype-settings"))
    try:
        template_id = templates[renderer]
    except KeyError:
        raise RuntimeError("Unmapped renderer - missing template id")

    return template_id


def _get_script():
    """Get path to the image sequence script"""
    try:
        from openpype.scripts import publish_filesequence
    except Exception:
        raise RuntimeError("Expected module 'publish_deadline'"
                           "to be available")

    module_path = publish_filesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[:-len(".pyc")] + ".py"

    return module_path


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
    output = "maya/{scene}/{layer}/{layer}.{number}.{ext}".format(
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
    icon = "satellite-dish"
    if not os.environ.get("MUSTER_REST_URL"):
        optional = False
        active = False
    else:
        optional = True

    _token = None

    def _load_credentials(self):
        """
        Load Muster credentials from file and set `MUSTER_USER`,
        `MUSTER_PASSWORD`, `MUSTER_REST_URL` is loaded from settings.

        .. todo::

           Show login dialog if access token is invalid or missing.
        """
        app_dir = os.path.normpath(
            appdirs.user_data_dir('pype-app', 'pype')
        )
        file_name = 'muster_cred.json'
        fpath = os.path.join(app_dir, file_name)
        file = open(fpath, 'r')
        muster_json = json.load(file)
        self._token = muster_json.get('token', None)
        if not self._token:
            raise RuntimeError("Invalid access token for Muster")
        file.close()
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")
        if not self.MUSTER_REST_URL:
            raise AttributeError("Muster REST API url not set")

    def _get_templates(self):
        """
        Get Muster templates from server.
        """
        params = {
            "authToken": self._token,
            "select": "name"
        }
        api_entry = '/api/templates/list'
        response = requests_post(
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
        self.log.info("Trying to find template for [{}]".format(renderer))
        mapped = _get_template_id(renderer)
        self.log.info("got id [{}]".format(mapped))
        return self._templates.get(mapped)

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
        response = requests_post(
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
        instance.data["toBeRenderedOn"] = "muster"
        # setup muster environment
        self.MUSTER_REST_URL = os.environ.get("MUSTER_REST_URL")

        if self.MUSTER_REST_URL is None:
            self.log.error(
                "\"MUSTER_REST_URL\" is not found. Skipping "
                "[{}]".format(instance)
            )
            raise RuntimeError("MUSTER_REST_URL not set")

        self._load_credentials()
        # self._get_templates()

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
        renderglobals = instance.data["renderGlobals"]
        # legacy_layers = renderlayer_globals["UseLegacyRenderLayers"]
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
        self.log.debug("output: {}".format(filepath))
        # build path for metadata file
        metadata_filename = "{}_metadata.json".format(instance.data["subset"])
        output_dir = instance.data["outputDir"]
        metadata_path = os.path.join(output_dir, metadata_filename)

        pype_root = os.environ["OPENPYPE_SETUP_PATH"]

        # we must provide either full path to executable or use musters own
        # python named MPython.exe, residing directly in muster bin
        # directory.
        if platform.system().lower() == "windows":
            # for muster, those backslashes must be escaped twice
            muster_python = ("\"C:\\\\Program Files\\\\Virtual Vertex\\\\"
                             "Muster 9\\\\MPython.exe\"")
        else:
            # we need to run pype as different user then Muster dispatcher
            # service is running (usually root).
            muster_python = ("/usr/sbin/runuser -u {}"
                             " -- /usr/bin/python3".format(getpass.getuser()))

        # build the path and argument. We are providing separate --pype
        # argument with network path to pype as post job actions are run
        # but dispatcher (Server) and not render clients. Render clients
        # inherit environment from publisher including PATH, so there's
        # no problem finding PYPE, but there is now way (as far as I know)
        # to set environment dynamically for dispatcher. Therefore this hack.
        args = [muster_python,
                _get_script().replace('\\', '\\\\'),
                "--paths",
                metadata_path.replace('\\', '\\\\'),
                "--pype",
                pype_root.replace('\\', '\\\\')]

        postjob_command = " ".join(args)

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
                    "templateId": _get_template_id(
                        instance.data["renderer"]),
                    "chunksInterleave": 2,
                    "chunksPriority": "0",
                    "chunksTimeoutValue": 320,
                    "department": "",
                    "dependIds": [""],
                    "dependLinkMode": 0,
                    "dependMode": 0,
                    "emergencyQueue": False,
                    "excludedPools": [""],
                    "includedPools": [renderglobals["Pool"]],
                    "packetSize": 4,
                    "packetType": 1,
                    "priority": 1,
                    "jobId": -1,
                    "startOn": 0,
                    "parentId": -1,
                    "project": os.environ.get('AVALON_PROJECT') or scene,
                    "shot": os.environ.get('AVALON_ASSET') or scene,
                    "camera": instance.data.get("cameras")[0],
                    "dependMode": 0,
                    "packetSize": 4,
                    "packetType": 1,
                    "priority": 1,
                    "maximumInstances": 0,
                    "assignedInstances": 0,
                    "attributes": {
                        "environmental_variables": {
                            "value": ", ".join("{!s}={!r}".format(k, v)
                                               for (k, v) in env.items()),

                            "state": True,
                            "subst": False
                         },
                        "memo": {
                            "value": comment,
                            "state": True,
                            "subst": False
                        },
                        "frames_range": {
                            "value": "{start}-{end}".format(
                                start=int(instance.data["frameStart"]),
                                end=int(instance.data["frameEnd"])),
                            "state": True,
                            "subst": False
                        },
                        "job_file": {
                            "value": filepath,
                            "state": True,
                            "subst": True
                        },
                        "job_project": {
                            "value": workspace,
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
                        "MAYADIGITS": {
                          "value": 1,
                          "state": True,
                          "subst": False
                        },
                        "ARNOLDMODE": {
                          "value": "0",
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
                          "value": "-rl {}".format(renderlayer),
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
        """
        Clean and set environment variables for render job so render clients
        work in more or less same environment as publishing machine.

        .. warning:: This is not usable for **post job action** as this is
           executed on dispatcher machine (server) and not render clients.
        """
        keys = [
            # This will trigger `userSetup.py` on the slave
            # such that proper initialisation happens the same
            # way as it does on a local machine.
            # TODO(marcus): This won't work if the slaves don't
            # have access to these paths, such as if slaves are
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
        # self.log.debug("enviro: {}".format(environment['OPENPYPE_SCRIPTS']))
        clean_environment = {}
        for key, value in environment.items():
            clean_path = ""
            self.log.debug("key: {}".format(key))
            if "://" in value:
                clean_path = value
            else:
                valid_paths = []
                for path in value.split(os.pathsep):
                    if not path:
                        continue
                    try:
                        path.decode('UTF-8', 'strict')
                        valid_paths.append(os.path.normpath(path))
                    except UnicodeDecodeError:
                        print('path contains non UTF characters')

                if valid_paths:
                    clean_path = os.pathsep.join(valid_paths)

            clean_environment[key] = clean_path

        return clean_environment

    def preflight_check(self, instance):
        """Ensure the startFrame, endFrame and byFrameStep are integers"""

        for key in ("frameStart", "frameEnd", "byFrameStep"):
            value = instance.data[key]

            if int(value) == value:
                continue

            self.log.warning(
                "%f=%d was rounded off to nearest integer"
                % (value, int(value))
            )

