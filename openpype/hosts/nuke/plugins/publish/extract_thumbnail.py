import sys
import os
import nuke
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.nuke import api as napi
from openpype.hosts.nuke.api.lib import set_node_knobs_from_settings


# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    unicode = str


class ExtractThumbnail(publish.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.011
    label = "Extract Thumbnail"

    families = ["review"]
    hosts = ["nuke"]

    # settings
    use_rendered = False
    bake_viewer_process = True
    bake_viewer_input_process = True
    nodes = {}
    reposition_nodes = None

    def process(self, instance):
        if instance.data.get("farm"):
            return

        with napi.maintained_selection():
            self.log.debug("instance: {}".format(instance))
            self.log.debug("instance.data[families]: {}".format(
                instance.data["families"]))

            if instance.data.get("bakePresets"):
                for o_name, o_data in instance.data["bakePresets"].items():
                    self.render_thumbnail(instance, o_name, **o_data)
            else:
                viewer_process_switches = {
                    "bake_viewer_process": True,
                    "bake_viewer_input_process": True
                }
                self.render_thumbnail(
                    instance, None, **viewer_process_switches)

    def render_thumbnail(self, instance, output_name=None, **kwargs):
        first_frame = instance.data["frameStartHandle"]
        last_frame = instance.data["frameEndHandle"]
        colorspace = instance.data["colorspace"]

        # find frame range and define middle thumb frame
        mid_frame = int((last_frame - first_frame) / 2)

        # solve output name if any is set
        output_name = output_name or ""

        bake_viewer_process = kwargs["bake_viewer_process"]
        bake_viewer_input_process_node = kwargs[
            "bake_viewer_input_process"]

        node = instance.data["transientData"]["node"]  # group node
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
        previous_node = node
        collection = instance.data.get("collection", None)
        self.log.debug("__ collection: `{}`".format(collection))

        if collection:
            # get path
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

        if self.use_rendered and os.path.isfile(path_render):
            # check if file exist otherwise connect to write node
            rnode = nuke.createNode("Read")
            rnode["file"].setValue(path_render)
            rnode["colorspace"].setValue(colorspace)

            # turn it raw if none of baking is ON
            if all([
                not self.bake_viewer_input_process,
                not self.bake_viewer_process
            ]):
                rnode["raw"].setValue(True)

            temporary_nodes.append(rnode)
            previous_node = rnode

        if self.reposition_nodes is None:
            # [deprecated] create reformat node old way
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
        else:
            # create reformat node new way
            for repo_node in self.reposition_nodes:
                node_class = repo_node["node_class"]
                knobs = repo_node["knobs"]
                node = nuke.createNode(node_class)
                set_node_knobs_from_settings(node, knobs)

                # connect in order
                node.setInput(0, previous_node)
                previous_node = node
                temporary_nodes.append(node)

        # only create colorspace baking if toggled on
        if bake_viewer_process:
            if bake_viewer_input_process_node:
                # get input process and connect it to baking
                ipn = napi.get_view_process_node()
                if ipn is not None:
                    ipn.setInput(0, previous_node)
                    previous_node = ipn
                    temporary_nodes.append(ipn)

            dag_node = nuke.createNode("OCIODisplay")
            dag_node.setInput(0, previous_node)
            previous_node = dag_node
            temporary_nodes.append(dag_node)

        thumb_name = "thumbnail"
        # only add output name and
        # if there are more than one bake preset
        if (
            output_name
            and len(instance.data.get("bakePresets", {}).keys()) > 1
        ):
            thumb_name = "{}_{}".format(output_name, thumb_name)

        # create write node
        write_node = nuke.createNode("Write")
        file = fhead[:-1] + thumb_name + ".jpg"
        thumb_path = os.path.join(staging_dir, file).replace("\\", "/")

        # add thumbnail to cleanup
        instance.context.data["cleanupFullPaths"].append(thumb_path)

        # make sure only one thumbnail path is set
        # and it is existing file
        instance_thumb_path = instance.data.get("thumbnailPath")
        if not instance_thumb_path or not os.path.isfile(instance_thumb_path):
            instance.data["thumbnailPath"] = thumb_path

        write_node["file"].setValue(thumb_path)
        write_node["file_type"].setValue("jpg")
        write_node["raw"].setValue(1)
        write_node.setInput(0, previous_node)
        temporary_nodes.append(write_node)

        repre = {
            'name': thumb_name,
            'ext': "jpg",
            "outputName": thumb_name,
            'files': file,
            "stagingDir": staging_dir,
            "tags": ["thumbnail", "publish_on_farm", "delete"]
        }
        instance.data["representations"].append(repre)

        # Render frames
        nuke.execute(write_node.name(), mid_frame, mid_frame)

        self.log.debug(
            "representations: {}".format(instance.data["representations"]))

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)
