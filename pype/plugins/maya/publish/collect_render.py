import re
import os
import types

from maya import cmds
from maya import OpenMaya as om
import maya.aovs as aovs
import pymel.core as pm
import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api

from avalon import maya, api
import pype.maya.lib as lib


R_SINGLE_FRAME = re.compile(r'^(-?)\d+$')
R_FRAME_RANGE = re.compile(r'^(?P<sf>(-?)\d+)-(?P<ef>(-?)\d+)$')
R_FRAME_NUMBER = re.compile(r'.+\.(?P<frame>[0-9]+)\..+')
R_LAYER_TOKEN = re.compile(
    r'.*%l.*|.*<layer>.*|.*<renderlayer>.*', re.IGNORECASE)
R_AOV_TOKEN = re.compile(r'.*%l.*|.*<aov>.*|.*<renderpass>.*', re.IGNORECASE)
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


class CollectMayaRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"
    families = ["render"]

    def _get_expected_files(self, layer):
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
        renderer = cmds.getAttr('defaultRenderGlobals.currentRenderer').lower()
        if renderer.startswith('renderman'):
            renderer = 'renderman'

        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 3 -  image prefix  /__________________/
        # __________________/
        try:
            file_prefix = cmds.getAttr(ImagePrefixes[renderer])
        except KeyError:
            raise RuntimeError("Unsupported renderer {}".format(renderer))

        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 4 -  get renderabe cameras_____________/
        # __________________/
        cam_parents = [cmds.listRelatives(x, ap=True)[-1]
                       for x in cmds.ls(cameras=True)]

        self.log.info("cameras in scene: %s" % ", ".join(cam_parents))

        renderable_cameras = []
        for cam in cam_parents:
            renderable = False
            if self.maya_is_true(cmds.getAttr('{}.renderable'.format(cam))):
                renderable = True

            for override in self.get_layer_overrides(
                    '{}.renderable'.format(cam), 'rs_{}'.format(layer)):
                renderable = self.maya_is_true(override)

            if renderable:
                renderable_cameras.append(cam)

        self.log.info("renderable cameras: %s" % ", ".join(renderable_cameras))

        #                    ________________________________________________
        # __________________/ ______________________________________________/
        # 5 -  get AOVs      /_____________/
        # __________________/

        enabled_aovs = []

        if renderer == "arnold":

            if (cmds.getAttr('defaultArnoldRenderOptions.aovMode') and
                    not cmds.getAttr('defaultArnoldDriver.mergeAOVs')):
                # AOVs are set to be rendered separately. We should expect
                # <RenderPass> token in path.
                mergeAOVs = False
            else:
                mergeAOVs = True

            if not mergeAOVs:
                ai_aovs = [n for n in cmds.ls(type='aiAOV')]

                for aov in ai_aovs:
                    enabled = self.maya_is_true(
                        cmds.getAttr('{}.enabled'.format(aov)))
                    ai_driver = cmds.listConnections(
                        '{}.outputs'.format(aov))[0]
                    ai_translator = cmds.getAttr(
                        '{}.aiTranslator'.format(ai_driver))
                    try:
                        aov_ext = aiDriverExtension[ai_translator]
                    except KeyError:
                        msg = ('Unrecognized arnold '
                               'drive format for AOV - {}').format(
                            cmds.getAttr('{}.name'.format(aov))
                        )
                        self.log.error(msg)
                        raise RuntimeError(msg)

                    for override in self.get_layer_overrides(
                            '{}.enabled'.format(aov), 'rs_{}'.format(layer)):
                        enabled = self.maya_is_true(override)
                    if enabled:
                        enabled_aovs.append((aov, aov_ext))

                self.log.info("enabled aovs: %s" % ", ".join(
                    [cmds.getAttr('%s.name' % (n,)) for n in enabled_aovs]))

        elif renderer == "vray":
            # todo: implement vray aovs
            pass

        elif renderer == "redshift":
            # todo: implement redshift aovs
            pass

        elif renderer == "mentalray":
            # todo: implement mentalray aovs
            pass

        elif renderer == "renderman":
            # todo: implement renderman aovs
            pass

        mappings = (
            (R_SUBSTITUTE_SCENE_TOKEN, scene_name),
            (R_SUBSTITUTE_LAYER_TOKEN, layer),
            (R_SUBSTITUTE_CAMERA_TOKEN, camera),
        )

        # if we have <camera> token in prefix path we'll expect output for
        # every renderable camera in layer.



        for regex, value in mappings:
            file_prefix = re.sub(regex, value, file_prefix)


    def process(self, context):
        render_instance = None
        for instance in context:
            if 'render' in instance.data['families']:
                render_instance = instance

        if not render_instance:
            self.log.info("No render instance found, skipping render "
                          "layer collection.")
            return

        render_globals = render_instance
        collected_render_layers = render_instance.data['setMembers']
        filepath = context.data["currentFile"].replace("\\", "/")
        asset = api.Session["AVALON_ASSET"]

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
            files = cmds.renderSettings(fp=True, fin=True, lin=True,
                                        lut=True, lyr=expected_layer_name)

            if len(files) == 1:
                # if last file is not specified, maya is not set for animation
                pass
            else:
                # get frame position and padding

                # get extension
                re.search(r'\.(\w+)$', files[0])

                # find <RenderPass> token. If no AOVs are specified, assume
                # <RenderPass> is 'beauty'
                render_passes = ['beauty']
                if pm.getAttr('defaultRenderGlobals.currentRenderer') == 'arnold':  # noqa: E501
                    # arnold is our renderer
                    for node in cmd.ls(type="aiAOV"):
                        render_pass = node.split('_')[1]






            # Get layer specific settings, might be overrides
            data = {
                "subset": expected_layer_name,
                "attachTo": attachTo,
                "setMembers": expected_layer_name,
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
                "family": "Render Layers",
                "families": ["renderlayer"],
                "asset": asset,
                "time": api.time(),
                "author": context.data["user"],

                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": filepath
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

        legacy = attributes["useLegacyRenderLayers"]
        options["renderGlobals"]["UseLegacyRenderLayers"] = legacy

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

    def _get_layer_overrides(self, attr, layer):
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

    def _maya_is_true(self, attr_val):
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
