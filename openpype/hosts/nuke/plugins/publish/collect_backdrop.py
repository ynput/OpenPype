from pprint import pformat
import pyblish.api
from openpype.hosts.nuke.api import lib as pnlib
import nuke


class CollectBackdrops(pyblish.api.InstancePlugin):
    """Collect Backdrop node instance and its content
    """

    order = pyblish.api.CollectorOrder + 0.22
    label = "Collect Backdrop"
    hosts = ["nuke"]
    families = ["nukenodes"]

    def process(self, instance):
        self.log.debug(pformat(instance.data))

        bckn = instance.data["transientData"]["node"]

        # define size of the backdrop
        left = bckn.xpos()
        top = bckn.ypos()
        right = left + bckn['bdwidth'].value()
        bottom = top + bckn['bdheight'].value()

        instance.data["transientData"]["childNodes"] = []
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
                instance.data["transientData"]["childNodes"].append(node)

        # get all connections from outside of backdrop
        nodes = instance.data["transientData"]["childNodes"]
        connections_in, connections_out = pnlib.get_dependent_nodes(nodes)
        instance.data["transientData"]["nodeConnectionsIn"] = connections_in
        instance.data["transientData"]["nodeConnectionsOut"] = connections_out

        # make label nicer
        instance.data["label"] = "{0} ({1} nodes)".format(
            bckn.name(), len(instance.data["transientData"]["childNodes"]))

        # get version
        version = instance.context.data.get('version')

        if version:
            instance.data['version'] = version

        self.log.debug("Backdrop instance collected: `{}`".format(instance))
