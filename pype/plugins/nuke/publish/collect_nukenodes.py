import pyblish.api
import nuke

class CollectBackdrops(pyblish.api.InstancePlugin):
    """Collect Backdrop instance from rendered frames
    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Collect Backdrop"
    hosts = ["nuke"]
    families = ["nukenodes"]

    def process(self, instance):

        bckn = instance[0]

        left = bckn.xpos()
        top = bckn.ypos()
        right = left + bckn['bdwidth'].value()
        bottom = top + bckn['bdheight'].value()

        inNodes = []
        for node in nuke.allNodes():
            if node.Class() == "Viewer":
                continue

            if (node.xpos() > left) \
                and (node.xpos() + node.screenWidth() < right) \
                    and (node.ypos() > top) \
                    and (node.ypos() + node.screenHeight() < bottom):
                inNodes.append(node)

        self.log.info("Backdrop content collected: `{}`".format(inNodes))
        self.log.info("Backdrop instance collected: `{}`".format(instance))
