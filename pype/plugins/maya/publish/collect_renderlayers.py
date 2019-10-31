from maya import cmds

import pyblish.api

from avalon import maya, api
import pype.maya.lib as lib


class CollectMayaRenderlayers(pyblish.api.ContextPlugin):
    """Gather instances by active render layers"""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Render Layers"

    def process(self, context):

        asset = api.Session["AVALON_ASSET"]
        filepath = context.data["currentFile"].replace("\\", "/")

        # Get render globals node
        try:
            render_globals = cmds.ls("renderglobalsMain")[0]
            for instance in context:
                self.log.debug(instance.name)
                if instance.data['family'] == 'workfile':
                    instance.data['publish'] = True
        except IndexError:
            self.log.info("Skipping renderlayer collection, no "
                          "renderGlobalsDefault found..")
            return
        # Get all valid renderlayers
        # This is how Maya populates the renderlayer display
        rlm_attribute = "renderLayerManager.renderLayerId"
        connected_layers = cmds.listConnections(rlm_attribute) or []
        valid_layers = set(connected_layers)

        # Get all renderlayers and check their state
        renderlayers = [i for i in cmds.ls(type="renderLayer") if
                        cmds.getAttr("{}.renderable".format(i)) and not
                        cmds.referenceQuery(i, isNodeReferenced=True)]

        # Sort by displayOrder
        def sort_by_display_order(layer):
            return cmds.getAttr("%s.displayOrder" % layer)

        renderlayers = sorted(renderlayers, key=sort_by_display_order)

        for layer in renderlayers:

            # Check if layer is in valid (linked) layers
            if layer not in valid_layers:
                self.log.warning("%s is invalid, skipping" % layer)
                continue

            if layer.endswith("defaultRenderLayer"):
                continue
            else:
                # Remove Maya render setup prefix `rs_`
                layername = layer.split("rs_", 1)[-1]

            # Get layer specific settings, might be overrides
            data = {
                "subset": layername,
                "setMembers": layer,
                "publish": True,
                "frameStart": self.get_render_attribute("startFrame",
                                                        layer=layer),
                "frameEnd": self.get_render_attribute("endFrame",
                                                      layer=layer),
                "byFrameStep": self.get_render_attribute("byFrameStep",
                                                         layer=layer),
                "renderer": self.get_render_attribute("currentRenderer",
                                                      layer=layer),

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
            overrides = self.parse_options(render_globals)
            data.update(**overrides)

            # Define nice label
            label = "{0} ({1})".format(layername, data["asset"])
            label += "  [{0}-{1}]".format(int(data["frameStart"]),
                                          int(data["frameEnd"]))

            instance = context.create_instance(layername)
            instance.data["label"] = label
            instance.data.update(data)

    def get_render_attribute(self, attr, layer):
        return lib.get_attr_in_layer("defaultRenderGlobals.{}".format(attr),
                                     layer=layer)

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
