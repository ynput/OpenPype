import pyblish.api
import nuke


class CollectSlate(pyblish.api.InstancePlugin):
    """Check if SLATE node is in scene and connected to rendering tree"""

    order = pyblish.api.CollectorOrder + 0.002
    label = "Collect Slate Node"
    hosts = ["nuke"]
    families = ["render"]

    def process(self, instance):
        node = instance.data["transientData"]["node"]

        slate = next(
            (
                n_ for n_ in nuke.allNodes()
                if "slate" in n_.name().lower()
                if not n_["disable"].getValue() and
                "publish_instance" not in n_.knobs()  # Exclude instance nodes.
            ),
            None
        )

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
                instance.data["slate"] = True
                instance.data["families"].append("slate")
                self.log.debug(
                    "Slate node is in node graph: `{}`".format(slate.name()))
                self.log.debug(
                    "__ instance.data: `{}`".format(instance.data))
