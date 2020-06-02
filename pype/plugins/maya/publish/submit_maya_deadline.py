# -*- coding: utf-8 -*-
"""Submitting render job to Deadline.

This module is taking care of submitting job from Maya to Deadline. It
creates job and set correct environments. Its behavior is controlled by
``DEADLINE_REST_URL`` environment variable - pointing to Deadline Web Service
and :data:`MayaSubmitDeadline.use_published` property telling Deadline to
use published scene workfile or not.

If ``vrscene`` or ``assscene`` are detected in families, it will first
submit job to export these files and then dependent job to render them.

Attributes:
    payload_skeleton (dict): Skeleton payload data sent as job to Deadline.
        Default values are for ``MayaBatch`` plugin.

"""

import os
import json
import getpass
import copy

import clique
import requests

from maya import cmds

from avalon import api
import pyblish.api

from pype.hosts.maya import lib

# Documentation for keys available at:
# https://docs.thinkboxsoftware.com
#    /products/deadline/8.0/1_User%20Manual/manual
#    /manual-submission.html#job-info-file-options

payload_skeleton = {
    "JobInfo": {
        "BatchName": None,  # Top-level group name
        "Name": None,  # Job name, as seen in Monitor
        "UserName": None,
        "Plugin": "MayaBatch",
        "Frames": "{start}-{end}x{step}",
        "Comment": None,
    },
    "PluginInfo": {
        "SceneFile": None,  # Input
        "OutputFilePath": None,  # Output directory and filename
        "OutputFilePrefix": None,
        "Version": cmds.about(version=True),  # Mandatory for Deadline
        "UsingRenderLayers": True,
        "RenderLayer": None,  # Render only this layer
        "Renderer": None,
        "ProjectPath": None,  # Resolve relative references
    },
    "AuxFiles": []  # Mandatory for Deadline, may be empty
}


def get_renderer_variables(renderlayer=None):
    """Retrieve the extension which has been set in the VRay settings.

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

    filename_0 = cmds.renderSettings(
        fullPath=True,
        gin="#" * int(padding),
        lut=True,
        layer=renderlayer or lib.get_current_renderlayer())[0]
    filename_0 = filename_0.replace('_<RenderPass>', '_beauty')
    prefix_attr = "defaultRenderGlobals.imageFilePrefix"
    if renderer == "vray":
        # Maya's renderSettings function does not return V-Ray file extension
        # so we get the extension from vraySettings
        extension = cmds.getAttr("vraySettings.imageFormatStr")

        # When V-Ray image format has not been switched once from default .png
        # the getAttr command above returns None. As such we explicitly set
        # it to `.png`
        if extension is None:
            extension = "png"

        if extension == "exr (multichannel)" or extension == "exr (deep)":
            extension = "exr"

        prefix_attr = "vraySettings.fileNamePrefix"
    elif renderer == "renderman":
        prefix_attr = "rmanGlobals.imageFileFormat"
    elif renderer == "redshift":
        # mapping redshift extension dropdown values to strings
        ext_mapping = ["iff", "exr", "tif", "png", "tga", "jpg"]
        extension = ext_mapping[
            cmds.getAttr("redshiftOptions.imageFormat")
        ]
    else:
        # Get the extension, getAttr defaultRenderGlobals.imageFormat
        # returns an index number.
        filename_base = os.path.basename(filename_0)
        extension = os.path.splitext(filename_base)[-1].strip(".")

    filename_prefix = cmds.getAttr(prefix_attr)
    return {"ext": extension,
            "filename_prefix": filename_prefix,
            "padding": padding,
            "filename_0": filename_0}


class MayaSubmitDeadline(pyblish.api.InstancePlugin):
    """Submit available render layers to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable ``DEADLINE_REST_URL``.

    Note:
        If Deadline configuration is not detected, this plugin will
        be disabled.

    Attributes:
        use_published (bool): Use published scene to render instead of the
            one in work area.

    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["maya"]
    families = ["renderlayer"]
    if not os.environ.get("DEADLINE_REST_URL"):
        optional = False
        active = False
    else:
        optional = True

    use_published = True

    def process(self, instance):
        """Plugin entry point."""
        self._instance = instance
        self._deadline_url = os.environ.get(
            "DEADLINE_REST_URL", "http://localhost:8082")
        assert self._deadline_url, "Requires DEADLINE_REST_URL"

        context = instance.context
        workspace = context.data["workspaceDir"]
        anatomy = context.data['anatomy']

        filepath = None

        # Handle render/export from published scene or not ------------------
        if self.use_published:
            for i in context:
                if "workfile" in i.data["families"]:
                    assert i.data["publish"] is True, (
                        "Workfile (scene) must be published along")
                    template_data = i.data.get("anatomyData")
                    rep = i.data.get("representations")[0].get("name")
                    template_data["representation"] = rep
                    template_data["ext"] = rep
                    template_data["comment"] = None
                    anatomy_filled = anatomy.format(template_data)
                    template_filled = anatomy_filled["publish"]["path"]
                    filepath = os.path.normpath(template_filled)
                    self.log.info("Using published scene for render {}".format(
                        filepath))

                    if not os.path.exists(filepath):
                        self.log.error("published scene does not exist!")
                        raise
                    # now we need to switch scene in expected files
                    # because <scene> token will now point to published
                    # scene file and that might differ from current one
                    new_scene = os.path.splitext(
                        os.path.basename(filepath))[0]
                    orig_scene = os.path.splitext(
                        os.path.basename(context.data["currentFile"]))[0]
                    exp = instance.data.get("expectedFiles")

                    if isinstance(exp[0], dict):
                        # we have aovs and we need to iterate over them
                        new_exp = {}
                        for aov, files in exp[0].items():
                            replaced_files = []
                            for f in files:
                                replaced_files.append(
                                    f.replace(orig_scene, new_scene)
                                )
                            new_exp[aov] = replaced_files
                        instance.data["expectedFiles"] = [new_exp]
                    else:
                        new_exp = []
                        for f in exp:
                            new_exp.append(
                                f.replace(orig_scene, new_scene)
                            )
                        instance.data["expectedFiles"] = [new_exp]
                    self.log.info("Scene name was switched {} -> {}".format(
                        orig_scene, new_scene
                    ))

        all_instances = []
        for result in context.data["results"]:
            if (result["instance"] is not None and
               result["instance"] not in all_instances):  # noqa: E128
                all_instances.append(result["instance"])

        # fallback if nothing was set
        if not filepath:
            self.log.warning("Falling back to workfile")
            filepath = context.data["currentFile"]

        self.log.debug(filepath)

        # Gather needed data ------------------------------------------------
        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        dirname = os.path.join(workspace, "renders")
        renderlayer = instance.data['setMembers']       # rs_beauty
        deadline_user = context.data.get("deadlineUser", getpass.getuser())
        jobname = "%s - %s" % (filename, instance.name)

        # Get the variables depending on the renderer
        render_variables = get_renderer_variables(renderlayer)
        filename_0 = render_variables["filename_0"]
        if self.use_published:
            new_scene = os.path.splitext(filename)[0]
            orig_scene = os.path.splitext(
                os.path.basename(context.data["currentFile"]))[0]
            filename_0 = render_variables["filename_0"].replace(
                orig_scene, new_scene)

        output_filename_0 = filename_0

        # Create render folder ----------------------------------------------
        try:
            # Ensure render folder exists
            os.makedirs(dirname)
        except OSError:
            pass

        # Fill in common data to payload ------------------------------------
        payload_data = {}
        payload_data["filename"] = filename
        payload_data["filepath"] = filepath
        payload_data["jobname"] = jobname
        payload_data["deadline_user"] = deadline_user
        payload_data["comment"] = comment
        payload_data["output_filename_0"] = output_filename_0
        payload_data["render_variables"] = render_variables
        payload_data["renderlayer"] = renderlayer
        payload_data["workspace"] = workspace
        payload_data["dirname"] = dirname

        frame_pattern = payload_skeleton["JobInfo"]["Frames"]
        payload_skeleton["JobInfo"]["Frames"] = frame_pattern.format(
            start=int(self._instance.data["frameStartHandle"]),
            end=int(self._instance.data["frameEndHandle"]),
            step=int(self._instance.data["byFrameStep"]))

        payload_skeleton["JobInfo"]["Plugin"] = self._instance.data.get(
            "mayaRenderPlugin", "MayaBatch")

        payload_skeleton["JobInfo"]["BatchName"] = filename
        # Job name, as seen in Monitor
        payload_skeleton["JobInfo"]["Name"] = jobname
        # Arbitrary username, for visualisation in Monitor
        payload_skeleton["JobInfo"]["UserName"] = deadline_user
        # Optional, enable double-click to preview rendered
        # frames from Deadline Monitor
        payload_skeleton["JobInfo"]["OutputDirectory0"] = \
            os.path.dirname(output_filename_0)
        payload_skeleton["JobInfo"]["OutputFilename0"] = \
            output_filename_0.replace("\\", "/")

        payload_skeleton["JobInfo"]["Comment"] = comment
        payload_skeleton["PluginInfo"]["RenderLayer"] = renderlayer

        # Adding file dependencies.
        dependencies = instance.context.data["fileDependencies"]
        dependencies.append(filepath)
        for dependency in dependencies:
            self.log.info(dependency)
            key = "AssetDependency" + str(dependencies.index(dependency))
            self.log.info(key)
            payload_skeleton["JobInfo"][key] = dependency

        # Handle environments -----------------------------------------------
        # We need those to pass them to pype for it to set correct context
        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "PYPE_USERNAME",
            "PYPE_DEV",
            "PYPE_LOG_NO_COLORS"
        ]

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)
        environment["PYPE_LOG_NO_COLORS"] = "1"
        payload_skeleton["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })
        # Add options from RenderGlobals-------------------------------------
        render_globals = instance.data.get("renderGlobals", {})
        payload_skeleton["JobInfo"].update(render_globals)

        # Submit preceeding export jobs -------------------------------------
        export_job = None
        assert not all(x in instance.data["families"]
                       for x in ['vrayscene', 'assscene']), (
            "Vray Scene and Ass Scene options are mutually exclusive")
        if "vrayscene" in instance.data["families"]:
            export_job = self._submit_export(payload_data, "vray")

        if "assscene" in instance.data["families"]:
            export_job = self._submit_export(payload_data, "arnold")

        # Prepare main render job -------------------------------------------
        if "vrayscene" in instance.data["families"]:
            payload = self._get_vray_render_payload(payload_data)
        elif "assscene" in instance.data["families"]:
            payload = self._get_arnold_render_payload(payload_data)
        else:
            payload = self._get_maya_payload(payload_data)

        # Add export job as dependency --------------------------------------
        if export_job:
            payload["JobInfo"]["JobDependency0"] = export_job

        # Add list of expected files to job ---------------------------------
        exp = instance.data.get("expectedFiles")

        output_filenames = {}
        exp_index = 0

        if isinstance(exp[0], dict):
            # we have aovs and we need to iterate over them
            for aov, files in exp[0].items():
                col = clique.assemble(files)[0][0]
                output_file = col.format('{head}{padding}{tail}')
                payload['JobInfo']['OutputFilename' + str(exp_index)] = output_file  # noqa: E501
                output_filenames[exp_index] = output_file
                exp_index += 1
        else:
            col = clique.assemble(files)[0][0]
            output_file = col.format('{head}{padding}{tail}')
            payload['JobInfo']['OutputFilename' + str(exp_index)] = output_file
            # OutputFilenames[exp_index] = output_file

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("using render plugin : {}".format(plugin))

        self.preflight_check(instance)

        # Submit job to farm ------------------------------------------------
        self.log.info("Submitting ...")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(self._deadline_url)
        response = self._requests_post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store output dir for unified publisher (filesequence)
        instance.data["outputDir"] = os.path.dirname(filename_0)
        instance.data["deadlineSubmissionJob"] = response.json()

    def _get_maya_payload(self, data):
        payload = copy.deepcopy(payload_skeleton)

        job_info_ext = {
            # Asset dependency to wait for at least the scene file to sync.
            "AssetDependency0": data["filepath"],
        }

        plugin_info = {
            "SceneFile": data["filepath"],
            # Output directory and filename
            "OutputFilePath": data["dirname"].replace("\\", "/"),
            "OutputFilePrefix": data["render_variables"]["filename_prefix"],  # noqa: E501

            # Only render layers are considered renderable in this pipeline
            "UsingRenderLayers": True,

            # Render only this layer
            "RenderLayer": data["renderlayer"],

            # Determine which renderer to use from the file itself
            "Renderer": self._instance.data["renderer"],

            # Resolve relative references
            "ProjectPath": data["workspace"],
        }
        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info)
        return payload

    def _get_vray_export_payload(self, data):
        payload = copy.deepcopy(payload_skeleton)
        job_info_ext = {
            # Job name, as seen in Monitor
            "Name": "Export {} [{}-{}]".format(
                data["jobname"],
                int(self._instance.data["frameStartHandle"]),
                int(self._instance.data["frameEndHandle"])),

            "Plugin": "MayaBatch",
            "FramesPerTask": self._instance.data.get("framesPerTask", 1)
        }

        plugin_info_ext = {
            # Renderer
            "Renderer": "vray",
            # Input
            "SceneFile": data["filepath"],
            "SkipExistingFrames": True,
            "UsingRenderLayers": True,
            "UseLegacyRenderLayers": True,
            "RenderLayer": data["renderlayer"],
            "ProjectPath": data["workspace"]
        }

        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info_ext)
        return payload

    def _get_arnold_export_payload(self, data):

        try:
            from pype.scripts import export_maya_ass_job
        except Exception:
            assert False, (
                "Expected module 'export_maya_ass_job' to be available")

        module_path = export_maya_ass_job.__file__
        if module_path.endswith(".pyc"):
            module_path = module_path[: -len(".pyc")] + ".py"

        script = os.path.normpath(module_path)

        payload = copy.deepcopy(payload_skeleton)
        job_info_ext = {
            # Job name, as seen in Monitor
            "Name": "Export {} [{}-{}]".format(
                data["jobname"],
                int(self._instance.data["frameStartHandle"]),
                int(self._instance.data["frameEndHandle"])),

            "Plugin": "Python",
            "FramesPerTask": self._instance.data.get("framesPerTask", 1),
            "Frames": 1
        }

        plugin_info_ext = {
            "Version": "3.6",
            "ScriptFile": script,
            "Arguments": "",
            "SingleFrameOnly": "True",
        }
        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info_ext)

        envs = []
        for k, v in payload["JobInfo"].items():
            if k.startswith("EnvironmentKeyValue"):
                envs.append(v)

        # add app name to environment
        envs.append(
            "AVALON_APP_NAME={}".format(os.environ.get("AVALON_APP_NAME")))
        envs.append(
            "PYPE_ASS_EXPORT_RENDER_LAYER={}".format(data["renderlayer"]))
        envs.append(
            "PYPE_ASS_EXPORT_SCENE_FILE={}".format(data["filepath"]))
        envs.append(
            "PYPE_ASS_EXPORT_OUTPUT={}".format(
                payload['JobInfo']['OutputFilename0']))
        envs.append(
            "PYPE_ASS_EXPORT_START={}".format(
                int(self._instance.data["frameStartHandle"])))
        envs.append(
            "PYPE_ASS_EXPORT_END={}".format(
                int(self._instance.data["frameEndHandle"])))
        envs.append(
            "PYPE_ASS_EXPORT_STEP={}".format(1))

        i = 0
        for e in envs:
            payload["JobInfo"]["EnvironmentKeyValue{}".format(i)] = e
            i += 1

        return payload

    def _get_vray_render_payload(self, data):
        payload = copy.deepcopy(payload_skeleton)
        vray_settings = cmds.ls(type="VRaySettingsNode")
        node = vray_settings[0]
        template = cmds.getAttr("{}.vrscene_filename".format(node))
        # "vrayscene/<Scene>/<Scene>_<Layer>/<Layer>"

        scene, _ = os.path.splitext(data["filename"])
        first_file = self.format_vray_output_filename(scene, template)
        first_file = "{}/{}".format(data["workspace"], first_file)
        job_info_ext = {
            "Name": "Render {} [{}-{}]".format(
                data["jobname"],
                int(self._instance.data["frameStartHandle"]),
                int(self._instance.data["frameEndHandle"])),

            "Plugin": "Vray",
            "OverrideTaskExtraInfoNames": False,
        }

        plugin_info = {
            "InputFilename": first_file,
            "SeparateFilesPerFrame": True,
            "VRayEngine": "V-Ray",

            "Width": self._instance.data["resolutionWidth"],
            "Height": self._instance.data["resolutionHeight"],
        }

        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info)
        return payload

    def _get_arnold_render_payload(self, data):
        payload = copy.deepcopy(payload_skeleton)
        ass_file, _ = os.path.splitext(data["output_filename_0"])
        first_file = ass_file + ".ass"
        job_info_ext = {
            "Name": "Render {} [{}-{}]".format(
                data["jobname"],
                int(self._instance.data["frameStartHandle"]),
                int(self._instance.data["frameEndHandle"])),

            "Plugin": "Arnold",
            "OverrideTaskExtraInfoNames": False,
        }

        plugin_info = {
            "ArnoldFile": first_file,
        }

        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info)
        return payload

    def _submit_export(self, data, format):
        if format == "vray":
            payload = self._get_vray_export_payload(data)
            self.log.info("Submitting vrscene export job.")
        elif format == "arnold":
            payload = self._get_arnold_export_payload(data)
            self.log.info("Submitting ass export job.")

        url = "{}/api/jobs".format(self._deadline_url)
        response = self._requests_post(url, json=payload)
        if not response.ok:
            self.log.error("Submition failed!")
            self.log.error(response.status_code)
            self.log.error(response.content)
            self.log.debug(payload)
            raise RuntimeError(response.text)

        dependency = response.json()
        return dependency["_id"]

    def preflight_check(self, instance):
        """Ensure the startFrame, endFrame and byFrameStep are integers."""
        for key in ("frameStartHandle", "frameEndHandle", "byFrameStep"):
            value = instance.data[key]

            if int(value) == value:
                continue

            self.log.warning(
                "%f=%d was rounded off to nearest integer"
                % (value, int(value))
            )

    def _requests_post(self, *args, **kwargs):
        """Wrap request post method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        # add 10sec timeout before bailing out
        kwargs['timeout'] = 10
        return requests.post(*args, **kwargs)

    def _requests_get(self, *args, **kwargs):
        """Wrap request get method.

        Disabling SSL certificate validation if ``DONT_VERIFY_SSL`` environment
        variable is found. This is useful when Deadline or Muster server are
        running with self-signed certificates and their certificate is not
        added to trusted certificates on client machines.

        Warning:
            Disabling SSL certificate validation is defeating one line
            of defense SSL is providing and it is not recommended.

        """
        if 'verify' not in kwargs:
            kwargs['verify'] = False if os.getenv("PYPE_DONT_VERIFY_SSL", True) else True  # noqa
        # add 10sec timeout before bailing out
        kwargs['timeout'] = 10
        return requests.get(*args, **kwargs)

    def format_vray_output_filename(self, filename, template, dir=False):
        """Format the expected output file of the Export job.

        Example:
            <Scene>/<Scene>_<Layer>/<Layer>
            "shot010_v006/shot010_v006_CHARS/CHARS"

        Args:
            instance:
            filename(str):
            dir(bool):

        Returns:
            str

        """
        def smart_replace(string, key_values):
            new_string = string
            for key, value in key_values.items():
                new_string = new_string.replace(key, value)
            return new_string

        # Ensure filename has no extension
        file_name, _ = os.path.splitext(filename)

        # Reformat without tokens
        output_path = smart_replace(
            template,
            {"<Scene>": file_name,
             "<Layer>": self._instance.data['setMembers']})

        if dir:
            return output_path.replace("\\", "/")

        start_frame = int(self._instance.data["frameStartHandle"])
        filename_zero = "{}_{:04d}.vrscene".format(output_path, start_frame)

        result = filename_zero.replace("\\", "/")

        return result
