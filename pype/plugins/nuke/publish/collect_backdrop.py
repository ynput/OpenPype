import pyblish.api
import pype.api as pype
from pype.hosts.nuke import lib as pnlib
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

        # get all connections from outside of backdrop
        nodes = instance[1:]
        connections_in, connections_out = pnlib.get_dependent_nodes(nodes)
        instance.data["connections_in"] = connections_in
        instance.data["connections_out"] = connections_out

        # make label nicer
        instance.data["label"] = "{0} ({1} nodes)".format(
            bckn.name(), len(instance)-1)

        instance.data["families"].append(instance.data["family"])

        # Get frame range
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = int(nuke.root()["first_frame"].getValue())
        last_frame = int(nuke.root()["last_frame"].getValue())

        # get version
        version = instance.context.data.get('version')

        if not version:
            raise RuntimeError("Script name has no version in the name.")

        instance.data['version'] = version

        # Add version data to instance
        version_data = {
            "handles": handle_start,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "version": int(version),
            "families": [instance.data["family"]] + instance.data["families"],
            "subset": instance.data["subset"],
            "fps": instance.context.data["fps"]
        }

        instance.data.update({
            "versionData": version_data,
            "frameStart": first_frame,
            "frameEnd": last_frame
        })
        self.log.info("Backdrop content collected: `{}`".format(instance[:]))
        self.log.info("Backdrop instance collected: `{}`".format(instance))
