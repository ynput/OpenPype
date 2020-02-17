import re
import os
import types
# TODO: pending python 3 upgrade
from abc import ABCMeta, abstractmethod

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api

from avalon import maya, api
import pype.maya.lib as lib


R_SINGLE_FRAME = re.compile(r'^(-?)\d+$')
R_FRAME_RANGE = re.compile(r'^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+)$')
R_FRAME_NUMBER = re.compile(r'.+\.(?P<frame>[0-9]+)\..+')
R_LAYER_TOKEN = re.compile(
    r'.*%l.*|.*<layer>.*|.*<renderlayer>.*', re.IGNORECASE)
R_AOV_TOKEN = re.compile(r'.*%a.*|.*<aov>.*|.*<renderpass>.*', re.IGNORECASE)
R_SUBSTITUTE_AOV_TOKEN = re.compile(r'%a|<aov>|<renderpass>', re.IGNORECASE)
R_SUBSTITUTE_LAYER_TOKEN = re.compile(
    r'%l|<layer>|<renderlayer>', re.IGNORECASE)
R_SUBSTITUTE_CAMERA_TOKEN = re.compile(r'%c|<camera>', re.IGNORECASE)
R_SUBSTITUTE_SCENE_TOKEN = re.compile(r'%s|<scene>', re.IGNORECASE)

RENDERER_NAMES = {
    'mentalray': 'MentalRay',
    'vray': 'V-Ray',
    'arnold': 'Arnold',
    'renderman': 'Renderman',
    'redshift': 'Redshift'
}

# not sure about the renderman image prefix
ImagePrefixes = {
    'mentalray': 'defaultRenderGlobals.imageFilePrefix',
    'vray': 'vraySettings.fileNamePrefix',
    'arnold': 'defaultRenderGlobals.imageFilePrefix',
    'renderman': 'defaultRenderGlobals.imageFilePrefix',
    'redshift': 'defaultRenderGlobals.imageFilePrefix'
}


class CollectMayaRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"

    def process(self, context):
        render_instance = None
        for instance in context:
            if 'rendering' in instance.data['families']:
                render_instance = instance
                render_instance.data["remove"] = True

        if not render_instance:
            self.log.info("No render instance found, skipping render "
                          "layer collection.")
            return

        render_globals = render_instance
        collected_render_layers = render_instance.data['setMembers']
        filepath = context.data["currentFile"].replace("\\", "/")
        asset = api.Session["AVALON_ASSET"]
        workspace = context.data["workspaceDir"]

        self._rs = renderSetup.instance()
        maya_render_layers = {l.name(): l for l in self._rs.getRenderLayers()}

        self.maya_layers = maya_render_layers

        for layer in collected_render_layers:
            # every layer in set should start with `LAYER_` prefix
            try:
                expected_layer_name = re.search(r"^LAYER_(.*)", layer).group(1)
            except IndexError:
                msg = ("Invalid layer name in set [ {} ]".format(layer))
                self.log.warnig(msg)
                continue

            self.log.info("processing %s" % layer)
            # check if layer is part of renderSetup
            if expected_layer_name not in maya_render_layers:
                msg = ("Render layer [ {} ] is not in "
                       "Render Setup".format(expected_layer_name))
                self.log.warning(msg)
                continue

            # check if layer is renderable
            if not maya_render_layers[expected_layer_name].isRenderable():
                msg = ("Render layer [ {} ] is not "
                       "renderable".format(expected_layer_name))
                self.log.warning(msg)
                continue

            # test if there are sets (subsets) to attach render to
            sets = cmds.sets(layer, query=True) or []
            attachTo = []
            if sets:
                for s in sets:
                    attachTo.append({
                        "version": None,  # we need integrator to get version
                        "subset": s,
                        "family": cmds.getAttr("{}.family".format(s))
                    })
                    self.log.info(" -> attach render to: {}".format(s))

            layer_name = "rs_{}".format(expected_layer_name)

            # collect all frames we are expecting to be rendered
            renderer = cmds.getAttr(
                'defaultRenderGlobals.currentRenderer').lower()
            # handle various renderman names
            if renderer.startswith('renderman'):
                renderer = 'renderman'

            # return all expected files for all cameras and aovs in given
            # frame range
            exp_files = ExpectedFiles().get(renderer, layer_name)

            # append full path
            full_exp_files = []
            for ef in exp_files:
                full_path = os.path.join(workspace, "renders", ef)
                full_path = full_path.replace("\\", "/")
                full_exp_files.append(full_path)

            self.log.info("collecting layer: {}".format(layer_name))
            # Get layer specific settings, might be overrides
            data = {
                "subset": expected_layer_name,
                "attachTo": attachTo,
                "setMembers": layer_name,
                "publish": True,
                "frameStart": self.get_render_attribute("startFrame",
                                                        layer=layer_name),
                "frameEnd": self.get_render_attribute("endFrame",
                                                      layer=layer_name),
                "byFrameStep": self.get_render_attribute("byFrameStep",
                                                         layer=layer_name),
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
                "expectedFiles": full_exp_files
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
            label += "  [{0}-{1}]".format(int(data["frameStart"]),
                                          int(data["frameEnd"]))

            instance = context.create_instance(expected_layer_name)
            instance.data["label"] = label
            instance.data.update(data)
        pass

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
            options['renderGlobals'][key] = machine_list

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
        return lib.get_attr_in_layer("defaultRenderGlobals.{}".format(attr),
                                     layer=layer)


class ExpectedFiles:

    def get(self, renderer, layer):
        if renderer.lower() == 'arnold':
            return ExpectedFilesArnold(layer).get_files()
        elif renderer.lower() == 'vray':
            return ExpectedFilesVray(layer).get_files()
        elif renderer.lower() == 'redshift':
            return ExpectedFilesRedshift(layer).get_files()
        elif renderer.lower() == 'mentalray':
            renderer.ExpectedFilesMentalray(layer).get_files()
        elif renderer.lower() == 'renderman':
            renderer.ExpectedFilesRenderman(layer).get_files()
        else:
            raise UnsupportedRendererException(
                "unsupported {}".format(renderer))


class AExpectedFiles:
    __metaclass__ = ABCMeta
    renderer = None
    layer = None

    def __init__(self, layer):
        self.layer = layer

    @abstractmethod
    def get_aovs(self):
        pass

    def get_files(self):
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
        try:
            file_prefix = cmds.getAttr(ImagePrefixes[renderer])
        except KeyError:
            raise UnsupportedRendererException(
                "Unsupported renderer {}".format(renderer))

        if not file_prefix:
            raise RuntimeError("Image prefix not set")

        default_ext = cmds.getAttr('defaultRenderGlobals.imfPluginKey')

        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 4 -  get renderable cameras_____________/
        # __________________/

        renderable_cameras = self.get_renderable_cameras()
        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 5 -  get AOVs      /____________________/
        # __________________/

        enabled_aovs = self.get_aovs()

        # if we have <camera> token in prefix path we'll expect output for
        # every renderable camera in layer.

        expected_files = []
        layer_name = self.layer
        if self.layer.startswith("rs_"):
            layer_name = self.layer[3:]
        start_frame = int(self.get_render_attribute('startFrame'))
        end_frame = int(self.get_render_attribute('endFrame'))
        frame_step = int(self.get_render_attribute('byFrameStep'))
        padding = int(self.get_render_attribute('extensionPadding'))

        resolved_path = file_prefix
        for cam in renderable_cameras:
            if enabled_aovs:
                for aov in enabled_aovs:

                    mappings = (
                        (R_SUBSTITUTE_SCENE_TOKEN, scene_name),
                        (R_SUBSTITUTE_LAYER_TOKEN, layer_name),
                        (R_SUBSTITUTE_CAMERA_TOKEN, cam),
                        (R_SUBSTITUTE_AOV_TOKEN, aov[0])
                    )

                    for regex, value in mappings:
                        file_prefix = re.sub(regex, value, file_prefix)

                    aov_files = []
                    for frame in range(
                            int(start_frame),
                            int(end_frame) + 1,
                            int(frame_step)):
                        aov_files.append(
                            '{}.{}.{}'.format(file_prefix,
                                              str(frame).rjust(padding, "0"),
                                              aov[1]))
                    expected_files.append({aov[0]: aov_files})
                    file_prefix = resolved_path
            else:
                mappings = (
                    (R_SUBSTITUTE_SCENE_TOKEN, scene_name),
                    (R_SUBSTITUTE_LAYER_TOKEN, layer_name),
                    (R_SUBSTITUTE_CAMERA_TOKEN, cam)
                )

                for regex, value in mappings:
                    file_prefix = re.sub(regex, value, file_prefix)

                for frame in range(
                        int(start_frame),
                        int(end_frame) + 1,
                        int(frame_step)):
                    expected_files.append(
                        '{}.{}.{}'.format(file_prefix,
                                          str(frame).rjust(padding, "0"),
                                          default_ext))

        return expected_files

    def get_renderable_cameras(self):
        cam_parents = [cmds.listRelatives(x, ap=True)[-1]
                       for x in cmds.ls(cameras=True)]

        renderable_cameras = []
        for cam in cam_parents:
            renderable = False
            if self.maya_is_true(cmds.getAttr('{}.renderable'.format(cam))):
                renderable = True

            for override in self.get_layer_overrides(
                    '{}.renderable'.format(cam), self.layer):
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
                    node_name = connection.split('.')[0]
                    if cmds.nodeType(node_name) == 'renderLayer':
                        attr_name = '%s.value' % '.'.join(
                            connection.split('.')[:-1])
                        if node_name == layer:
                            yield cmds.getAttr(attr_name)

    def get_render_attribute(self, attr):
        return lib.get_attr_in_layer("defaultRenderGlobals.{}".format(attr),
                                     layer=self.layer)


class ExpectedFilesArnold(AExpectedFiles):

    # Arnold AOV driver extension mapping
    # Is there a better way?
    aiDriverExtension = {
        'jpeg': 'jpg',
        'exr': 'exr',
        'deepexr': 'exr',
        'png': 'png',
        'tiff': 'tif',
        'mtoa_shaders': 'ass',  # TODO: research what those last two should be
        'maya': ''
    }

    def __init__(self, layer):
        super(ExpectedFilesArnold, self).__init__(layer)
        self.renderer = 'arnold'

    def get_aovs(self):
        enabled_aovs = []
        if not (cmds.getAttr('defaultArnoldRenderOptions.aovMode')
                and not cmds.getAttr('defaultArnoldDriver.mergeAOVs')):
            # AOVs are merged in mutli-channel file
            return enabled_aovs

        # AOVs are set to be rendered separately. We should expect
        # <RenderPass> token in path.

        ai_aovs = [n for n in cmds.ls(type='aiAOV')]

        for aov in ai_aovs:
            enabled = self.maya_is_true(
                cmds.getAttr('{}.enabled'.format(aov)))
            ai_driver = cmds.listConnections(
                '{}.outputs'.format(aov))[0]
            ai_translator = cmds.getAttr(
                '{}.aiTranslator'.format(ai_driver))
            try:
                aov_ext = self.aiDriverExtension[ai_translator]
            except KeyError:
                msg = ('Unrecognized arnold '
                       'driver format for AOV - {}').format(
                    cmds.getAttr('{}.name'.format(aov))
                )
                raise AOVError(msg)

            for override in self.get_layer_overrides(
                    '{}.enabled'.format(aov), self.layer):
                enabled = self.maya_is_true(override)
            if enabled:
                # If aov RGBA is selected, arnold will translate it to `beauty`
                aov_name = cmds.getAttr('%s.name' % aov)
                if aov_name == 'RGBA':
                    aov_name = 'beauty'
                enabled_aovs.append(
                    (
                        aov_name,
                        aov_ext
                    )
                )
        if not enabled_aovs:
            # if there are no AOVs, append 'beauty' as this is arnolds
            # default. If <RenderPass> token is specified and no AOVs are
            # defined, this will be used.
            enabled_aovs.append(
                (
                    'beauty',
                    cmds.getAttr('defaultRenderGlobals.imfPluginKey')
                )
            )
        return enabled_aovs


class ExpectedFilesVray(AExpectedFiles):

    def __init__(self, layer):
        super(ExpectedFilesVray, self).__init__(layer)
        self.renderer = 'vray'

    def get_aovs(self):

        default_ext = cmds.getAttr('defaultRenderGlobals.imfPluginKey')
        enabled_aovs = []
        vr_aovs = [n for n in cmds.ls(
            type=["VRayRenderElement", "VRayRenderElementSet"])]

        # todo: find out how to detect multichannel exr for vray
        for aov in vr_aovs:
            enabled = self.maya_is_true(
                cmds.getAttr('{}.enabled'.format(aov)))
            for override in self.get_layer_overrides(
                    '{}.enabled'.format(aov), 'rs_{}'.format(self.layer)):
                enabled = self.maya_is_true(override)

            if enabled:
                # todo: find how vray set format for AOVs
                enabled_aovs.append(
                    (
                        self._get_vray_aov_name(aov),
                        default_ext)
                    )
        return enabled_aovs

    def _get_vray_aov_name(self, node):

        # Get render element pass type
        vray_node_attr = next(attr for attr in cmds.listAttr(node)
                              if attr.startswith("vray_name"))
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

    def __init__(self, layer):
        super(ExpectedFilesRedshift, self).__init__(layer)
        self.renderer = 'redshift'

    def get_aovs(self):
        enabled_aovs = []
        default_ext = cmds.getAttr('defaultRenderGlobals.imfPluginKey')
        rs_aovs = [n for n in cmds.ls(type='RedshiftAOV')]

        # todo: find out how to detect multichannel exr for redshift
        for aov in rs_aovs:
            enabled = self.maya_is_true(
                cmds.getAttr('{}.enabled'.format(aov)))
            for override in self.get_layer_overrides(
                    '{}.enabled'.format(aov), self.layer):
                enabled = self.maya_is_true(override)

            if enabled:
                # todo: find how redshift set format for AOVs
                enabled_aovs.append(
                    (
                        cmds.getAttr('%s.name' % aov),
                        default_ext
                    )
                )

        return enabled_aovs


class ExpectedFilesRenderman(AExpectedFiles):

    def __init__(self, layer):
        raise UnimplementedRendererException('Renderman not implemented')


class ExpectedFilesMentalray(AExpectedFiles):

    def __init__(self, layer):
        raise UnimplementedRendererException('Mentalray not implemented')


class AOVError(Exception):
    pass


class UnsupportedRendererException(Exception):
    pass


class UnimplementedRendererException(Exception):
    pass
