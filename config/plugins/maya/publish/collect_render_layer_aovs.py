from maya import cmds

import pyblish.api

import config.maya.lib as lib


class CollectRenderLayerAOVS(pyblish.api.InstancePlugin):
    """Validate all render layer's AOVs / Render Elements are registered in
    the database

    This validator is important to be able to Extend Frames

    Technical information:
    Each renderer uses different logic to work with render passes.
    VRay - RenderElement
        Simple node connection to the actual renderLayer node

    Arnold - AOV:
        Uses its own render settings node and connects an aiOAV to it

    Redshift - AOV:
        Uses its own render settings node and RedshiftAOV node. It is not
        connected but all AOVs are enabled for all render layers by default.

    """

    order = pyblish.api.CollectorOrder + 0.01
    label = "Render Elements / AOVs"
    hosts = ["maya"]
    families = ["studio.renderlayer"]

    def process(self, instance):

        # Check if Extend Frames is toggled
        if not instance.data("extendFrames", False):
            return

        # Get renderer
        renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")

        self.log.info("Renderer found: {}".format(renderer))

        rp_node_types = {"vray": "VRayRenderElement",
                         "arnold": "aiAOV",
                         "redshift": "RedshiftAOV"}

        if renderer not in rp_node_types.keys():
            self.log.error("Unsupported renderer found: '{}'".format(renderer))
            return

        result = []

        # Collect all AOVs / Render Elements
        with lib.renderlayer(instance.name):

            node_type = rp_node_types[renderer]
            render_elements = cmds.ls(type=node_type)

            # Check if AOVs / Render Elements are enabled
            for element in render_elements:
                enabled = cmds.getAttr("{}.enabled".format(element))
                if not enabled:
                    continue

                pass_name = self.get_pass_name(renderer, element)
                render_pass = "%s.%s" % (instance.name, pass_name)

                result.append(render_pass)

        self.log.info("Found {} render elements / AOVs for "
                      "'{}'".format(len(result), instance.name))

        instance.data["renderPasses"] = result

    def get_pass_name(self, renderer, node):

        if renderer == "vray":
            vray_node_attr = next(attr for attr in cmds.listAttr(node)
                                  if attr.startswith("vray_name"))

            pass_type = vray_node_attr.rsplit("_", 1)[-1]
            if pass_type == "extratex":
                vray_node_attr = "vray_explicit_name_extratex"

            # Node type is in the attribute name but we need to check if value
            # of the attribute as it can be changed
            pass_name = cmds.getAttr("{}.{}".format(node, vray_node_attr))

        elif renderer in ["arnold", "redshift"]:
            pass_name = cmds.getAttr("{}.name".format(node))
        else:
            raise RuntimeError("Unsupported renderer: '{}'".format(renderer))

        return pass_name