import os
import nuke
import pyblish.api
from avalon.nuke import lib as anlib
import pype


class ExtractReviewData(pype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.01
    label = "Extract Review Data Lut"

    families = ["review"]
    hosts = ["nuke"]

    def process(self, instance):

        self.log.debug("creating staging dir:")
        self.staging_dir(instance)

        with anlib.maintained_selection():
            if "still" not in instance.data["families"]:
                self.render_review_representation(instance,
                                                  representation="mov")
                self.render_review_representation(instance,
                                                  representation="jpeg")
            else:
                self.render_review_representation(instance, representation="jpeg")

    def render_review_representation(self,
                                     instance,
                                     representation="mov"):

        assert instance.data['representations'][0]['files'], "Instance data files should't be empty!"

        temporary_nodes = []
        stagingDir = instance.data[
            'representations'][0]["stagingDir"].replace("\\", "/")
        self.log.debug("StagingDir `{0}`...".format(stagingDir))

        collection = instance.data.get("collection", None)

        if collection:
            # get path
            fname = os.path.basename(collection.format(
                "{head}{padding}{tail}"))
            fhead = collection.format("{head}")

            # get first and last frame
            first_frame = min(collection.indexes)
            last_frame = max(collection.indexes)
        else:
            fname = os.path.basename(instance.data.get("path", None))
            fhead = os.path.splitext(fname)[0] + "."
            first_frame = instance.data.get("frameStart", None)
            last_frame = instance.data.get("frameEnd", None)

        rnode = nuke.createNode("Read")

        rnode["file"].setValue(
            os.path.join(stagingDir, fname).replace("\\", "/"))

        rnode["first"].setValue(first_frame)
        rnode["origfirst"].setValue(first_frame)
        rnode["last"].setValue(last_frame)
        rnode["origlast"].setValue(last_frame)
        temporary_nodes.append(rnode)
        previous_node = rnode

        # get input process and connect it to baking
        ipn = self.get_view_process_node()
        if ipn is not None:
            ipn.setInput(0, previous_node)
            previous_node = ipn
            temporary_nodes.append(ipn)

        reformat_node = nuke.createNode("Reformat")

        ref_node = self.nodes.get("Reformat", None)
        if ref_node:
            for k, v in ref_node:
                self.log.debug("k,v: {0}:{1}".format(k,v))
                if isinstance(v, unicode):
                    v = str(v)
                reformat_node[k].setValue(v)

        reformat_node.setInput(0, previous_node)
        previous_node = reformat_node
        temporary_nodes.append(reformat_node)

        dag_node = nuke.createNode("OCIODisplay")
        dag_node.setInput(0, previous_node)
        previous_node = dag_node
        temporary_nodes.append(dag_node)

        # create write node
        write_node = nuke.createNode("Write")

        if representation in "mov":
            file = fhead + "baked.mov"
            name = "baked"
            path = os.path.join(stagingDir, file).replace("\\", "/")
            self.log.debug("Path: {}".format(path))
            instance.data["baked_colorspace_movie"] = path
            write_node["file"].setValue(path)
            write_node["file_type"].setValue("mov")
            write_node["raw"].setValue(1)
            write_node.setInput(0, previous_node)
            temporary_nodes.append(write_node)
            tags = ["review", "delete"]

        elif representation in "jpeg":
            file = fhead + "jpeg"
            name = "thumbnail"
            path = os.path.join(stagingDir, file).replace("\\", "/")
            instance.data["thumbnail"] = path
            write_node["file"].setValue(path)
            write_node["file_type"].setValue("jpeg")
            write_node["raw"].setValue(1)
            write_node.setInput(0, previous_node)
            temporary_nodes.append(write_node)
            tags = ["thumbnail"]

            # retime for
            first_frame = int(last_frame) / 2
            last_frame = int(last_frame) / 2

        repre = {
            'name': name,
            'ext': representation,
            'files': file,
            "stagingDir": stagingDir,
            "frameStart": first_frame,
            "frameEnd": last_frame,
            "anatomy_template": "render",
            "tags": tags
        }
        instance.data["representations"].append(repre)

        # Render frames
        nuke.execute(write_node.name(), int(first_frame), int(last_frame))

        self.log.debug("representations: {}".format(instance.data["representations"]))

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)

    def get_view_process_node(self):
        """
        Will get any active view process.

        Arguments:
            self (class): in object definition

        Returns:
            nuke.Node: copy node of Input Process node
        """

        with anlib.maintained_selection():
            ipn_orig = None
            for v in [n for n in nuke.allNodes()
                      if "Viewer" in n.Class()]:
                ip = v['input_process'].getValue()
                ipn = v['input_process_node'].getValue()
                if "VIEWER_INPUT" not in ipn and ip:
                    ipn_orig = nuke.toNode(ipn)
                    ipn_orig.setSelected(True)

            if ipn_orig:
                # copy selected to clipboard
                nuke.nodeCopy('%clipboard%')
                # reset selection
                anlib.reset_selection()
                # paste node and selection is on it only
                nuke.nodePaste('%clipboard%')
                # assign to variable
                ipn = nuke.selectedNode()

                return ipn
