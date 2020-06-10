"""
This collector will go through render layers in maya and prepare all data
needed to create instances and their representations for submition and
publishing on farm.

Requires:
    instance    -> families
    instance    -> setMembers

    context     -> currentFile
    context     -> workspaceDir
    context     -> user

    session     -> AVALON_ASSET

Optional:

Provides:
    instance    -> label
    instance    -> subset
    instance    -> attachTo
    instance    -> setMembers
    instance    -> publish
    instance    -> frameStart
    instance    -> frameEnd
    instance    -> byFrameStep
    instance    -> renderer
    instance    -> family
    instance    -> families
    instance    -> asset
    instance    -> time
    instance    -> author
    instance    -> source
    instance    -> expectedFiles
    instance    -> resolutionWidth
    instance    -> resolutionHeight
    instance    -> pixelAspect
"""

import re
import os
import types
import six
import json
from abc import ABCMeta, abstractmethod

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api

from avalon import maya, api
from pype.hosts.maya import lib


R_SINGLE_FRAME = re.compile(r"^(-?)\d+$")
R_FRAME_RANGE = re.compile(r"^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+)$")
R_FRAME_NUMBER = re.compile(r".+\.(?P<frame>[0-9]+)\..+")
R_LAYER_TOKEN = re.compile(
    r".*((?:%l)|(?:<layer>)|(?:<renderlayer>)).*", re.IGNORECASE
)
R_AOV_TOKEN = re.compile(r".*%a.*|.*<aov>.*|.*<renderpass>.*", re.IGNORECASE)
R_SUBSTITUTE_AOV_TOKEN = re.compile(r"%a|<aov>|<renderpass>", re.IGNORECASE)
R_REMOVE_AOV_TOKEN = re.compile(r"(?:_|\.)((?:%a)|(?:<aov>)|(?:<renderpass>))",
                                re.IGNORECASE)
# to remove unused renderman tokens
R_CLEAN_FRAME_TOKEN = re.compile(r"\.?<f\d>\.?", re.IGNORECASE)
R_CLEAN_EXT_TOKEN = re.compile(r"\.?<ext>\.?", re.IGNORECASE)

R_SUBSTITUTE_LAYER_TOKEN = re.compile(
    r"%l|<layer>|<renderlayer>", re.IGNORECASE
)
R_SUBSTITUTE_CAMERA_TOKEN = re.compile(r"%c|<camera>", re.IGNORECASE)
R_SUBSTITUTE_SCENE_TOKEN = re.compile(r"%s|<scene>", re.IGNORECASE)

RENDERER_NAMES = {
    "mentalray": "MentalRay",
    "vray": "V-Ray",
    "arnold": "Arnold",
    "renderman": "Renderman",
    "redshift": "Redshift",
}

# not sure about the renderman image prefix
ImagePrefixes = {
    "mentalray": "defaultRenderGlobals.imageFilePrefix",
    "vray": "vraySettings.fileNamePrefix",
    "arnold": "defaultRenderGlobals.imageFilePrefix",
    "renderman": "rmanGlobals.imageFileFormat",
    "redshift": "defaultRenderGlobals.imageFilePrefix",
}


class CollectMayaRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"

    def process(self, context):
        render_instance = None
        for instance in context:
            if "rendering" in instance.data["families"]:
                render_instance = instance
                render_instance.data["remove"] = True

            # make sure workfile instance publishing is enabled
            if "workfile" in instance.data["families"]:
                instance.data["publish"] = True

        if not render_instance:
            self.log.info(
                "No render instance found, skipping render "
                "layer collection."
            )
            return

        render_globals = render_instance
        collected_render_layers = render_instance.data["setMembers"]
        filepath = context.data["currentFile"].replace("\\", "/")
        asset = api.Session["AVALON_ASSET"]
        workspace = context.data["workspaceDir"]

        self._rs = renderSetup.instance()
        current_layer = self._rs.getVisibleRenderLayer()
        maya_render_layers = {l.name(): l for l in self._rs.getRenderLayers()}

        self.maya_layers = maya_render_layers

        for layer in collected_render_layers:
            # every layer in set should start with `LAYER_` prefix
            try:
                expected_layer_name = re.search(r"^LAYER_(.*)", layer).group(1)
            except IndexError:
                msg = "Invalid layer name in set [ {} ]".format(layer)
                self.log.warnig(msg)
                continue

            self.log.info("processing %s" % layer)
            # check if layer is part of renderSetup
            if expected_layer_name not in maya_render_layers:
                msg = "Render layer [ {} ] is not in " "Render Setup".format(
                    expected_layer_name
                )
                self.log.warning(msg)
                continue

            # check if layer is renderable
            if not maya_render_layers[expected_layer_name].isRenderable():
                msg = "Render layer [ {} ] is not " "renderable".format(
                    expected_layer_name
                )
                self.log.warning(msg)
                continue

            # test if there are sets (subsets) to attach render to
            sets = cmds.sets(layer, query=True) or []
            attachTo = []
            if sets:
                for s in sets:
                    if "family" not in cmds.listAttr(s):
                        continue

                    attachTo.append(
                        {
                            "version": None,  # we need integrator for that
                            "subset": s,
                            "family": cmds.getAttr("{}.family".format(s)),
                        }
                    )
                    self.log.info(" -> attach render to: {}".format(s))

            layer_name = "rs_{}".format(expected_layer_name)

            # collect all frames we are expecting to be rendered
            renderer = cmds.getAttr(
                "defaultRenderGlobals.currentRenderer"
            ).lower()
            # handle various renderman names
            if renderer.startswith("renderman"):
                renderer = "renderman"

            # return all expected files for all cameras and aovs in given
            # frame range
            exf = ExpectedFiles()
            exp_files = exf.get(renderer, layer_name)
            self.log.info("multipart: {}".format(exf.multipart))
            assert exp_files, "no file names were generated, this is bug"

            # if we want to attach render to subset, check if we have AOV's
            # in expectedFiles. If so, raise error as we cannot attach AOV
            # (considered to be subset on its own) to another subset
            if attachTo:
                assert len(exp_files[0].keys()) == 1, (
                    "attaching multiple AOVs or renderable cameras to "
                    "subset is not supported"
                )

            # append full path
            full_exp_files = []
            aov_dict = {}

            # we either get AOVs or just list of files. List of files can
            # mean two things - there are no AOVs enabled or multipass EXR
            # is produced. In either case we treat those as `beauty`.
            if isinstance(exp_files[0], dict):
                for aov, files in exp_files[0].items():
                    full_paths = []
                    for ef in files:
                        full_path = os.path.join(workspace, "renders", ef)
                        full_path = full_path.replace("\\", "/")
                        full_paths.append(full_path)
                    aov_dict[aov] = full_paths
            else:
                full_paths = []
                for ef in exp_files:
                    full_path = os.path.join(workspace, "renders", ef)
                    full_path = full_path.replace("\\", "/")
                    full_paths.append(full_path)
                aov_dict["beauty"] = full_paths

            frame_start_render = int(self.get_render_attribute(
                "startFrame", layer=layer_name))
            frame_end_render = int(self.get_render_attribute(
                "endFrame", layer=layer_name))

            if (int(context.data['frameStartHandle']) == frame_start_render
                    and int(context.data['frameEndHandle']) == frame_end_render):  # noqa: W503, E501

                handle_start = context.data['handleStart']
                handle_end = context.data['handleEnd']
                frame_start = context.data['frameStart']
                frame_end = context.data['frameEnd']
                frame_start_handle = context.data['frameStartHandle']
                frame_end_handle = context.data['frameEndHandle']
            else:
                handle_start = 0
                handle_end = 0
                frame_start = frame_start_render
                frame_end = frame_end_render
                frame_start_handle = frame_start_render
                frame_end_handle = frame_end_render

            full_exp_files.append(aov_dict)
            self.log.info(full_exp_files)
            self.log.info("collecting layer: {}".format(layer_name))
            # Get layer specific settings, might be overrides
            data = {
                "subset": expected_layer_name,
                "attachTo": attachTo,
                "setMembers": layer_name,
                "multipartExr": exf.multipart,
                "publish": True,

                "handleStart": handle_start,
                "handleEnd": handle_end,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartHandle": frame_start_handle,
                "frameEndHandle": frame_end_handle,
                "byFrameStep": int(
                    self.get_render_attribute("byFrameStep",
                                              layer=layer_name)),
                "renderer": self.get_render_attribute("currentRenderer",
                                                      layer=layer_name),
                # instance subset
                "family": "renderlayer",
                "families": ["renderlayer"],
                "asset": asset,
                "time": api.time(),
                "author": context.data["user"],
                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": filepath,
                "expectedFiles": full_exp_files,
                "resolutionWidth": cmds.getAttr("defaultResolution.width"),
                "resolutionHeight": cmds.getAttr("defaultResolution.height"),
                "pixelAspect": cmds.getAttr("defaultResolution.pixelAspect"),
            }

            # Apply each user defined attribute as data
            for attr in cmds.listAttr(layer, userDefined=True) or list():
                try:
                    value = cmds.getAttr("{}.{}".format(layer, attr))
                except Exception:
                    # Some attributes cannot be read directly,
                    # such as mesh and color attributes. These
                    # are considered non-essential to this
                    # particular publishing pipeline.
                    value = None

                data[attr] = value

            # Include (optional) global settings
            # Get global overrides and translate to Deadline values
            overrides = self.parse_options(str(render_globals))
            data.update(**overrides)

            # Define nice label
            label = "{0} ({1})".format(expected_layer_name, data["asset"])
            label += "  [{0}-{1}]".format(
                int(data["frameStartHandle"]), int(data["frameEndHandle"])
            )

            instance = context.create_instance(expected_layer_name)
            instance.data["label"] = label
            instance.data.update(data)
            self.log.debug("data: {}".format(json.dumps(data, indent=4)))

        # Restore current layer.
        self.log.info("Restoring to {}".format(current_layer.name()))
        self._rs.switchToLayer(current_layer)

    def parse_options(self, render_globals):
        """Get all overrides with a value, skip those without

        Here's the kicker. These globals override defaults in the submission
        integrator, but an empty value means no overriding is made.
        Otherwise, Frames would override the default frames set under globals.

        Args:
            render_globals (str): collection of render globals

        Returns:
            dict: only overrides with values
        """

        attributes = maya.read(render_globals)

        options = {"renderGlobals": {}}
        options["renderGlobals"]["Priority"] = attributes["priority"]

        # Check for specific pools
        pool_a, pool_b = self._discover_pools(attributes)
        options["renderGlobals"].update({"Pool": pool_a})
        if pool_b:
            options["renderGlobals"].update({"SecondaryPool": pool_b})

        # Machine list
        machine_list = attributes["machineList"]
        if machine_list:
            key = "Whitelist" if attributes["whitelist"] else "Blacklist"
            options["renderGlobals"][key] = machine_list

        # Suspend publish job
        state = "Suspended" if attributes["suspendPublishJob"] else "Active"
        options["publishJobState"] = state

        chunksize = attributes.get("framesPerTask", 1)
        options["renderGlobals"]["ChunkSize"] = chunksize

        # Override frames should be False if extendFrames is False. This is
        # to ensure it doesn't go off doing crazy unpredictable things
        override_frames = False
        extend_frames = attributes.get("extendFrames", False)
        if extend_frames:
            override_frames = attributes.get("overrideExistingFrame", False)

        options["extendFrames"] = extend_frames
        options["overrideExistingFrame"] = override_frames

        maya_render_plugin = "MayaBatch"
        if not attributes.get("useMayaBatch", True):
            maya_render_plugin = "MayaCmd"

        options["mayaRenderPlugin"] = maya_render_plugin

        return options

    def _discover_pools(self, attributes):

        pool_a = None
        pool_b = None

        # Check for specific pools
        pool_b = []
        if "primaryPool" in attributes:
            pool_a = attributes["primaryPool"]
            if "secondaryPool" in attributes:
                pool_b = attributes["secondaryPool"]

        else:
            # Backwards compatibility
            pool_str = attributes.get("pools", None)
            if pool_str:
                pool_a, pool_b = pool_str.split(";")

        # Ensure empty entry token is caught
        if pool_b == "-":
            pool_b = None

        return pool_a, pool_b

    def _get_overrides(self, layer):
        rset = self.maya_layers[layer].renderSettingsCollectionInstance()
        return rset.getOverrides()

    def get_render_attribute(self, attr, layer):
        return lib.get_attr_in_layer(
            "defaultRenderGlobals.{}".format(attr), layer=layer
        )


class ExpectedFiles:
    multipart = False

    def get(self, renderer, layer):
        renderSetup.instance().switchToLayerUsingLegacyName(layer)

        if renderer.lower() == "arnold":
            return self._get_files(ExpectedFilesArnold(layer))
        elif renderer.lower() == "vray":
            return self._get_files(ExpectedFilesVray(layer))
        elif renderer.lower() == "redshift":
            return self._get_files(ExpectedFilesRedshift(layer))
        elif renderer.lower() == "mentalray":
            return self._get_files(ExpectedFilesMentalray(layer))
        elif renderer.lower() == "renderman":
            return self._get_files(ExpectedFilesRenderman(layer))
        else:
            raise UnsupportedRendererException(
                "unsupported {}".format(renderer)
            )

    def _get_files(self, renderer):
        files = renderer.get_files()
        self.multipart = renderer.multipart
        return files


@six.add_metaclass(ABCMeta)
class AExpectedFiles:
    renderer = None
    layer = None
    multipart = False

    def __init__(self, layer):
        self.layer = layer

    @abstractmethod
    def get_aovs(self):
        pass

    def get_renderer_prefix(self):
        try:
            file_prefix = cmds.getAttr(ImagePrefixes[self.renderer])
        except KeyError:
            raise UnsupportedRendererException(
                "Unsupported renderer {}".format(self.renderer)
            )
        return file_prefix

    def _get_layer_data(self):
        #                      ______________________________________________
        # ____________________/ ____________________________________________/
        # 1 -  get scene name  /__________________/
        # ____________________/
        scene_dir, scene_basename = os.path.split(cmds.file(q=True, loc=True))
        scene_name, _ = os.path.splitext(scene_basename)

        #                      ______________________________________________
        # ____________________/ ____________________________________________/
        # 2 -  detect renderer /__________________/
        # ____________________/
        renderer = self.renderer

        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 3 -  image prefix  /__________________/
        # __________________/
        file_prefix = self.get_renderer_prefix()

        if not file_prefix:
            raise RuntimeError("Image prefix not set")

        default_ext = cmds.getAttr("defaultRenderGlobals.imfPluginKey")

        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 4 -  get renderable cameras_____________/
        # __________________/

        # if we have <camera> token in prefix path we'll expect output for
        # every renderable camera in layer.

        renderable_cameras = self.get_renderable_cameras()
        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 5 -  get AOVs      /____________________/
        # __________________/

        enabled_aovs = self.get_aovs()

        layer_name = self.layer
        if self.layer.startswith("rs_"):
            layer_name = self.layer[3:]
        start_frame = int(self.get_render_attribute("startFrame"))
        end_frame = int(self.get_render_attribute("endFrame"))
        frame_step = int(self.get_render_attribute("byFrameStep"))
        padding = int(self.get_render_attribute("extensionPadding"))

        scene_data = {
            "frameStart": start_frame,
            "frameEnd": end_frame,
            "frameStep": frame_step,
            "padding": padding,
            "cameras": renderable_cameras,
            "sceneName": scene_name,
            "layerName": layer_name,
            "renderer": renderer,
            "defaultExt": default_ext,
            "filePrefix": file_prefix,
            "enabledAOVs": enabled_aovs,
        }
        return scene_data

    def _generate_single_file_sequence(self, layer_data, aov_name=None):
        expected_files = []
        file_prefix = layer_data["filePrefix"]
        for cam in layer_data["cameras"]:
            mappings = [
                (R_SUBSTITUTE_SCENE_TOKEN, layer_data["sceneName"]),
                (R_SUBSTITUTE_LAYER_TOKEN, layer_data["layerName"]),
                (R_SUBSTITUTE_CAMERA_TOKEN, cam),
                (R_CLEAN_FRAME_TOKEN, ""),
                (R_CLEAN_EXT_TOKEN, ""),
            ]
            # this is required to remove unfilled aov token, for example
            # in Redshift
            if aov_name:
                mappings.append((R_SUBSTITUTE_AOV_TOKEN, aov_name))
            else:
                mappings.append((R_REMOVE_AOV_TOKEN, ""))

            for regex, value in mappings:
                file_prefix = re.sub(regex, value, file_prefix)

            for frame in range(
                int(layer_data["frameStart"]),
                int(layer_data["frameEnd"]) + 1,
                int(layer_data["frameStep"]),
            ):
                expected_files.append(
                    "{}.{}.{}".format(
                        file_prefix,
                        str(frame).rjust(layer_data["padding"], "0"),
                        layer_data["defaultExt"],
                    )
                )
        return expected_files

    def _generate_aov_file_sequences(self, layer_data):
        expected_files = []
        aov_file_list = {}
        file_prefix = layer_data["filePrefix"]
        for aov in layer_data["enabledAOVs"]:
            for cam in layer_data["cameras"]:

                mappings = (
                    (R_SUBSTITUTE_SCENE_TOKEN, layer_data["sceneName"]),
                    (R_SUBSTITUTE_LAYER_TOKEN, layer_data["layerName"]),
                    (R_SUBSTITUTE_CAMERA_TOKEN, cam),
                    (R_SUBSTITUTE_AOV_TOKEN, aov[0]),
                    (R_CLEAN_FRAME_TOKEN, ""),
                    (R_CLEAN_EXT_TOKEN, ""),
                )

                for regex, value in mappings:
                    file_prefix = re.sub(regex, value, file_prefix)

                aov_files = []
                for frame in range(
                    int(layer_data["frameStart"]),
                    int(layer_data["frameEnd"]) + 1,
                    int(layer_data["frameStep"]),
                ):
                    aov_files.append(
                        "{}.{}.{}".format(
                            file_prefix,
                            str(frame).rjust(layer_data["padding"], "0"),
                            aov[1],
                        )
                    )

                # if we have more then one renderable camera, append
                # camera name to AOV to allow per camera AOVs.
                aov_name = aov[0]
                if len(layer_data["cameras"]) > 1:
                    aov_name = "{}_{}".format(aov[0], cam)

                aov_file_list[aov_name] = aov_files
                file_prefix = layer_data["filePrefix"]

        expected_files.append(aov_file_list)
        return expected_files

    def get_files(self):
        """
        This method will return list of expected files.

        It will translate render token strings  ('<RenderPass>', etc.) to
        their values. This task is tricky as every renderer deals with this
        differently. It depends on `get_aovs()` abstract method implemented
        for every supported renderer.
        """
        layer_data = self._get_layer_data()

        expected_files = []
        if layer_data.get("enabledAOVs"):
            expected_files = self._generate_aov_file_sequences(layer_data)
        else:
            expected_files = self._generate_single_file_sequence(layer_data)

        return expected_files

    def get_renderable_cameras(self):
        cam_parents = [
            cmds.listRelatives(x, ap=True)[-1] for x in cmds.ls(cameras=True)
        ]

        renderable_cameras = []
        for cam in cam_parents:
            renderable = False
            if self.maya_is_true(cmds.getAttr("{}.renderable".format(cam))):
                renderable = True

            for override in self.get_layer_overrides(
                "{}.renderable".format(cam), self.layer
            ):
                renderable = self.maya_is_true(override)

            if renderable:
                renderable_cameras.append(cam)
        return renderable_cameras

    def maya_is_true(self, attr_val):
        """
        Whether a Maya attr evaluates to True.
        When querying an attribute value from an ambiguous object the
        Maya API will return a list of values, which need to be properly
        handled to evaluate properly.
        """
        if isinstance(attr_val, types.BooleanType):
            return attr_val
        elif isinstance(attr_val, (types.ListType, types.GeneratorType)):
            return any(attr_val)
        else:
            return bool(attr_val)

    def get_layer_overrides(self, attr, layer):
        connections = cmds.listConnections(attr, plugs=True)
        if connections:
            for connection in connections:
                if connection:
                    node_name = connection.split(".")[0]
                    if cmds.nodeType(node_name) == "renderLayer":
                        attr_name = "%s.value" % ".".join(
                            connection.split(".")[:-1]
                        )
                        if node_name == layer:
                            yield cmds.getAttr(attr_name)

    def get_render_attribute(self, attr):
        return lib.get_attr_in_layer(
            "defaultRenderGlobals.{}".format(attr), layer=self.layer
        )


class ExpectedFilesArnold(AExpectedFiles):

    # Arnold AOV driver extension mapping
    # Is there a better way?
    aiDriverExtension = {
        "jpeg": "jpg",
        "exr": "exr",
        "deepexr": "exr",
        "png": "png",
        "tiff": "tif",
        "mtoa_shaders": "ass",  # TODO: research what those last two should be
        "maya": "",
    }

    def __init__(self, layer):
        super(ExpectedFilesArnold, self).__init__(layer)
        self.renderer = "arnold"

    def get_aovs(self):
        enabled_aovs = []
        try:
            if not (
                cmds.getAttr("defaultArnoldRenderOptions.aovMode")
                and not cmds.getAttr("defaultArnoldDriver.mergeAOVs")  # noqa: W503, E501
            ):
                # AOVs are merged in mutli-channel file
                self.multipart = True
                return enabled_aovs
        except ValueError:
            # this occurs when Render Setting windows was not opened yet. In
            # such case there are no Arnold options created so query for AOVs
            # will fail. We terminate here as there are no AOVs specified then.
            # This state will most probably fail later on some Validator
            # anyway.
            return enabled_aovs

        # AOVs are set to be rendered separately. We should expect
        # <RenderPass> token in path.

        ai_aovs = [n for n in cmds.ls(type="aiAOV")]

        for aov in ai_aovs:
            enabled = self.maya_is_true(cmds.getAttr("{}.enabled".format(aov)))
            ai_driver = cmds.listConnections("{}.outputs".format(aov))[0]
            ai_translator = cmds.getAttr("{}.aiTranslator".format(ai_driver))
            try:
                aov_ext = self.aiDriverExtension[ai_translator]
            except KeyError:
                msg = (
                    "Unrecognized arnold " "driver format for AOV - {}"
                ).format(cmds.getAttr("{}.name".format(aov)))
                raise AOVError(msg)

            for override in self.get_layer_overrides(
                "{}.enabled".format(aov), self.layer
            ):
                enabled = self.maya_is_true(override)
            if enabled:
                # If aov RGBA is selected, arnold will translate it to `beauty`
                aov_name = cmds.getAttr("%s.name" % aov)
                if aov_name == "RGBA":
                    aov_name = "beauty"
                enabled_aovs.append((aov_name, aov_ext))
        # Append 'beauty' as this is arnolds
        # default. If <RenderPass> token is specified and no AOVs are
        # defined, this will be used.
        enabled_aovs.append(
            (u"beauty", cmds.getAttr("defaultRenderGlobals.imfPluginKey"))
        )
        return enabled_aovs


class ExpectedFilesVray(AExpectedFiles):

    # V-ray file extension mapping
    # 5 - exr
    # 6 - multichannel exr
    # 13 - deep exr

    def __init__(self, layer):
        super(ExpectedFilesVray, self).__init__(layer)
        self.renderer = "vray"

    def get_renderer_prefix(self):
        prefix = super(ExpectedFilesVray, self).get_renderer_prefix()
        prefix = "{}_<aov>".format(prefix)
        return prefix

    def get_files(self):
        expected_files = super(ExpectedFilesVray, self).get_files()

        # we need to add one sequence for plain beauty if AOVs are enabled.
        # as vray output beauty without 'beauty' in filename.

        layer_data = self._get_layer_data()
        if layer_data.get("enabledAOVs"):
            expected_files[0][u"beauty"] = self._generate_single_file_sequence(
                layer_data
            )  # noqa: E501

        return expected_files

    def get_aovs(self):
        enabled_aovs = []

        try:
            # really? do we set it in vray just by selecting multichannel exr?
            if (
                cmds.getAttr("vraySettings.imageFormatStr")
                == "exr (multichannel)"  # noqa: W503
            ):
                # AOVs are merged in mutli-channel file
                self.multipart = True
                return enabled_aovs
        except ValueError:
            # this occurs when Render Setting windows was not opened yet. In
            # such case there are no Arnold options created so query for AOVs
            # will fail. We terminate here as there are no AOVs specified then.
            # This state will most probably fail later on some Validator
            # anyway.
            return enabled_aovs

        default_ext = cmds.getAttr("vraySettings.imageFormatStr")
        if default_ext == "exr (multichannel)" or default_ext == "exr (deep)":
            default_ext = "exr"

        vr_aovs = [
            n
            for n in cmds.ls(
                type=["VRayRenderElement", "VRayRenderElementSet"]
            )
        ]

        # todo: find out how to detect multichannel exr for vray
        for aov in vr_aovs:
            enabled = self.maya_is_true(cmds.getAttr("{}.enabled".format(aov)))
            for override in self.get_layer_overrides(
                "{}.enabled".format(aov), "rs_{}".format(self.layer)
            ):
                enabled = self.maya_is_true(override)

            if enabled:
                # todo: find how vray set format for AOVs
                enabled_aovs.append(
                    (self._get_vray_aov_name(aov), default_ext))
        return enabled_aovs

    def _get_vray_aov_name(self, node):

        # Get render element pass type
        vray_node_attr = next(
            attr
            for attr in cmds.listAttr(node)
            if attr.startswith("vray_name")
        )
        pass_type = vray_node_attr.rsplit("_", 1)[-1]

        # Support V-Ray extratex explicit name (if set by user)
        if pass_type == "extratex":
            explicit_attr = "{}.vray_explicit_name_extratex".format(node)
            explicit_name = cmds.getAttr(explicit_attr)
            if explicit_name:
                return explicit_name

        # Node type is in the attribute name but we need to check if value
        # of the attribute as it can be changed
        return cmds.getAttr("{}.{}".format(node, vray_node_attr))


class ExpectedFilesRedshift(AExpectedFiles):

    # mapping redshift extension dropdown values to strings
    ext_mapping = ["iff", "exr", "tif", "png", "tga", "jpg"]

    # name of aovs that are not merged into resulting exr and we need
    # them specified in expectedFiles output.
    unmerged_aovs = ["Cryptomatte"]

    def __init__(self, layer):
        super(ExpectedFilesRedshift, self).__init__(layer)
        self.renderer = "redshift"

    def get_renderer_prefix(self):
        prefix = super(ExpectedFilesRedshift, self).get_renderer_prefix()
        prefix = "{}.<aov>".format(prefix)
        return prefix

    def get_files(self):
        expected_files = super(ExpectedFilesRedshift, self).get_files()

        # we need to add one sequence for plain beauty if AOVs are enabled.
        # as redshift output beauty without 'beauty' in filename.

        layer_data = self._get_layer_data()
        if layer_data.get("enabledAOVs"):
            expected_files[0][u"beauty"] = self._generate_single_file_sequence(
                layer_data
            )

        # Redshift doesn't merge Cryptomatte AOV to final exr. We need to check
        # for such condition and add it to list of expected files.

        for aov in layer_data.get("enabledAOVs"):
            if aov[0].lower() == "cryptomatte":
                aov_name = aov[0]
                expected_files.append(
                    {aov_name: self._generate_single_file_sequence(
                        layer_data, aov_name=aov_name)})

        return expected_files

    def get_aovs(self):
        enabled_aovs = []

        try:
            default_ext = self.ext_mapping[
                cmds.getAttr("redshiftOptions.imageFormat")
            ]
        except ValueError:
            # this occurs when Render Setting windows was not opened yet. In
            # such case there are no Redshift options created so query
            # will fail.
            raise ValueError("Render settings are not initialized")

        rs_aovs = [n for n in cmds.ls(type="RedshiftAOV")]

        # todo: find out how to detect multichannel exr for redshift
        for aov in rs_aovs:
            enabled = self.maya_is_true(cmds.getAttr("{}.enabled".format(aov)))
            for override in self.get_layer_overrides(
                "{}.enabled".format(aov), self.layer
            ):
                enabled = self.maya_is_true(override)

            if enabled:
                # If AOVs are merged into multipart exr, append AOV only if it
                # is in the list of AOVs that renderer cannot (or will not)
                # merge into final exr.
                if self.maya_is_true(
                    cmds.getAttr("redshiftOptions.exrForceMultilayer")
                ):
                    if cmds.getAttr("%s.name" % aov) in self.unmerged_aovs:
                        enabled_aovs.append(
                            (cmds.getAttr("%s.name" % aov), default_ext)
                        )
                else:
                    enabled_aovs.append(
                        (cmds.getAttr("%s.name" % aov), default_ext)
                    )

        if self.maya_is_true(
            cmds.getAttr("redshiftOptions.exrForceMultilayer")
        ):
            # AOVs are merged in mutli-channel file
            self.multipart = True

        return enabled_aovs


class ExpectedFilesRenderman(AExpectedFiles):
    def __init__(self, layer):
        super(ExpectedFilesRenderman, self).__init__(layer)
        self.renderer = "renderman"

    def get_aovs(self):
        enabled_aovs = []

        default_ext = "exr"
        displays = cmds.listConnections("rmanGlobals.displays")
        for aov in displays:
            aov_name = str(aov)
            if aov_name == "rmanDefaultDisplay":
                aov_name = "beauty"

            enabled = self.maya_is_true(cmds.getAttr("{}.enable".format(aov)))
            for override in self.get_layer_overrides(
                "{}.enable".format(aov), self.layer
            ):
                enabled = self.maya_is_true(override)

            if enabled:
                enabled_aovs.append((aov_name, default_ext))

        return enabled_aovs

    def get_files(self):
        """
        In renderman we hack it with prepending path. This path would
        normally be translated from `rmanGlobals.imageOutputDir`. We skip
        this and harcode prepend path we expect. There is no place for user
        to mess around with this settings anyway and it is enforced in
        render settings validator.
        """
        layer_data = self._get_layer_data()
        new_aovs = {}

        expected_files = super(ExpectedFilesRenderman, self).get_files()
        # we always get beauty
        for aov, files in expected_files[0].items():
            new_files = []
            for file in files:
                new_file = "{}/{}/{}".format(
                    layer_data["sceneName"], layer_data["layerName"], file
                )
                new_files.append(new_file)
            new_aovs[aov] = new_files

        return [new_aovs]


class ExpectedFilesMentalray(AExpectedFiles):
    def __init__(self, layer):
        raise UnimplementedRendererException("Mentalray not implemented")

    def get_aovs(self):
        return []


class AOVError(Exception):
    pass


class UnsupportedRendererException(Exception):
    pass


class UnimplementedRendererException(Exception):
    pass
