from collections import defaultdict

import pyblish.api

from maya import cmds


class ValidateMayaRenderLayersAccessible(pyblish.api.ContextPlugin):
    """Validate if the render is accessible to iterate through

    A bug in Maya can result in inaccessible render layers.
    The render layer is not visible in the render layer manager or outliner
    but can be found through code. The bug occurs when a referenced file is
    imported.

    Sometimes the issue is an unresolved adjustment in render layers.

    """

    order = pyblish.api.CollectorOrder
    label = "Render Layer Accessible"
    hosts = ["maya"]

    def process(self, context):

        # Get render globals node
        try:
            render_globals = cmds.ls("renderglobalsDefault")[0]
        except IndexError:
            self.log.error("Cannot collect renderlayers without "
                           "renderGlobals node")
            return

        loaded, referenced = self.get_invalid()
        if loaded or referenced:
            message_a = ("Discovered inaccessible loaded renderlayers: %s"
                         % list(loaded)) if loaded else ""

            message_b = ("Discovered inaccessible referenced renderlayers: %s"
                         % list(referenced)) if referenced else ""

            raise RuntimeError("{}\n{}".format(message_a, message_b))

    @classmethod
    def get_invalid(cls):

        invalid = []
        invalid_referenced = []

        lookup = defaultdict(list)
        render_layers = cmds.ls(type="renderLayer")

        # Create look up
        for layer in render_layers:
            parts = layer.rsplit(":", 1)
            lookup[parts[-1]].append(layer)

        for name, layers in lookup.items():
            cls.log.info("Checking if %i '%s' layers can be accessed" %
                         (len(layers), name))

            for layer in layers:
                try:
                    cmds.editRenderLayerGlobals(currentRenderLayer=layer)
                except RuntimeError:
                    if cmds.referenceQuery(layer, isNodeReferenced=True):
                        cls.log.error("Referenced layer '%s' cannot "
                                      "be accessed" % layer)
                        invalid_referenced.append(layer)
                    else:
                        cls.log.error("Non-referenced layer '%s' cannot "
                                      "be accessed" % layer)

                        invalid.append(layer)

        return invalid, invalid_referenced
