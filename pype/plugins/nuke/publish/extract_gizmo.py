import pyblish.api
from avalon.nuke import lib as anlib
from pype.hosts.nuke import lib as pnlib
from pype.hosts.nuke import utils as pnutils
import nuke
import os
import pype


class ExtractGizmo(pype.api.Extractor):
    """Extracting Gizmo (Group) node

    Will create nuke script only with the Gizmo node.
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Gizmo (Group)"
    hosts = ["nuke"]
    families = ["gizmo"]

    def process(self, instance):
        tmp_nodes = list()
        orig_grpn = instance[0]
        # Define extract output file path
        stagingdir = self.staging_dir(instance)
        filename = "{0}.nk".format(instance.name)
        path = os.path.join(stagingdir, filename)

        # maintain selection
        with anlib.maintained_selection():
            orig_grpn_name = orig_grpn.name()
            tmp_grpn_name = orig_grpn_name + "_tmp"
            # select original group node
            anlib.select_nodes([orig_grpn])

            # copy to clipboard
            nuke.nodeCopy("%clipboard%")

            # reset selection to none
            anlib.reset_selection()

            # paste clipboard
            nuke.nodePaste("%clipboard%")

            # assign pasted node
            copy_grpn = nuke.selectedNode()
            copy_grpn.setXYpos((orig_grpn.xpos() + 120), orig_grpn.ypos())

            # convert gizmos to groups
            pnutils.bake_gizmos_recursively(copy_grpn)

            # remove avalonknobs
            knobs = copy_grpn.knobs()
            avalon_knobs = [k for k in knobs.keys()
                            for ak in ["avalon:", "ak:"]
                            if ak in k]
            avalon_knobs.append("publish")
            for ak in avalon_knobs:
                copy_grpn.removeKnob(knobs[ak])

            # add to temporary nodes
            tmp_nodes.append(copy_grpn)

            # swap names
            orig_grpn.setName(tmp_grpn_name)
            copy_grpn.setName(orig_grpn_name)

            # create tmp nk file
            # save file to the path
            nuke.nodeCopy(path)

            # Clean up
            for tn in tmp_nodes:
                nuke.delete(tn)

            # rename back to original
            orig_grpn.setName(orig_grpn_name)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        # create representation
        representation = {
            'name': 'gizmo',
            'ext': 'nk',
            'files': filename,
            "stagingDir": stagingdir
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '{}' to: {}".format(
            instance.name, path))

        self.log.info("Data {}".format(
            instance.data))
