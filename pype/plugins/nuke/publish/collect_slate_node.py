import pyblish.api
import nuke


class CollectSlate(pyblish.api.InstancePlugin):
    """Check if SLATE node is in scene and connected to rendering tree"""

    order = pyblish.api.CollectorOrder + 0.09
    label = "Collect Slate Node"
    hosts = ["nuke"]
    families = ["render", "render.local", "render.farm"]

    def process(self, instance):
        node = instance[0]

        slate = next((n for n in nuke.allNodes()
                      if "slate" in n.name().lower()
                      if not n["disable"].getValue()),
                     None)

        if slate:
            # check if slate node is connected to write node tree
            slate_check = 0
            slate_node = None
            while slate_check == 0:
                try:
                    node = node.dependencies()[0]
                    if slate.name() in node.name():
                        slate_node = node
                        slate_check = 1
                except IndexError:
                    break

            if slate_node:
                instance.data["slateNode"] = slate_node
                instance.data["families"].append("slate")
                self.log.info(
                    "Slate node is in node graph: `{}`".format(slate.name()))
                self.log.debug(
                    "__ instance: `{}`".format(instance))
