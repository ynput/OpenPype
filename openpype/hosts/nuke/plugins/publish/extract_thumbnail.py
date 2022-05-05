import sys
import os
import nuke
import pyblish.api
import openpype
from openpype.hosts.nuke.api.lib import maintained_selection


if sys.version_info[0] >= 3:
    unicode = str


class ExtractThumbnail(openpype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.01
    label = "Extract Thumbnail"

    families = ["review"]
    hosts = ["nuke"]

    # settings
    use_rendered = False
    bake_viewer_process = True
    bake_viewer_input_process = True
    nodes = {}


    def process(self, instance):
        if "render.farm" in instance.data["families"]:
            return

        with maintained_selection():
            self.log.debug("instance: {}".format(instance))
            self.log.debug("instance.data[families]: {}".format(
                instance.data["families"]))

            self.render_thumbnail(instance)

    def render_thumbnail(self, instance):
        first_frame = instance.data["frameStartHandle"]
        last_frame = instance.data["frameEndHandle"]

        # find frame range and define middle thumb frame
        mid_frame = int((last_frame - first_frame) / 2)

        node = instance[0]  # group node
        self.log.info("Creating staging dir...")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        staging_dir = os.path.normpath(
            os.path.dirname(instance.data['path']))

        instance.data["stagingDir"] = staging_dir

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        temporary_nodes = []

        # try to connect already rendered images
        if self.use_rendered:
            collection = instance.data.get("collection", None)
            self.log.debug("__ collection: `{}`".format(collection))

            if collection:
                # get path
                fname = os.path.basename(collection.format(
                    "{head}{padding}{tail}"))
                fhead = collection.format("{head}")

                thumb_fname = list(collection)[mid_frame]
            else:
                fname = thumb_fname = os.path.basename(
                    instance.data.get("path", None))
                fhead = os.path.splitext(fname)[0] + "."

            self.log.debug("__ fhead: `{}`".format(fhead))

            if "#" in fhead:
                fhead = fhead.replace("#", "")[:-1]

            path_render = os.path.join(
                staging_dir, thumb_fname).replace("\\", "/")
            self.log.debug("__ path_render: `{}`".format(path_render))

            # check if file exist otherwise connect to write node
            if os.path.isfile(path_render):
                rnode = nuke.createNode("Read")

                rnode["file"].setValue(path_render)

                # turn it raw if none of baking is ON
                if all([
                    not self.bake_viewer_input_process,
                    not self.bake_viewer_process
                ]):
                    rnode["raw"].setValue(True)

                temporary_nodes.append(rnode)
                previous_node = rnode
            else:
                previous_node = node

        # bake viewer input look node into thumbnail image
        if self.bake_viewer_input_process:
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
                self.log.debug("k, v: {0}:{1}".format(k, v))
                if isinstance(v, unicode):
                    v = str(v)
                reformat_node[k].setValue(v)

        reformat_node.setInput(0, previous_node)
        previous_node = reformat_node
        temporary_nodes.append(reformat_node)

        # bake viewer colorspace into thumbnail image
        if self.bake_viewer_process:
            dag_node = nuke.createNode("OCIODisplay")
            dag_node.setInput(0, previous_node)
            previous_node = dag_node
            temporary_nodes.append(dag_node)

        # create write node
        write_node = nuke.createNode("Write")
        file = fhead + "jpg"
        name = "thumbnail"
        path = os.path.join(staging_dir, file).replace("\\", "/")
        instance.data["thumbnail"] = path
        write_node["file"].setValue(path)
        write_node["file_type"].setValue("jpg")
        write_node["raw"].setValue(1)
        write_node.setInput(0, previous_node)
        temporary_nodes.append(write_node)
        tags = ["thumbnail", "publish_on_farm"]

        repre = {
            'name': name,
            'ext': "jpg",
            "outputName": "thumb",
            'files': file,
            "stagingDir": staging_dir,
            "tags": tags
        }
        instance.data["representations"].append(repre)

        # Render frames
        nuke.execute(write_node.name(), mid_frame, mid_frame)

        self.log.debug(
            "representations: {}".format(instance.data["representations"]))

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)

    def get_view_process_node(self):

        # Select only the target node
        if nuke.selectedNodes():
            [n.setSelected(False) for n in nuke.selectedNodes()]

        ipn_orig = None
        for v in [n for n in nuke.allNodes()
                  if "Viewer" == n.Class()]:
            ip = v['input_process'].getValue()
            ipn = v['input_process_node'].getValue()
            if "VIEWER_INPUT" not in ipn and ip:
                ipn_orig = nuke.toNode(ipn)
                ipn_orig.setSelected(True)

        if ipn_orig:
            nuke.nodeCopy('%clipboard%')

            # Deselect all
            [n.setSelected(False) for n in nuke.selectedNodes()]

            nuke.nodePaste('%clipboard%')

            ipn = nuke.selectedNode()

            return ipn
