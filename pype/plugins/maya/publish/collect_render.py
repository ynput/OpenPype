import re

from maya import cmds
from maya import OpenMaya as om
from pprint import pprint

import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api

from avalon import maya, api
import pype.maya.lib as lib


class CollectMayaRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"
    families = ["render"]

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
            if sets:
                for s in sets:
                    self.log.info("  - attach render to: {}".format(s))

            self.log.debug("marked subsets: {}".format(sets))

            layer_name = "rs_{}".format(expected_layer_name)
            self.log.info("  - %s" % layer_name)
            # Get layer specific settings, might be overrides
            data = {
                "subset": expected_layer_name,
                "attachTo": sets,
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
            # TODO(marcus): Take into account layer overrides
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

        self.log.info(attributes)

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
