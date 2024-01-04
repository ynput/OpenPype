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

from openpype.pipeline import (
    legacy_io,
    OpenPypePyblishPluginMixin
)
from openpype.lib import (
    BoolDef,
    NumberDef,
    TextDef,
    EnumDef
)
from openpype.hosts.maya.api.lib_rendersettings import RenderSettings
from openpype.hosts.maya.api.lib import get_attr_in_layer

from openpype_modules.deadline import abstract_submit_deadline
from openpype_modules.deadline.abstract_submit_deadline import DeadlineJobInfo
from openpype.tests.lib import is_in_tests
from openpype.lib import is_running_from_build
from openpype.pipeline.farm.tools import iter_expected_files


def _validate_deadline_bool_value(instance, attribute, value):
    if not isinstance(value, (str, bool)):
        raise TypeError(
            "Attribute {} must be str or bool.".format(attribute))
    if value not in {"1", "0", True, False}:
        raise ValueError(
            ("Value of {} must be one of "
             "'0', '1', True, False").format(attribute)
        )


@attr.s
class MayaPluginInfo(object):
    SceneFile = attr.ib(default=None)   # Input
    OutputFilePath = attr.ib(default=None)  # Output directory and filename
    OutputFilePrefix = attr.ib(default=None)
    Version = attr.ib(default=None)  # Mandatory for Deadline
    UsingRenderLayers = attr.ib(default=True)
    RenderLayer = attr.ib(default=None)  # Render only this layer
    Renderer = attr.ib(default=None)
    ProjectPath = attr.ib(default=None)  # Resolve relative references
    # Include all lights flag
    RenderSetupIncludeLights = attr.ib(
        default="1", validator=_validate_deadline_bool_value)
    StrictErrorChecking = attr.ib(default=True)


@attr.s
class PythonPluginInfo(object):
    ScriptFile = attr.ib()
    Version = attr.ib(default="3.6")
    Arguments = attr.ib(default=None)
    SingleFrameOnly = attr.ib(default=None)


@attr.s
class VRayPluginInfo(object):
    InputFilename = attr.ib(default=None)   # Input
    SeparateFilesPerFrame = attr.ib(default=None)
    VRayEngine = attr.ib(default="V-Ray")
    Width = attr.ib(default=None)
    Height = attr.ib(default=None)  # Mandatory for Deadline
    OutputFilePath = attr.ib(default=True)
    OutputFileName = attr.ib(default=None)  # Render only this layer


@attr.s
class ArnoldPluginInfo(object):
    ArnoldFile = attr.ib(default=None)


class MayaSubmitDeadline(abstract_submit_deadline.AbstractSubmitDeadline,
                         OpenPypePyblishPluginMixin):

    label = "Submit Render to Deadline"
    hosts = ["maya"]
    families = ["renderlayer"]
    targets = ["local"]

    tile_assembler_plugin = "OpenPypeTileAssembler"
    priority = 50
    tile_priority = 50
    limit = []  # limit groups
    jobInfo = {}
    pluginInfo = {}
    group = "none"
    strict_error_checking = True

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        settings = project_settings["deadline"]["publish"]["MayaSubmitDeadline"]  # noqa

        # Take some defaults from settings
        cls.asset_dependencies = settings.get("asset_dependencies",
                                              cls.asset_dependencies)
        cls.import_reference = settings.get("import_reference",
                                            cls.import_reference)
        cls.use_published = settings.get("use_published", cls.use_published)
        cls.priority = settings.get("priority", cls.priority)
        cls.tile_priority = settings.get("tile_priority", cls.tile_priority)
        cls.limit = settings.get("limit", cls.limit)
        cls.group = settings.get("group", cls.group)
        cls.strict_error_checking = settings.get("strict_error_checking",
                                                 cls.strict_error_checking)
        cls.jobInfo = settings.get("jobInfo", cls.jobInfo)
        cls.pluginInfo = settings.get("pluginInfo", cls.pluginInfo)

    def get_job_info(self):
        job_info = DeadlineJobInfo(Plugin="MayaBatch")

        # todo: test whether this works for existing production cases
        #       where custom jobInfo was stored in the project settings
        job_info.update(self.jobInfo)

        instance = self._instance
        context = instance.context

        # Always use the original work file name for the Job name even when
        # rendering is done from the published Work File. The original work
        # file name is clearer because it can also have subversion strings,
        # etc. which are stripped for the published file.
        src_filepath = context.data["currentFile"]
        src_filename = os.path.basename(src_filepath)

        if is_in_tests():
            src_filename += datetime.now().strftime("%d%m%Y%H%M%S")

        job_info.Name = "%s - %s" % (src_filename, instance.name)
        job_info.BatchName = src_filename
        job_info.Plugin = instance.data.get("mayaRenderPlugin", "MayaBatch")
        job_info.UserName = context.data.get("deadlineUser", getpass.getuser())

        # Deadline requires integers in frame range
        frames = "{start}-{end}x{step}".format(
            start=int(instance.data["frameStartHandle"]),
            end=int(instance.data["frameEndHandle"]),
            step=int(instance.data["byFrameStep"]),
        )
        job_info.Frames = frames

        job_info.Pool = instance.data.get("primaryPool")
        job_info.SecondaryPool = instance.data.get("secondaryPool")
        job_info.Comment = context.data.get("comment")
        job_info.Priority = instance.data.get("priority", self.priority)

        if self.group != "none" and self.group:
            job_info.Group = self.group

        if self.limit:
            job_info.LimitGroups = ",".join(self.limit)

        attr_values = self.get_attr_values_from_data(instance.data)
        render_globals = instance.data.setdefault("renderGlobals", dict())
        machine_list = attr_values.get("machineList", "")
        if machine_list:
            if attr_values.get("whitelist", True):
                machine_list_key = "Whitelist"
            else:
                machine_list_key = "Blacklist"
            render_globals[machine_list_key] = machine_list

        job_info.Priority = attr_values.get("priority")
        job_info.ChunkSize = attr_values.get("chunkSize")

        # Add options from RenderGlobals
        render_globals = instance.data.get("renderGlobals", {})
        job_info.update(render_globals)

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "OPENPYPE_SG_USER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "OPENPYPE_DEV"
            "IS_TEST"
        ]

        # Add OpenPype version if we are running from build.
        if is_running_from_build():
            keys.append("OPENPYPE_VERSION")

        # Add mongo url if it's enabled
        if self._instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        for key in keys:
            value = environment.get(key)
            if not value:
                continue
            job_info.EnvironmentKeyValue[key] = value

        # to recognize render jobs
        job_info.add_render_job_env_var()
        job_info.EnvironmentKeyValue["OPENPYPE_LOG_NO_COLORS"] = "1"

        # Adding file dependencies.
        if not bool(os.environ.get("IS_TEST")) and self.asset_dependencies:
            dependencies = instance.context.data["fileDependencies"]
            for dependency in dependencies:
                job_info.AssetDependency += dependency

        # Add list of expected files to job
        # ---------------------------------
        exp = instance.data.get("expectedFiles")
        for filepath in iter_expected_files(exp):
            job_info.OutputDirectory += os.path.dirname(filepath)
            job_info.OutputFilename += os.path.basename(filepath)

        return job_info

    def get_plugin_info(self):
        # Not all hosts can import this module.
        from maya import cmds

        instance = self._instance
        context = instance.context

        # Set it to default Maya behaviour if it cannot be determined
        # from instance (but it should be, by the Collector).

        default_rs_include_lights = (
            instance.context.data['project_settings']
                                 ['maya']
                                 ['RenderSettings']
                                 ['enable_all_lights']
        )

        rs_include_lights = instance.data.get(
            "renderSetupIncludeLights", default_rs_include_lights)
        if rs_include_lights not in {"1", "0", True, False}:
            rs_include_lights = default_rs_include_lights

        attr_values = self.get_attr_values_from_data(instance.data)
        strict_error_checking = attr_values.get("strict_error_checking",
                                                self.strict_error_checking)
        plugin_info = MayaPluginInfo(
            SceneFile=self.scene_path,
            Version=cmds.about(version=True),
            RenderLayer=instance.data['setMembers'],
            Renderer=instance.data["renderer"],
            RenderSetupIncludeLights=rs_include_lights,  # noqa
            ProjectPath=context.data["workspaceDir"],
            UsingRenderLayers=True,
            StrictErrorChecking=strict_error_checking
        )

        plugin_payload = attr.asdict(plugin_info)

        # Patching with pluginInfo from settings
        for key, value in self.pluginInfo.items():
            plugin_payload[key] = value

        return plugin_payload

    def process_submission(self):
        from maya import cmds
        instance = self._instance

        filepath = self.scene_path  # publish if `use_publish` else workfile

        # TODO: Avoid the need for this logic here, needed for submit publish
        # Store output dir for unified publisher (filesequence)
        expected_files = instance.data["expectedFiles"]
        first_file = next(iter_expected_files(expected_files))
        output_dir = os.path.dirname(first_file)
        instance.data["outputDir"] = output_dir

        # Patch workfile (only when use_published is enabled)
        if self.use_published:
            self._patch_workfile()

        # Gather needed data ------------------------------------------------
        filename = os.path.basename(filepath)
        dirname = os.path.join(
            cmds.workspace(query=True, rootDirectory=True),
            cmds.workspace(fileRuleEntry="images")
        )

        # Fill in common data to payload ------------------------------------
        # TODO: Replace these with collected data from CollectRender
        payload_data = {
            "filename": filename,
            "dirname": dirname,
        }

        # Submit preceding export jobs -------------------------------------
        export_job = None
        assert not all(x in instance.data["families"]
                       for x in ['vrayscene', 'assscene']), (
            "Vray Scene and Ass Scene options are mutually exclusive")

        if "vrayscene" in instance.data["families"]:
            self.log.debug("Submitting V-Ray scene render..")
            vray_export_payload = self._get_vray_export_payload(payload_data)
            export_job = self.submit(vray_export_payload)

            payload = self._get_vray_render_payload(payload_data)

        else:
            self.log.debug("Submitting MayaBatch render..")
            payload = self._get_maya_payload(payload_data)

        # Add export job as dependency --------------------------------------
        if export_job:
            job_info, _ = payload
            job_info.JobDependencies = export_job

        if instance.data.get("tileRendering"):
            # Prepare tiles data
            self._tile_render(payload)
        else:
            # Submit main render job
            job_info, plugin_info = payload
            self.submit(self.assemble_payload(job_info, plugin_info))

    def _tile_render(self, payload):
        """Submit as tile render per frame with dependent assembly jobs."""

        # As collected by super process()
        instance = self._instance

        payload_job_info, payload_plugin_info = payload
        job_info = copy.deepcopy(payload_job_info)
        plugin_info = copy.deepcopy(payload_plugin_info)

        # Force plugin reload for vray cause the region does not get flushed
        # between tile renders.
        if plugin_info["Renderer"] == "vray":
            job_info.ForceReloadPlugin = True

        # if we have sequence of files, we need to create tile job for
        # every frame
        job_info.TileJob = True
        job_info.TileJobTilesInX = instance.data.get("tilesX")
        job_info.TileJobTilesInY = instance.data.get("tilesY")

        tiles_count = job_info.TileJobTilesInX * job_info.TileJobTilesInY

        plugin_info["ImageHeight"] = instance.data.get("resolutionHeight")
        plugin_info["ImageWidth"] = instance.data.get("resolutionWidth")
        plugin_info["RegionRendering"] = True

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
                # if beauty doesn't exist, use first aov we found
                files = exp[0].get(list(exp[0].keys())[0])
        else:
            files = exp
            assembly_files = files

        # Define frame tile jobs
        frame_file_hash = {}
        frame_payloads = {}
        file_index = 1
        for file in files:
            frame = re.search(R_FRAME_NUMBER, file).group("frame")

            new_job_info = copy.deepcopy(job_info)
            new_job_info.Name += " (Frame {} - {} tiles)".format(frame,
                                                                 tiles_count)
            new_job_info.TileJobFrame = frame

            new_plugin_info = copy.deepcopy(plugin_info)

            # Add tile data into job info and plugin info
            tiles_data = _format_tiles(
                file, 0,
                instance.data.get("tilesX"),
                instance.data.get("tilesY"),
                instance.data.get("resolutionWidth"),
                instance.data.get("resolutionHeight"),
                payload_plugin_info["OutputFilePrefix"]
            )[0]

            new_job_info.update(tiles_data["JobInfo"])
            new_plugin_info.update(tiles_data["PluginInfo"])

            self.log.debug("hashing {} - {}".format(file_index, file))
            job_hash = hashlib.sha256(
                ("{}_{}".format(file_index, file)).encode("utf-8"))

            file_hash = job_hash.hexdigest()
            frame_file_hash[frame] = file_hash

            new_job_info.ExtraInfo[0] = file_hash
            new_job_info.ExtraInfo[1] = file

            frame_payloads[frame] = self.assemble_payload(
                job_info=new_job_info,
                plugin_info=new_plugin_info
            )
            file_index += 1

        self.log.debug(
            "Submitting tile job(s) [{}] ...".format(len(frame_payloads)))

        # Submit frame tile jobs
        frame_tile_job_id = {}
        for frame, tile_job_payload in frame_payloads.items():
            job_id = self.submit(tile_job_payload)
            frame_tile_job_id[frame] = job_id

        # Define assembly payloads
        assembly_job_info = copy.deepcopy(job_info)
        assembly_job_info.Plugin = self.tile_assembler_plugin
        assembly_job_info.Name += " - Tile Assembly Job"
        assembly_job_info.Frames = 1
        assembly_job_info.MachineLimit = 1

        attr_values = self.get_attr_values_from_data(instance.data)
        assembly_job_info.Priority = attr_values.get("tile_priority",
                                                     self.tile_priority)
        assembly_job_info.TileJob = False

        # TODO: This should be a new publisher attribute definition
        pool = instance.context.data["project_settings"]["deadline"]
        pool = pool["publish"]["ProcessSubmittedJobOnFarm"]["deadline_pool"]
        assembly_job_info.Pool = pool or instance.data.get("primaryPool", "")

        assembly_plugin_info = {
            "CleanupTiles": 1,
            "ErrorOnMissing": True,
            "Renderer": self._instance.data["renderer"]
        }

        assembly_payloads = []
        output_dir = self.job_info.OutputDirectory[0]
        config_files = []
        for file in assembly_files:
            frame = re.search(R_FRAME_NUMBER, file).group("frame")

            frame_assembly_job_info = copy.deepcopy(assembly_job_info)
            frame_assembly_job_info.Name += " (Frame {})".format(frame)
            frame_assembly_job_info.OutputFilename[0] = re.sub(
                REPL_FRAME_NUMBER,
                "\\1{}\\3".format("#" * len(frame)), file)

            file_hash = frame_file_hash[frame]
            tile_job_id = frame_tile_job_id[frame]

            frame_assembly_job_info.ExtraInfo[0] = file_hash
            frame_assembly_job_info.ExtraInfo[1] = file
            frame_assembly_job_info.JobDependencies = tile_job_id
            frame_assembly_job_info.Frames = frame

            # write assembly job config files
            config_file = os.path.join(
                output_dir,
                "{}_config_{}.txt".format(
                    os.path.splitext(file)[0],
                    datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                )
            )
            config_files.append(config_file)
            try:
                if not os.path.isdir(output_dir):
                    os.makedirs(output_dir)
            except OSError:
                # directory is not available
                self.log.warning("Path is unreachable: "
                                 "`{}`".format(output_dir))

            with open(config_file, "w") as cf:
                print("TileCount={}".format(tiles_count), file=cf)
                print("ImageFileName={}".format(file), file=cf)
                print("ImageWidth={}".format(
                    instance.data.get("resolutionWidth")), file=cf)
                print("ImageHeight={}".format(
                    instance.data.get("resolutionHeight")), file=cf)

            reversed_y = False
            if plugin_info["Renderer"] == "arnold":
                reversed_y = True

            with open(config_file, "a") as cf:
                # Need to reverse the order of the y tiles, because image
                # coordinates are calculated from bottom left corner.
                tiles = _format_tiles(
                    file, 0,
                    instance.data.get("tilesX"),
                    instance.data.get("tilesY"),
                    instance.data.get("resolutionWidth"),
                    instance.data.get("resolutionHeight"),
                    payload_plugin_info["OutputFilePrefix"],
                    reversed_y=reversed_y
                )[1]
                for k, v in sorted(tiles.items()):
                    print("{}={}".format(k, v), file=cf)

            assembly_payloads.append(
                self.assemble_payload(
                    job_info=frame_assembly_job_info,
                    plugin_info=assembly_plugin_info.copy(),
                    # This would fail if the client machine and webserice are
                    # using different storage paths.
                    aux_files=[config_file]
                )
            )

        # Submit assembly jobs
        assembly_job_ids = []
        num_assemblies = len(assembly_payloads)
        for i, payload in enumerate(assembly_payloads):
            self.log.debug(
                "submitting assembly job {} of {}".format(i + 1,
                                                          num_assemblies)
            )
            assembly_job_id = self.submit(payload)
            assembly_job_ids.append(assembly_job_id)

        instance.data["assemblySubmissionJobs"] = assembly_job_ids

        # Remove config files to avoid confusion about where data is coming
        # from in Deadline.
        for config_file in config_files:
            os.remove(config_file)

    def _get_maya_payload(self, data):

        job_info = copy.deepcopy(self.job_info)

        if not bool(os.environ.get("IS_TEST")) and self.asset_dependencies:
            # Asset dependency to wait for at least the scene file to sync.
            job_info.AssetDependency += self.scene_path

        # Get layer prefix
        renderlayer = self._instance.data["setMembers"]
        renderer = self._instance.data["renderer"]
        layer_prefix_attr = RenderSettings.get_image_prefix_attr(renderer)
        layer_prefix = get_attr_in_layer(layer_prefix_attr, layer=renderlayer)

        plugin_info = copy.deepcopy(self.plugin_info)
        plugin_info.update({
            # Output directory and filename
            "OutputFilePath": data["dirname"].replace("\\", "/"),
            "OutputFilePrefix": layer_prefix,
        })

        # This hack is here because of how Deadline handles Renderman version.
        # it considers everything with `renderman` set as version older than
        # Renderman 22, and so if we are using renderman > 21 we need to set
        # renderer string on the job to `renderman22`. We will have to change
        # this when Deadline releases new version handling this.
        renderer = self._instance.data["renderer"]
        if renderer == "renderman":
            try:
                from rfm2.config import cfg  # noqa
            except ImportError:
                raise Exception("Cannot determine renderman version")

            rman_version = cfg().build_info.version()  # type: str
            if int(rman_version.split(".")[0]) > 22:
                renderer = "renderman22"

            plugin_info["Renderer"] = renderer

            # this is needed because renderman plugin in Deadline
            # handles directory and file prefixes separately
            plugin_info["OutputFilePath"] = job_info.OutputDirectory[0]

        return job_info, plugin_info

    def _get_vray_export_payload(self, data):

        job_info = copy.deepcopy(self.job_info)
        job_info.Name = self._job_info_label("Export")

        # Get V-Ray settings info to compute output path
        vray_scene = self.format_vray_output_filename()

        plugin_info = {
            "Renderer": "vray",
            "SkipExistingFrames": True,
            "UseLegacyRenderLayers": True,
            "OutputFilePath": os.path.dirname(vray_scene)
        }

        return job_info, attr.asdict(plugin_info)

    def _get_vray_render_payload(self, data):

        # Job Info
        job_info = copy.deepcopy(self.job_info)
        job_info.Name = self._job_info_label("Render")
        job_info.Plugin = "Vray"
        job_info.OverrideTaskExtraInfoNames = False

        # Plugin Info
        plugin_info = VRayPluginInfo(
            InputFilename=self.format_vray_output_filename(),
            SeparateFilesPerFrame=False,
            VRayEngine="V-Ray",
            Width=self._instance.data["resolutionWidth"],
            Height=self._instance.data["resolutionHeight"],
            OutputFilePath=job_info.OutputDirectory[0],
            OutputFileName=job_info.OutputFilename[0]
        )

        return job_info, attr.asdict(plugin_info)

    def _get_arnold_render_payload(self, data):
        from maya import cmds
        # Job Info
        job_info = copy.deepcopy(self.job_info)
        job_info.Name = self._job_info_label("Render")
        job_info.Plugin = "Arnold"
        job_info.OverrideTaskExtraInfoNames = False

        # Plugin Info
        ass_file, _ = os.path.splitext(data["output_filename_0"])
        ass_filepath = ass_file + ".ass"

        plugin_info = ArnoldPluginInfo(
            ArnoldFile=ass_filepath
        )

        return job_info, attr.asdict(plugin_info)

    def format_vray_output_filename(self):
        """Format the expected output file of the Export job.

        Example:
            <Scene>/<Scene>_<Layer>/<Layer>
            "shot010_v006/shot010_v006_CHARS/CHARS_0001.vrscene"
        Returns:
            str

        """
        from maya import cmds
        # "vrayscene/<Scene>/<Scene>_<Layer>/<Layer>"
        vray_settings = cmds.ls(type="VRaySettingsNode")
        node = vray_settings[0]
        template = cmds.getAttr("{}.vrscene_filename".format(node))
        scene, _ = os.path.splitext(self.scene_path)

        def smart_replace(string, key_values):
            new_string = string
            for key, value in key_values.items():
                new_string = new_string.replace(key, value)
            return new_string

        # Get workfile scene path without extension to format vrscene_filename
        scene_filename = os.path.basename(self.scene_path)
        scene_filename_no_ext, _ = os.path.splitext(scene_filename)

        layer = self._instance.data['setMembers']

        # Reformat without tokens
        output_path = smart_replace(
            template,
            {"<Scene>": scene_filename_no_ext,
             "<Layer>": layer})

        start_frame = int(self._instance.data["frameStartHandle"])
        workspace = self._instance.context.data["workspace"]
        filename_zero = "{}_{:04d}.vrscene".format(output_path, start_frame)
        filepath_zero = os.path.join(workspace, filename_zero)

        return filepath_zero.replace("\\", "/")

    def _patch_workfile(self):
        """Patch Maya scene.

        This will take list of patches (lines to add) and apply them to
        *published* Maya  scene file (that is used later for rendering).

        Patches are dict with following structure::
            {
                "name": "Name of patch",
                "regex": "regex of line before patch",
                "line": "line to insert"
            }

        """
        project_settings = self._instance.context.data["project_settings"]
        patches = (
            project_settings.get(
                "deadline", {}).get(
                "publish", {}).get(
                "MayaSubmitDeadline", {}).get(
                "scene_patches", {})
        )
        if not patches:
            return

        if not os.path.splitext(self.scene_path)[1].lower() != ".ma":
            self.log.debug("Skipping workfile patch since workfile is not "
                           ".ma file")
            return

        compiled_regex = [re.compile(p["regex"]) for p in patches]
        with open(self.scene_path, "r+") as pf:
            scene_data = pf.readlines()
            for ln, line in enumerate(scene_data):
                for i, r in enumerate(compiled_regex):
                    if re.match(r, line):
                        scene_data.insert(ln + 1, patches[i]["line"])
                        pf.seek(0)
                        pf.writelines(scene_data)
                        pf.truncate()
                        self.log.info("Applied {} patch to scene.".format(
                            patches[i]["name"]
                        ))

    def _job_info_label(self, label):
        return "{label} {job.Name} [{start}-{end}]".format(
            label=label,
            job=self.job_info,
            start=int(self._instance.data["frameStartHandle"]),
            end=int(self._instance.data["frameEndHandle"]),
        )

    @classmethod
    def get_attribute_defs(cls):
        defs = super(MayaSubmitDeadline, cls).get_attribute_defs()

        defs.extend([
            NumberDef("priority",
                      label="Priority",
                      default=cls.default_priority,
                      decimals=0),
            NumberDef("chunkSize",
                      label="Frames Per Task",
                      default=1,
                      decimals=0,
                      minimum=1,
                      maximum=1000),
            TextDef("machineList",
                    label="Machine List",
                    default="",
                    placeholder="machine1,machine2"),
            EnumDef("whitelist",
                    label="Machine List (Allow/Deny)",
                    items={
                        True: "Allow List",
                        False: "Deny List",
                    },
                    default=False),
            NumberDef("tile_priority",
                      label="Tile Assembler Priority",
                      decimals=0,
                      default=cls.tile_priority),
            BoolDef("strict_error_checking",
                    label="Strict Error Checking",
                    default=cls.strict_error_checking),

        ])

        return defs

def _format_tiles(
        filename,
        index,
        tiles_x,
        tiles_y,
        width,
        height,
        prefix,
        reversed_y=False
):
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
        `<Scene>/<RenderLayer>/<RenderLayer>_<RenderPass>`

        Result for tile 0 for 4x4 will be:
        `<Scene>/<RenderLayer>/_tile_1x1_4x4_<RenderLayer>_<RenderPass>`

        Calculating coordinates is tricky as in Job they are defined as top,
    left, bottom, right with zero being in top-left corner. But Assembler
    configuration file takes tile coordinates as X, Y, Width and Height and
    zero is bottom left corner.

    Args:
        filename (str): Filename to process as tiles.
        index (int): Index of that file if it is sequence.
        tiles_x (int): Number of tiles in X.
        tiles_y (int): Number of tiles in Y.
        width (int): Width resolution of final image.
        height (int):  Height resolution of final image.
        prefix (str): Image prefix.
        reversed_y (bool): Reverses the order of the y tiles.

    Returns:
        (dict, dict): Tuple of two dictionaries - first can be used to
                      extend JobInfo, second has tiles x, y, width and height
                      used for assembler configuration.

    """
    # Math used requires integers for correct output - as such
    # we ensure our inputs are correct.
    assert type(tiles_x) is int, "tiles_x must be an integer"
    assert type(tiles_y) is int, "tiles_y must be an integer"
    assert type(width) is int, "width must be an integer"
    assert type(height) is int, "height must be an integer"

    out = {"JobInfo": {}, "PluginInfo": {}}
    cfg = OrderedDict()
    w_space = width // tiles_x
    h_space = height // tiles_y

    cfg["TilesCropped"] = "False"

    tile = 0
    range_y = range(1, tiles_y + 1)
    reversed_y_range = list(reversed(range_y))
    for tile_x in range(1, tiles_x + 1):
        for i, tile_y in enumerate(range_y):
            tile_y_index = tile_y
            if reversed_y:
                tile_y_index = reversed_y_range[i]

            tile_prefix = "_tile_{}x{}_{}x{}_".format(
                tile_x, tile_y_index, tiles_x, tiles_y
            )

            new_filename = "{}/{}{}".format(
                os.path.dirname(filename),
                tile_prefix,
                os.path.basename(filename)
            )

            top = height - (tile_y * h_space)
            bottom = height - ((tile_y - 1) * h_space) - 1
            left = (tile_x - 1) * w_space
            right = (tile_x * w_space) - 1

            # Job info
            key = "OutputFilename{}".format(index)
            out["JobInfo"][key] = new_filename

            # Plugin Info
            key = "RegionPrefix{}".format(str(tile))
            out["PluginInfo"][key] = "/{}".format(
                tile_prefix
            ).join(prefix.rsplit("/", 1))
            out["PluginInfo"]["RegionTop{}".format(tile)] = top
            out["PluginInfo"]["RegionBottom{}".format(tile)] = bottom
            out["PluginInfo"]["RegionLeft{}".format(tile)] = left
            out["PluginInfo"]["RegionRight{}".format(tile)] = right

            # Tile config
            cfg["Tile{}FileName".format(tile)] = new_filename
            cfg["Tile{}X".format(tile)] = left
            cfg["Tile{}Y".format(tile)] = top
            cfg["Tile{}Width".format(tile)] = w_space
            cfg["Tile{}Height".format(tile)] = h_space

            tile += 1

    return out, cfg
