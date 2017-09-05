import os
from maya import cmds

import pyblish.api

from avalon import maya, api


class CollectMindbenderMayaRenderlayers(pyblish.api.ContextPlugin):
    """Gather instances by active render layers"""

    order = pyblish.api.CollectorOrder
    hosts = ["maya"]
    label = "Render Layers"

    def process(self, context):

        registered_root = api.registered_root()
        asset_name = os.environ["AVALON_ASSET"]

        current_file = context.data["currentFile"]
        relative_file = current_file.replace(registered_root, "{root}")
        source_file = relative_file.replace("\\", "/")

        renderlayers = cmds.ls(type="renderLayer")
        for layer in renderlayers:
            if layer.endswith("defaultRenderLayer"):
                continue

            data = {"family": "Render Layers",
                    "families": ["colorbleed.renderlayer"],
                    "publish": cmds.getAttr("{}.renderable".format(layer)),

                    "startFrame": self.get_render_attribute("startFrame"),
                    "endFrame": self.get_render_attribute("endFrame"),
                    "byFrameStep": self.get_render_attribute("byFrameStep"),
                    "renderer": self.get_render_attribute("currentRenderer"),

                    # instance subset
                    "asset": asset_name,
                    "subset": layer,
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
            try:
                avalon_globals = maya.lsattr("id", "avalon.renderglobals")[0]
            except IndexError:
                pass
            else:
                _globals = maya.read(avalon_globals)
                data["renderGlobals"] = self.get_global_overrides(_globals)

            instance = context.create_instance(layer)
            instance.data.update(data)

    def get_render_attribute(self, attr):
        return cmds.getAttr("defaultRenderGlobals.{}".format(attr))

    def get_global_overrides(self, globals):
        """
        Get all overrides with a value, skip those without

        Here's the kicker. These globals override defaults in the submission
        integrator, but an empty value means no overriding is made.
        Otherwise, Frames would override the default frames set under globals.

        Args:
            globals (dict) collection of render globals

        Returns:
            dict: only overrides with values
        """
        keys = ["pool", "group", "frames", "priority"]
        read_globals = {}
        for key in keys:
            value = globals[key]
            if not value:
                continue
            read_globals[key.capitalize()] = value

        if not read_globals:
            self.log.info("Submitting without overrides")

        return read_globals