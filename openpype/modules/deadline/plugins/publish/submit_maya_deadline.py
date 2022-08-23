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

from __future__ import print_function
import os
import getpass
import copy
import re
import hashlib
from datetime import datetime
import itertools
from collections import OrderedDict

import attr
import clique

from maya import cmds

from openpype.hosts.maya.api import lib
from openpype.pipeline import legacy_io

from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo


@attr.s
class DeadlinePluginInfo():
    SceneFile = attr.ib(default=None)   # Input
    OutputFilePath = attr.ib(default=None)  # Output directory and filename
    OutputFilePrefix = attr.ib(default=None)
    Version = attr.ib(default=None)  # Mandatory for Deadline
    UsingRenderLayers = attr.ib(default=True)
    RenderLayer = attr.ib(default=None)  # Render only this layer
    Renderer = attr.ib(default=None)
    ProjectPath = attr.ib(default=None)  # Resolve relative references
    RenderSetupIncludeLights = attr.ib(default=None)  # Include all lights flag


class MayaSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline):
    """Submit available render layers to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via settings key "DEADLINE_REST_URL".

    Attributes:
        use_published (bool): Use published scene to render instead of the
            one in work area.

    """

    label = "Submit Render to Deadline"
    hosts = ["maya"]
    families = ["renderlayer"]
    targets = ["local"]

    tile_assembler_plugin = "OpenPypeTileAssembler"
    priority = 50
    tile_priority = 50
    limit_groups = []
    jobInfo = {}
    pluginInfo = {}
    group = "none"

    def get_job_info(self):
        job_info = DeadlineJobInfo(Plugin="MayaBatch")

        # todo: test whether this works for existing production cases
        #       where custom jobInfo was stored in the project settings
        for key, value in self.jobInfo.items():
            setattr(job_info, key, value)

        instance = self._instance
        context = instance.context

        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)

        job_info.Name = "%s - %s" % (filename, instance.name)
        job_info.BatchName = filename
        job_info.Plugin = instance.data.get("mayaRenderPlugin", "MayaBatch")
        job_info.UserName = context.data.get(
            "deadlineUser", getpass.getuser())

        # Deadline requires integers in frame range
        frames = "{start}-{end}x{step}".format(
            start=int(instance.data["frameStartHandle"]),
            end=int(instance.data["frameEndHandle"]),
            step=int(instance.data["byFrameStep"]),
        )
        job_info.Frames = frames

        job_info.Pool = instance.data.get("primaryPool")
        job_info.SecondaryPool = instance.data.get("secondaryPool")
        job_info.ChunkSize = instance.data.get("chunkSize", 10)
        job_info.Comment = context.data.get("comment")
        job_info.Priority = instance.data.get("priority", self.priority)

        if self.group != "none" and self.group:
            job_info.Group = self.group

        if self.limit_groups:
            job_info.LimitGroups = ",".join(self.limit_groups)

            self.payload_skeleton["JobInfo"]["Name"] = jobname
            self.payload_skeleton["JobInfo"]["BatchName"] = src_filename

        # Optional, enable double-click to preview rendered
        # frames from Deadline Monitor
        self.payload_skeleton["JobInfo"]["OutputDirectory0"] = \
            os.path.dirname(output_filename_0).replace("\\", "/")
        self.payload_skeleton["JobInfo"]["OutputFilename0"] = \
            output_filename_0.replace("\\", "/")

        # Add options from RenderGlobals-------------------------------------
        render_globals = instance.data.get("renderGlobals", {})
        self.payload_skeleton["JobInfo"].update(render_globals)

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "OPENPYPE_SG_USER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "OPENPYPE_DEV",
            "OPENPYPE_LOG_NO_COLORS",
            "OPENPYPE_VERSION"
        ]
        # Add mongo url if it's enabled
        if self._instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)


        # TODO: Taken from old publish class - test whether still needed
        environment["OPENPYPE_LOG_NO_COLORS"] = "1"
        environment["OPENPYPE_MAYA_VERSION"] = cmds.about(v=True)
        # to recognize job from PYPE for turning Event On/Off
        environment["OPENPYPE_RENDER_JOB"] = "1"

        for key in keys:
            val = environment.get(key)
            if val:
                job_info.EnvironmentKeyValue = "{key}={value}".format(
                    key=key,
                    value=val
                )
        # to recognize job from PYPE for turning Event On/Off
        job_info.EnvironmentKeyValue = "OPENPYPE_RENDER_JOB=1"

        for i, filepath in enumerate(instance.data["files"]):
            dirname = os.path.dirname(filepath)
            fname = os.path.basename(filepath)
            job_info.OutputDirectory = dirname.replace("\\", "/")
            job_info.OutputFilename = fname

        # Adding file dependencies.
        if self.asset_dependencies:
            dependencies = instance.context.data["fileDependencies"]
            dependencies.append(context.data["currentFile"])
            for dependency in dependencies:
                job_info.AssetDependency = dependency

        # Add list of expected files to job
        # ---------------------------------
        exp = instance.data.get("expectedFiles")

        def _get_output_filename(files):
            col, rem = clique.assemble(files)
            if not col and rem:
                # we couldn't find any collections but have
                # individual files.
                assert len(rem) == 1, (
                    "Found multiple non related files "
                    "to render, don't know what to do "
                    "with them.")
                return rem[0]
            else:
                return col[0].format('{head}{padding}{tail}')

        if isinstance(exp[0], dict):
            # we have aovs and we need to iterate over them
            for _aov, files in exp[0].items():
                output_file = _get_output_filename(files)
                job_info.OutputFilename = output_file
        else:
            output_file = _get_output_filename(exp)
            job_info.OutputFilename = output_file

        return job_info

    def get_plugin_info(self):

        instance = self._instance
        context = instance.context

        renderlayer = instance.data['setMembers']       # rs_beauty

        self.payload_skeleton["PluginInfo"]["RenderLayer"] = renderlayer
        self.payload_skeleton["PluginInfo"]["RenderSetupIncludeLights"] = instance.data.get("renderSetupIncludeLights") # noqa

        # Output driver to render
        plugin_info = DeadlinePluginInfo(
            SceneFile=context.data["currentFile"],
            Version=cmds.about(version=True),
        )

        return attr.asdict(plugin_info)

    def process_submission(self):
        # Override to NOT submit by default when calling super process() method
        pass

    def process(self, instance):
        super(MayaSubmitDeadline, self).process(instance)

        # TODO: Avoid the need for this logic here, needed for submit publish
        # Store output dir for unified publisher (filesequence)
        output_dir = os.path.dirname(instance.data["files"][0])
        instance.data["outputDir"] = output_dir
        instance.data["toBeRenderedOn"] = "deadline"

        self.limit_groups = self.limit

        context = instance.context
        workspace = context.data["workspaceDir"]

        filepath = None
        patches = (
            context.data["project_settings"].get(
                "deadline", {}).get(
                "publish", {}).get(
                "MayaSubmitDeadline", {}).get(
                "scene_patches", {})
        )

        # todo: on self.use_published originally use template_data["representation"] using .get("name") instead of .get("ext")
        # todo: on self.use_published replace path for publishRenderMetadataFolder
        # todo: on self.use_published apply scene patches to workfile instance
        # rep = i.data.get("representations")[0].get("name")

        # if instance.data.get("publishRenderMetadataFolder"):
        #     instance.data["publishRenderMetadataFolder"] = \
        #         instance.data["publishRenderMetadataFolder"].replace(
        #             orig_scene, new_scene)
        # self.log.info("Scene name was switched {} -> {}".format(
        #     orig_scene, new_scene
        # ))
        # # patch workfile is needed
        # if filepath not in patched_files:
        #     patched_file = self._patch_workfile(filepath, patches)
        #     patched_files.append(patched_file)

        filepath = self.scene_path  # collect by super().process

        # Gather needed data ------------------------------------------------
        default_render_file = instance.context.data.get('project_settings')\
            .get('maya')\
            .get('RenderSettings')\
            .get('default_render_image_folder')
        filename = os.path.basename(filepath)
        dirname = os.path.join(workspace, default_render_file)
        renderlayer = instance.data['setMembers']       # rs_beauty

        # Always use the original work file name for the Job name even when
        # rendering is done from the published Work File. The original work
        # file name is clearer because it can also have subversion strings,
        # etc. which are stripped for the published file.
        src_filename = os.path.basename(context.data["currentFile"])
        jobname = "%s - %s" % (src_filename, instance.name)

        # Get the variables depending on the renderer
        render_variables = get_renderer_variables(renderlayer, dirname)
        filename_0 = render_variables["filename_0"]
        if self.use_published:
            new_scene = os.path.splitext(filename)[0]
            orig_scene = os.path.splitext(
                os.path.basename(context.data["currentFile"]))[0]
            filename_0 = render_variables["filename_0"].replace(
                orig_scene, new_scene)

        output_filename_0 = filename_0

        # this is needed because renderman handles directory and file
        # prefixes separately
        if self._instance.data["renderer"] == "renderman":
            dirname = os.path.dirname(output_filename_0)

        # Create render folder ----------------------------------------------
        try:
            # Ensure render folder exists
            os.makedirs(dirname)
        except OSError:
            pass

        # Fill in common data to payload ------------------------------------
        payload_data = {
            "filename": filename,
            "filepath": filepath,
            "jobname": jobname,
            "comment": comment,
            "output_filename_0": output_filename_0,
            "render_variables": render_variables,
            "renderlayer": renderlayer,
            "workspace": workspace,
            "dirname": dirname,
        }

        # Submit preceding export jobs -------------------------------------
        export_job = None
        assert not all(x in instance.data["families"]
                       for x in ['vrayscene', 'assscene']), (
            "Vray Scene and Ass Scene options are mutually exclusive")

        if "vrayscene" in instance.data["families"]:
            vray_export_payload = self._get_vray_export_payload(payload_data)
            export_job = self.submit(vray_export_payload)

            payload = self._get_vray_render_payload(payload_data)

        elif "assscene" in instance.data["families"]:
            ass_export_payload = self._get_arnold_export_payload(payload_data)
            export_job = self.submit(ass_export_payload)

            payload = self._get_arnold_render_payload(payload_data)
        else:
            payload = self._get_maya_payload(payload_data)

        # Add export job as dependency --------------------------------------
        if export_job:
            payload["JobInfo"]["JobDependency0"] = export_job

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("using render plugin : {}".format(plugin))

        # Store output dir for unified publisher (filesequence)
        instance.data["outputDir"] = os.path.dirname(output_filename_0)

        # add jobInfo and pluginInfo variables from Settings
        payload["JobInfo"].update(self.jobInfo)
        payload["PluginInfo"].update(self.pluginInfo)

        if instance.data.get("tileRendering"):
            # Prepare tiles data
            self._tile_render(instance, payload)
        else:
            # Submit main render job
            self.submit(payload)

    def _tile_render(self, instance, payload):

        # As collected by super process()
        job_info = self.job_info
        plugin_info = self.pluginInfo

        # if we have sequence of files, we need to create tile job for
        # every frame

        job_info.TileJob = True
        job_info.TileJobTilesInX = instance.data.get("tilesX")
        job_info.TileJobTilesInY = instance.data.get("tilesY")

        plugin_info["ImageHeight"] = instance.data.get("resolutionHeight")
        plugin_info["ImageWidth"] = instance.data.get("resolutionWidth")
        plugin_info["RegionRendering"] = True

        assembly_payload = {
            "AuxFiles": [],
            "JobInfo": {
                "BatchName": payload["JobInfo"]["BatchName"],
                "Frames": 1,
                "Name": "{} - Tile Assembly Job".format(
                    payload["JobInfo"]["Name"]),
                "OutputDirectory0":
                    payload["JobInfo"]["OutputDirectory0"].replace(
                        "\\", "/"),
                "Plugin": self.tile_assembler_plugin,
                "MachineLimit": 1
            },
            "PluginInfo": {
                "CleanupTiles": 1,
                "ErrorOnMissing": True
            }
        }
        assembly_payload["JobInfo"]["Priority"] = self._instance.data.get(
            "tile_priority", self.tile_priority)

        frame_payloads = []
        assembly_payloads = []

        R_FRAME_NUMBER = re.compile(
            r".+\.(?P<frame>[0-9]+)\..+")  # noqa: N806, E501
        REPL_FRAME_NUMBER = re.compile(
            r"(.+\.)([0-9]+)(\..+)")  # noqa: N806, E501

        exp = instance.data["expectedFiles"]
        if isinstance(exp[0], dict):
            # we have aovs and we need to iterate over them
            # get files from `beauty`
            files = exp[0].get("beauty")
            # assembly files are used for assembly jobs as we need to put
            # together all AOVs
            assembly_files = list(
                itertools.chain.from_iterable(
                    [f for _, f in exp[0].items()]))
            if not files:
                # if beauty doesn't exists, use first aov we found
                files = exp[0].get(list(exp[0].keys())[0])
        else:
            files = exp
            assembly_files = files

        frame_jobs = {}

        file_index = 1
        for file in files:
            frame = re.search(R_FRAME_NUMBER, file).group("frame")
            new_payload = copy.deepcopy(payload)
            new_payload["JobInfo"]["Name"] = \
                "{} (Frame {} - {} tiles)".format(
                    payload["JobInfo"]["Name"],
                    frame,
                    instance.data.get("tilesX") * instance.data.get("tilesY")
                    # noqa: E501
                )
            self.log.info(
                "... preparing job {}".format(
                    new_payload["JobInfo"]["Name"]))
            new_payload["JobInfo"]["TileJobFrame"] = frame

            tiles_data = _format_tiles(
                file, 0,
                instance.data.get("tilesX"),
                instance.data.get("tilesY"),
                instance.data.get("resolutionWidth"),
                instance.data.get("resolutionHeight"),
                payload["PluginInfo"]["OutputFilePrefix"]
            )[0]
            new_payload["JobInfo"].update(tiles_data["JobInfo"])
            new_payload["PluginInfo"].update(tiles_data["PluginInfo"])

            self.log.info("hashing {} - {}".format(file_index, file))
            job_hash = hashlib.sha256(
                ("{}_{}".format(file_index, file)).encode("utf-8"))
            frame_jobs[frame] = job_hash.hexdigest()
            new_payload["JobInfo"]["ExtraInfo0"] = job_hash.hexdigest()
            new_payload["JobInfo"]["ExtraInfo1"] = file

            frame_payloads.append(new_payload)
            file_index += 1

        file_index = 1
        for file in assembly_files:
            frame = re.search(R_FRAME_NUMBER, file).group("frame")
            new_assembly_payload = copy.deepcopy(assembly_payload)
            new_assembly_payload["JobInfo"]["Name"] = \
                "{} (Frame {})".format(
                    assembly_payload["JobInfo"]["Name"],
                    frame)
            new_assembly_payload["JobInfo"]["OutputFilename0"] = re.sub(
                REPL_FRAME_NUMBER,
                "\\1{}\\3".format("#" * len(frame)), file)

            new_assembly_payload["PluginInfo"]["Renderer"] = \
            self._instance.data["renderer"]  # noqa: E501
            new_assembly_payload["JobInfo"]["ExtraInfo0"] = frame_jobs[
                frame]  # noqa: E501
            new_assembly_payload["JobInfo"]["ExtraInfo1"] = file
            assembly_payloads.append(new_assembly_payload)
            file_index += 1

        self.log.info(
            "Submitting tile job(s) [{}] ...".format(len(frame_payloads)))

        url = "{}/api/jobs".format(self.deadline_url)
        tiles_count = instance.data.get("tilesX") * instance.data.get(
            "tilesY")  # noqa: E501

        for tile_job in frame_payloads:
            response = self.submit(tile_job)

            job_id = response.json()["_id"]
            hash = response.json()["Props"]["Ex0"]

            for assembly_job in assembly_payloads:
                if assembly_job["JobInfo"]["ExtraInfo0"] == hash:
                    assembly_job["JobInfo"]["JobDependency0"] = job_id

        for assembly_job in assembly_payloads:
            file = assembly_job["JobInfo"]["ExtraInfo1"]
            # write assembly job config files
            now = datetime.now()

            config_file = os.path.join(
                os.path.dirname(output_filename_0),
                "{}_config_{}.txt".format(
                    os.path.splitext(file)[0],
                    now.strftime("%Y_%m_%d_%H_%M_%S")
                )
            )

            try:
                if not os.path.isdir(os.path.dirname(config_file)):
                    os.makedirs(os.path.dirname(config_file))
            except OSError:
                # directory is not available
                self.log.warning(
                    "Path is unreachable: `{}`".format(
                        os.path.dirname(config_file)))

            # add config file as job auxFile
            assembly_job["AuxFiles"] = [config_file]

            with open(config_file, "w") as cf:
                print("TileCount={}".format(tiles_count), file=cf)
                print("ImageFileName={}".format(file), file=cf)
                print("ImageWidth={}".format(
                    instance.data.get("resolutionWidth")), file=cf)
                print("ImageHeight={}".format(
                    instance.data.get("resolutionHeight")), file=cf)

                tiles = _format_tiles(
                    file, 0,
                    instance.data.get("tilesX"),
                    instance.data.get("tilesY"),
                    instance.data.get("resolutionWidth"),
                    instance.data.get("resolutionHeight"),
                    payload["PluginInfo"]["OutputFilePrefix"]
                )[1]
                sorted(tiles)
                for k, v in tiles.items():
                    print("{}={}".format(k, v), file=cf)

        job_idx = 1
        instance.data["assemblySubmissionJobs"] = []
        for ass_job in assembly_payloads:
            self.log.info("submitting assembly job {} of {}".format(
                job_idx, len(assembly_payloads)
            ))
            response = self.submit(ass_job)

            instance.data["assemblySubmissionJobs"].append(
                response.json()["_id"])
            job_idx += 1

        instance.data["jobBatchName"] = payload["JobInfo"]["BatchName"]
        self.log.info("Setting batch name on instance: {}".format(
            instance.data["jobBatchName"]))

    def _get_maya_payload(self, data):
        payload = copy.deepcopy(self.payload_skeleton)

        if not self.asset_dependencies:
            job_info_ext = {}

        else:
            job_info_ext = {
                # Asset dependency to wait for at least the scene file to sync.
                "AssetDependency0": data["filepath"],
            }

        renderer = self._instance.data["renderer"]

        # This hack is here because of how Deadline handles Renderman version.
        # it considers everything with `renderman` set as version older than
        # Renderman 22, and so if we are using renderman > 21 we need to set
        # renderer string on the job to `renderman22`. We will have to change
        # this when Deadline releases new version handling this.
        if self._instance.data["renderer"] == "renderman":
            try:
                from rfm2.config import cfg  # noqa
            except ImportError:
                raise Exception("Cannot determine renderman version")

            rman_version = cfg().build_info.version()  # type: str
            if int(rman_version.split(".")[0]) > 22:
                renderer = "renderman22"

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
            "Renderer": renderer,

            # Resolve relative references
            "ProjectPath": data["workspace"],
        }
        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info)
        return payload

    def _get_vray_export_payload(self, data):
        payload = copy.deepcopy(self.payload_skeleton)
        vray_settings = cmds.ls(type="VRaySettingsNode")
        node = vray_settings[0]
        template = cmds.getAttr("{}.vrscene_filename".format(node))
        scene, _ = os.path.splitext(data["filename"])
        first_file = self.format_vray_output_filename(scene, template)
        first_file = "{}/{}".format(data["workspace"], first_file)
        output = os.path.dirname(first_file)
        job_info_ext = {
            # Job name, as seen in Monitor
            "Name": "Export {} [{}-{}]".format(
                data["jobname"],
                int(self._instance.data["frameStartHandle"]),
                int(self._instance.data["frameEndHandle"])),

            "Plugin": self._instance.data.get(
                "mayaRenderPlugin", "MayaPype"),
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
            "ProjectPath": data["workspace"],
            "OutputFilePath": output
        }

        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info_ext)
        return payload

    def _get_arnold_export_payload(self, data):

        try:
            from openpype.scripts import export_maya_ass_job
        except Exception:
            raise AssertionError(
                "Expected module 'export_maya_ass_job' to be available")

        module_path = export_maya_ass_job.__file__
        if module_path.endswith(".pyc"):
            module_path = module_path[: -len(".pyc")] + ".py"

        script = os.path.normpath(module_path)

        payload = copy.deepcopy(self.payload_skeleton)
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

        envs = [
            v
            for k, v in payload["JobInfo"].items()
            if k.startswith("EnvironmentKeyValue")
        ]

        # add app name to environment
        envs.append(
            "AVALON_APP_NAME={}".format(os.environ.get("AVALON_APP_NAME")))
        envs.append(
            "OPENPYPE_ASS_EXPORT_RENDER_LAYER={}".format(data["renderlayer"]))
        envs.append(
            "OPENPYPE_ASS_EXPORT_SCENE_FILE={}".format(data["filepath"]))
        envs.append(
            "OPENPYPE_ASS_EXPORT_OUTPUT={}".format(
                payload['JobInfo']['OutputFilename0']))
        envs.append(
            "OPENPYPE_ASS_EXPORT_START={}".format(
                int(self._instance.data["frameStartHandle"])))
        envs.append(
            "OPENPYPE_ASS_EXPORT_END={}".format(
                int(self._instance.data["frameEndHandle"])))
        envs.append(
            "OPENPYPE_ASS_EXPORT_STEP={}".format(1))

        for i, e in enumerate(envs):
            payload["JobInfo"]["EnvironmentKeyValue{}".format(i)] = e
        return payload

    def _get_vray_render_payload(self, data):
        payload = copy.deepcopy(self.payload_skeleton)
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
            "OutputFilePath": payload["JobInfo"]["OutputDirectory0"],
            "OutputFileName": payload["JobInfo"]["OutputFilename0"]
        }

        payload["JobInfo"].update(job_info_ext)
        payload["PluginInfo"].update(plugin_info)
        return payload

    def _get_arnold_render_payload(self, data):
        payload = copy.deepcopy(self.payload_skeleton)
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

        layer = self._instance.data['setMembers']

        # Reformat without tokens
        output_path = smart_replace(
            template,
            {"<Scene>": file_name,
             "<Layer>": layer})

        if dir:
            return output_path.replace("\\", "/")

        start_frame = int(self._instance.data["frameStartHandle"])
        filename_zero = "{}_{:04d}.vrscene".format(output_path, start_frame)

        result = filename_zero.replace("\\", "/")

        return result

    def _patch_workfile(self, file, patches):
        # type: (str, dict) -> [str, None]
        """Patch Maya scene.

        This will take list of patches (lines to add) and apply them to
        *published* Maya  scene file (that is used later for rendering).

        Patches are dict with following structure::
            {
                "name": "Name of patch",
                "regex": "regex of line before patch",
                "line": "line to insert"
            }

        Args:
            file (str): File to patch.
            patches (dict): Dictionary defining patches.

        Returns:
            str: Patched file path or None

        """
        if os.path.splitext(file)[1].lower() != ".ma" or not patches:
            return None

        compiled_regex = [re.compile(p["regex"]) for p in patches]
        with open(file, "r+") as pf:
            scene_data = pf.readlines()
            for ln, line in enumerate(scene_data):
                for i, r in enumerate(compiled_regex):
                    if re.match(r, line):
                        scene_data.insert(ln + 1, patches[i]["line"])
                        pf.seek(0)
                        pf.writelines(scene_data)
                        pf.truncate()
                        self.log.info(
                            "Applied {} patch to scene.".format(
                                patches[i]["name"]))
        return file


def _format_tiles(
        filename, index, tiles_x, tiles_y,
        width, height, prefix):
    """Generate tile entries for Deadline tile job.

    Returns two dictionaries - one that can be directly used in Deadline
    job, second that can be used for Deadline Assembly job configuration
    file.

    This will format tile names:

    Example::
        {
        "OutputFilename0Tile0": "_tile_1x1_4x4_Main_beauty.1001.exr",
        "OutputFilename0Tile1": "_tile_2x1_4x4_Main_beauty.1001.exr"
        }

    And add tile prefixes like:

    Example::
        Image prefix is:
        `maya/<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>`

        Result for tile 0 for 4x4 will be:
        `maya/<Scene>/<RenderLayer>/_tile_1x1_4x4_<RenderLayer>_<RenderPass>`

    Calculating coordinates is tricky as in Job they are defined as top,
    left, bottom, right with zero being in top-left corner. But Assembler
    configuration file takes tile coordinates as X, Y, Width and Height and
    zero is bottom left corner.

    Args:
        filename (str): Filename to process as tiles.
        index (int): Index of that file if it is sequence.
        tiles_x (int): Number of tiles in X.
        tiles_y (int): Number if tikes in Y.
        width (int): Width resolution of final image.
        height (int):  Height resolution of final image.
        prefix (str): Image prefix.

    Returns:
        (dict, dict): Tuple of two dictionaires - first can be used to
                      extend JobInfo, second has tiles x, y, width and height
                      used for assembler configuration.

    """
    tile = 0
    out = {"JobInfo": {}, "PluginInfo": {}}
    cfg = OrderedDict()
    w_space = width / tiles_x
    h_space = height / tiles_y

    cfg["TilesCropped"] = "False"

    for tile_x in range(1, tiles_x + 1):
        for tile_y in reversed(range(1, tiles_y + 1)):
            tile_prefix = "_tile_{}x{}_{}x{}_".format(
                tile_x, tile_y,
                tiles_x,
                tiles_y
            )
            out_tile_index = "OutputFilename{}Tile{}".format(
                str(index), tile
            )
            new_filename = "{}/{}{}".format(
                os.path.dirname(filename),
                tile_prefix,
                os.path.basename(filename)
            )
            out["JobInfo"][out_tile_index] = new_filename
            out["PluginInfo"]["RegionPrefix{}".format(str(tile))] = \
                "/{}".format(tile_prefix).join(prefix.rsplit("/", 1))

            out["PluginInfo"]["RegionTop{}".format(tile)] = int(height) - (tile_y * h_space)  # noqa: E501
            out["PluginInfo"]["RegionBottom{}".format(tile)] = int(height) - ((tile_y - 1) * h_space) - 1  # noqa: E501
            out["PluginInfo"]["RegionLeft{}".format(tile)] = (tile_x - 1) * w_space  # noqa: E501
            out["PluginInfo"]["RegionRight{}".format(tile)] = (tile_x * w_space) - 1  # noqa: E501

            cfg["Tile{}".format(tile)] = new_filename
            cfg["Tile{}Tile".format(tile)] = new_filename
            cfg["Tile{}FileName".format(tile)] = new_filename
            cfg["Tile{}X".format(tile)] = (tile_x - 1) * w_space

            cfg["Tile{}Y".format(tile)] = int(height) - (tile_y * h_space)

            cfg["Tile{}Width".format(tile)] = w_space
            cfg["Tile{}Height".format(tile)] = h_space

            tile += 1
    return out, cfg


def get_renderer_variables(renderlayer, root):
    """Retrieve the extension which has been set in the VRay settings.

    Will return None if the current renderer is not VRay
    For Maya 2016.5 and up the renderSetup creates renderSetupLayer node which
    start with `rs`. Use the actual node name, do NOT use the `nice name`

    Args:
        renderlayer (str): the node name of the renderlayer.
        root (str): base path to render

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
    filename_0 = re.sub('_<RenderPass>', '_beauty',
                        filename_0, flags=re.IGNORECASE)
    prefix_attr = "defaultRenderGlobals.imageFilePrefix"

    scene = cmds.file(query=True, sceneName=True)
    scene, _ = os.path.splitext(os.path.basename(scene))

    if renderer == "vray":
        renderlayer = renderlayer.split("_")[-1]
        # Maya's renderSettings function does not return V-Ray file extension
        # so we get the extension from vraySettings
        extension = cmds.getAttr("vraySettings.imageFormatStr")

        # When V-Ray image format has not been switched once from default .png
        # the getAttr command above returns None. As such we explicitly set
        # it to `.png`
        if extension is None:
            extension = "png"

        if extension in ["exr (multichannel)", "exr (deep)"]:
            extension = "exr"

        prefix_attr = "vraySettings.fileNamePrefix"
        filename_prefix = cmds.getAttr(prefix_attr)
        # we need to determine path for vray as maya `renderSettings` query
        # does not work for vray.

        filename_0 = re.sub('<Scene>', scene, filename_prefix, flags=re.IGNORECASE)  # noqa: E501
        filename_0 = re.sub('<Layer>', renderlayer, filename_0, flags=re.IGNORECASE)  # noqa: E501
        filename_0 = "{}.{}.{}".format(
            filename_0, "#" * int(padding), extension)
        filename_0 = os.path.normpath(os.path.join(root, filename_0))
    elif renderer == "renderman":
        prefix_attr = "rmanGlobals.imageFileFormat"
        # NOTE: This is guessing extensions from renderman display types.
        #       Some of them are just framebuffers, d_texture format can be
        #       set in display setting. We set those now to None, but it
        #       should be handled more gracefully.
        display_types = {
            "d_deepexr": "exr",
            "d_it": None,
            "d_null": None,
            "d_openexr": "exr",
            "d_png": "png",
            "d_pointcloud": "ptc",
            "d_targa": "tga",
            "d_texture": None,
            "d_tiff": "tif"
        }

        extension = display_types.get(
            cmds.listConnections("rmanDefaultDisplay.displayType")[0],
            "exr"
        ) or "exr"

        filename_prefix = "{}/{}".format(
            cmds.getAttr("rmanGlobals.imageOutputDir"),
            cmds.getAttr("rmanGlobals.imageFileFormat")
        )

        renderlayer = renderlayer.split("_")[-1]

        filename_0 = re.sub('<scene>', scene, filename_prefix, flags=re.IGNORECASE)  # noqa: E501
        filename_0 = re.sub('<layer>', renderlayer, filename_0, flags=re.IGNORECASE)  # noqa: E501
        filename_0 = re.sub('<f[\\d+]>', "#" * int(padding), filename_0, flags=re.IGNORECASE)  # noqa: E501
        filename_0 = re.sub('<ext>', extension, filename_0, flags=re.IGNORECASE)  # noqa: E501
        filename_0 = os.path.normpath(os.path.join(root, filename_0))
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


