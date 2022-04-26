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
import json
import getpass
import copy
import re
import hashlib
from datetime import datetime
import itertools
from collections import OrderedDict

import clique
import requests

from maya import cmds

import pyblish.api

from openpype.lib import requests_post
from openpype.hosts.maya.api import lib
from openpype.pipeline import legacy_io

# Documentation for keys available at:
# https://docs.thinkboxsoftware.com
#    /products/deadline/8.0/1_User%20Manual/manual
#    /manual-submission.html#job-info-file-options

payload_skeleton_template = {
    "JobInfo": {
        "BatchName": None,  # Top-level group name
        "Name": None,  # Job name, as seen in Monitor
        "UserName": None,
        "Plugin": "MayaBatch",
        "Frames": "{start}-{end}x{step}",
        "Comment": None,
        "Priority": 50,
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


class MayaSubmitDeadline(pyblish.api.InstancePlugin):
    """Submit available render layers to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via settings key "DEADLINE_REST_URL".

    Attributes:
        use_published (bool): Use published scene to render instead of the
            one in work area.

    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["maya"]
    families = ["renderlayer"]

    use_published = True
    tile_assembler_plugin = "OpenPypeTileAssembler"
    asset_dependencies = False
    priority = 50
    tile_priority = 50
    limit_groups = []
    jobInfo = {}
    pluginInfo = {}
    group = "none"

    def process(self, instance):
        """Plugin entry point."""
        instance.data["toBeRenderedOn"] = "deadline"
        context = instance.context

        self._instance = instance
        self.payload_skeleton = copy.deepcopy(payload_skeleton_template)

        # get default deadline webservice url from deadline module
        self.deadline_url = instance.context.data.get("defaultDeadline")
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            self.deadline_url = instance.data.get("deadlineUrl")
        assert self.deadline_url, "Requires Deadline Webservice URL"

        # just using existing names from Setting
        self._job_info = self.jobInfo

        self._plugin_info = self.pluginInfo

        self.limit_groups = self.limit

        context = instance.context
        workspace = context.data["workspaceDir"]
        anatomy = context.data['anatomy']
        instance.data["toBeRenderedOn"] = "deadline"

        filepath = None
        patches = (
            context.data["project_settings"].get(
                "deadline", {}).get(
                "publish", {}).get(
                "MayaSubmitDeadline", {}).get(
                "scene_patches", {})
        )

        # Handle render/export from published scene or not ------------------
        if self.use_published:
            patched_files = []
            for i in context:
                if "workfile" not in i.data["families"]:
                    continue
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

                if instance.data.get("publishRenderMetadataFolder"):
                    instance.data["publishRenderMetadataFolder"] = \
                        instance.data["publishRenderMetadataFolder"].replace(
                            orig_scene, new_scene)
                self.log.info("Scene name was switched {} -> {}".format(
                    orig_scene, new_scene
                ))
                # patch workfile is needed
                if filepath not in patched_files:
                    patched_file = self._patch_workfile(filepath, patches)
                    patched_files.append(patched_file)

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
        default_render_file = instance.context.data.get('project_settings')\
            .get('maya')\
            .get('create')\
            .get('CreateRender')\
            .get('default_render_image_folder')
        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        dirname = os.path.join(workspace, default_render_file)
        renderlayer = instance.data['setMembers']       # rs_beauty
        deadline_user = context.data.get("user", getpass.getuser())

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

        dirname = os.path.dirname(output_filename_0)

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

        self.log.info("--- Submission data:")
        for k, v in payload_data.items():
            self.log.info("- {}: {}".format(k, v))
        self.log.info("-" * 20)

        frame_pattern = self.payload_skeleton["JobInfo"]["Frames"]
        self.payload_skeleton["JobInfo"]["Frames"] = frame_pattern.format(
            start=int(self._instance.data["frameStartHandle"]),
            end=int(self._instance.data["frameEndHandle"]),
            step=int(self._instance.data["byFrameStep"]))

        self.payload_skeleton["JobInfo"]["Plugin"] = self._instance.data.get(
            "mayaRenderPlugin", "MayaBatch")

        self.payload_skeleton["JobInfo"]["BatchName"] = src_filename
        # Job name, as seen in Monitor
        self.payload_skeleton["JobInfo"]["Name"] = jobname
        # Arbitrary username, for visualisation in Monitor
        self.payload_skeleton["JobInfo"]["UserName"] = deadline_user
        # Set job priority
        self.payload_skeleton["JobInfo"]["Priority"] = \
            self._instance.data.get("priority", self.priority)

        if self.group != "none" and self.group:
            self.payload_skeleton["JobInfo"]["Group"] = self.group

        if self.limit_groups:
            self.payload_skeleton["JobInfo"]["LimitGroups"] = \
                ",".join(self.limit_groups)
        # Optional, enable double-click to preview rendered
        # frames from Deadline Monitor
        self.payload_skeleton["JobInfo"]["OutputDirectory0"] = \
            os.path.dirname(output_filename_0).replace("\\", "/")
        self.payload_skeleton["JobInfo"]["OutputFilename0"] = \
            output_filename_0.replace("\\", "/")

        self.payload_skeleton["JobInfo"]["Comment"] = comment
        self.payload_skeleton["PluginInfo"]["RenderLayer"] = renderlayer

        # Adding file dependencies.
        dependencies = instance.context.data["fileDependencies"]
        dependencies.append(filepath)
        if self.asset_dependencies:
            for dependency in dependencies:
                key = "AssetDependency" + str(dependencies.index(dependency))
                self.payload_skeleton["JobInfo"][key] = dependency

        # Handle environments -----------------------------------------------
        # We need those to pass them to pype for it to set correct context
        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "OPENPYPE_DEV",
            "OPENPYPE_LOG_NO_COLORS"
        ]
        # Add mongo url if it's enabled
        if instance.context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)
        environment["OPENPYPE_LOG_NO_COLORS"] = "1"
        environment["OPENPYPE_MAYA_VERSION"] = cmds.about(v=True)
        # to recognize job from PYPE for turning Event On/Off
        environment["OPENPYPE_RENDER_JOB"] = "1"
        self.payload_skeleton["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })
        # Add options from RenderGlobals-------------------------------------
        render_globals = instance.data.get("renderGlobals", {})
        self.payload_skeleton["JobInfo"].update(render_globals)

        # Submit preceding export jobs -------------------------------------
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
        exp_index = 0
        output_filenames = {}

        if isinstance(exp[0], dict):
            # we have aovs and we need to iterate over them
            for _aov, files in exp[0].items():
                col, rem = clique.assemble(files)
                if not col and rem:
                    # we couldn't find any collections but have
                    # individual files.
                    assert len(rem) == 1, ("Found multiple non related files "
                                           "to render, don't know what to do "
                                           "with them.")
                    output_file = rem[0]
                    if not instance.data.get("tileRendering"):
                        payload['JobInfo']['OutputFilename' + str(exp_index)] = output_file  # noqa: E501
                else:
                    output_file = col[0].format('{head}{padding}{tail}')
                    if not instance.data.get("tileRendering"):
                        payload['JobInfo']['OutputFilename' + str(exp_index)] = output_file  # noqa: E501

                output_filenames['OutputFilename' + str(exp_index)] = output_file  # noqa: E501
                exp_index += 1
        else:
            col, rem = clique.assemble(exp)
            if not col and rem:
                # we couldn't find any collections but have
                # individual files.
                assert len(rem) == 1, ("Found multiple non related files "
                                       "to render, don't know what to do "
                                       "with them.")

                output_file = rem[0]
                if not instance.data.get("tileRendering"):
                    payload['JobInfo']['OutputFilename' + str(exp_index)] = output_file  # noqa: E501
            else:
                output_file = col[0].format('{head}{padding}{tail}')
                if not instance.data.get("tileRendering"):
                    payload['JobInfo']['OutputFilename' + str(exp_index)] = output_file  # noqa: E501

            output_filenames['OutputFilename' + str(exp_index)] = output_file

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("using render plugin : {}".format(plugin))

        # Store output dir for unified publisher (filesequence)
        instance.data["outputDir"] = os.path.dirname(output_filename_0)

        self.preflight_check(instance)

        # add jobInfo and pluginInfo variables from Settings
        payload["JobInfo"].update(self._job_info)
        payload["PluginInfo"].update(self._plugin_info)

        # Prepare tiles data ------------------------------------------------
        if instance.data.get("tileRendering"):
            # if we have sequence of files, we need to create tile job for
            # every frame

            payload["JobInfo"]["TileJob"] = True
            payload["JobInfo"]["TileJobTilesInX"] = instance.data.get("tilesX")
            payload["JobInfo"]["TileJobTilesInY"] = instance.data.get("tilesY")
            payload["PluginInfo"]["ImageHeight"] = instance.data.get("resolutionHeight")  # noqa: E501
            payload["PluginInfo"]["ImageWidth"] = instance.data.get("resolutionWidth")  # noqa: E501
            payload["PluginInfo"]["RegionRendering"] = True

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
            assembly_payload["JobInfo"].update(output_filenames)
            assembly_payload["JobInfo"]["Priority"] = self._instance.data.get(
                "tile_priority", self.tile_priority)
            assembly_payload["JobInfo"]["UserName"] = deadline_user

            frame_payloads = []
            assembly_payloads = []

            R_FRAME_NUMBER = re.compile(r".+\.(?P<frame>[0-9]+)\..+")  # noqa: N806, E501
            REPL_FRAME_NUMBER = re.compile(r"(.+\.)([0-9]+)(\..+)")  # noqa: N806, E501

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
                        instance.data.get("tilesX") * instance.data.get("tilesY")  # noqa: E501
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

                job_hash = hashlib.sha256("{}_{}".format(file_index, file))
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

                new_assembly_payload["PluginInfo"]["Renderer"] = self._instance.data["renderer"]  # noqa: E501
                new_assembly_payload["JobInfo"]["ExtraInfo0"] = frame_jobs[frame]  # noqa: E501
                new_assembly_payload["JobInfo"]["ExtraInfo1"] = file
                assembly_payloads.append(new_assembly_payload)
                file_index += 1

            self.log.info(
                "Submitting tile job(s) [{}] ...".format(len(frame_payloads)))

            url = "{}/api/jobs".format(self.deadline_url)
            tiles_count = instance.data.get("tilesX") * instance.data.get("tilesY")  # noqa: E501

            for tile_job in frame_payloads:
                response = requests_post(url, json=tile_job)
                if not response.ok:
                    raise Exception(response.text)

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
                self.log.debug(json.dumps(ass_job, indent=4, sort_keys=True))
                response = requests_post(url, json=ass_job)
                if not response.ok:
                    raise Exception(response.text)

                instance.data["assemblySubmissionJobs"].append(
                    response.json()["_id"])
                job_idx += 1

            instance.data["jobBatchName"] = payload["JobInfo"]["BatchName"]
            self.log.info("Setting batch name on instance: {}".format(
                instance.data["jobBatchName"]))
        else:
            # Submit job to farm --------------------------------------------
            self.log.info("Submitting ...")
            self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

            # E.g. http://192.168.0.1:8082/api/jobs
            url = "{}/api/jobs".format(self.deadline_url)
            response = requests_post(url, json=payload)
            if not response.ok:
                raise Exception(response.text)
            instance.data["deadlineSubmissionJob"] = response.json()

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

    def _submit_export(self, data, format):
        if format == "vray":
            payload = self._get_vray_export_payload(data)
            self.log.info("Submitting vrscene export job.")
        elif format == "arnold":
            payload = self._get_arnold_export_payload(data)
            self.log.info("Submitting ass export job.")

        url = "{}/api/jobs".format(self.deadline_url)
        response = requests_post(url, json=payload)
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
