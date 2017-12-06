from maya import cmds

import pyblish.api

from avalon import maya, api
import colorbleed.maya.lib as lib


class CollectMayaRenderlayers(pyblish.api.ContextPlugin):
    """Gather instances by active render layers"""

    order = pyblish.api.CollectorOrder
    hosts = ["maya"]
    label = "Render Layers"
    optional = True

    def process(self, context):

        registered_root = api.registered_root()
        asset_name = api.Session["AVALON_ASSET"]

        current_file = context.data["currentFile"]
        relative_file = current_file.replace(registered_root, "{root}")
        source_file = relative_file.replace("\\", "/")

        # Get render globals node
        try:
            render_globals = cmds.ls("renderglobalsDefault")[0]
        except IndexError:
            self.log.info("Cannot collect renderlayers without "
                          "renderGlobals node")
            return

        default_layer = "{}.includeDefaultRenderLayer".format(render_globals)
        use_defaultlayer = cmds.getAttr(default_layer)

        # Get render layers
        renderlayers = [i for i in cmds.ls(type="renderLayer") if not
                        cmds.referenceQuery(i, isNodeReferenced=True)]
        if not use_defaultlayer:
            renderlayers = [i for i in renderlayers if
                            not i.endswith("defaultRenderLayer")]

        for layer in renderlayers:
            if layer.endswith("defaultRenderLayer"):
                layername = "masterLayer"
            else:
                layername = layer.split("rs_", 1)[-1]

            data = {"family": "Render Layers",
                    "families": ["colorbleed.renderlayer"],
                    "publish": cmds.getAttr("{}.renderable".format(layer)),

                    "startFrame": self.get_render_attribute("startFrame"),
                    "endFrame": self.get_render_attribute("endFrame"),
                    "byFrameStep": self.get_render_attribute("byFrameStep"),
                    "renderer": lib.get_renderer(layer),

                    # instance subset
                    "asset": asset_name,
                    "subset": layername,
                    "setMembers": layer,

                    "time": api.time(),
                    "author": context.data["user"],
                    "source": source_file}

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

            instance = context.create_instance(layername)
            instance.data.update(data)

    def get_render_attribute(self, attr):
        return cmds.getAttr("defaultRenderGlobals.{}".format(attr))

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
        legacy = attributes["useLegacyRenderLayers"]
        options["renderGlobals"]["UseLegacyRenderLayers"] = legacy

        # Machine list
        machine_list = attributes["machineList"]
        if machine_list:
            key = "Whitelist" if attributes["whitelist"] else "Blacklist"
            options['renderGlobals'][key] = machine_list

        # Suspend publish job
        state = "Suspended" if attributes["suspendPublishJob"] else "Active"
        options["suspendPublishJob"] = state

        return options
