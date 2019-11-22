import pyblish.api
import nuke


@pyblish.api.log
class CollectBackdrops(pyblish.api.InstancePlugin):
    """Collect Backdrop node instance and its content
    """

    order = pyblish.api.CollectorOrder + 0.22
    label = "Collect Backdrop"
    hosts = ["nuke"]
    families = ["nukenodes"]

    def process(self, instance):

        bckn = instance[0]

        # define size of the backdrop
        left = bckn.xpos()
        top = bckn.ypos()
        right = left + bckn['bdwidth'].value()
        bottom = top + bckn['bdheight'].value()

        # iterate all nodes
        for node in nuke.allNodes():

            # exclude viewer
            if node.Class() == "Viewer":
                continue

            # find all related nodes
            if (node.xpos() > left) \
                and (node.xpos() + node.screenWidth() < right) \
                    and (node.ypos() > top) \
                    and (node.ypos() + node.screenHeight() < bottom):

                # add contained nodes to instance's node list
                instance.append(node)

        instance.data["label"] = "{0} ({1} nodes)".format(
            bckn.name(), len(instance)-1)

        self.log.info("Backdrop content collected: `{}`".format(instance[:]))
        self.log.info("Backdrop instance collected: `{}`".format(instance))
