import sys
import os
import nuke
import pyblish.api
import openpype
from openpype.hosts.nuke.api import (
    maintained_selection,
    get_view_process_node
)


if sys.version_info[0] >= 3:
    unicode = str


class ExtractThumbnail(openpype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.011
    label = "Extract Thumbnail"

    families = ["review"]
    hosts = ["nuke"]

    # presets
    nodes = {}

    def process(self, instance):
        if "render.farm" in instance.data["families"]:
            return

        with maintained_selection():
            self.log.debug("instance: {}".format(instance))
            self.log.debug("instance.data[families]: {}".format(
                instance.data["families"]))

            if instance.data.get("bakePresets"):
                for o_name, o_data in instance.data["bakePresets"].items():
                    self.render_thumbnail(instance, o_name, **o_data)
            else:
                viewer_process_swithes = {
                    "bake_viewer_process": True,
                    "bake_viewer_input_process": True
                }
                self.render_thumbnail(instance, None, **viewer_process_swithes)

    def render_thumbnail(self, instance, output_name=None, **kwargs):
        # solve output name if any is set
        output_name = output_name or ""
        if output_name:
            output_name = "_" + output_name

        bake_viewer_process = kwargs["bake_viewer_process"]
        bake_viewer_input_process_node = kwargs[
            "bake_viewer_input_process"]

        node = instance[0]  # group node
        self.log.info("Creating staging dir...")

        if "representations" not in instance.data:
            instance.data["representations"] = list()

        staging_dir = os.path.normpath(
            os.path.dirname(instance.data['path']))

        instance.data["stagingDir"] = staging_dir

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        temporary_nodes = []
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

        if "#" in fhead:
            fhead = fhead.replace("#", "")[:-1]

        path_render = os.path.join(staging_dir, fname).replace("\\", "/")
        # check if file exist otherwise connect to write node
        if os.path.isfile(path_render):
            rnode = nuke.createNode("Read")

            rnode["file"].setValue(path_render)

            rnode["first"].setValue(first_frame)
            rnode["origfirst"].setValue(first_frame)
            rnode["last"].setValue(last_frame)
            rnode["origlast"].setValue(last_frame)
            temporary_nodes.append(rnode)
            previous_node = rnode
        else:
            previous_node = node

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

        # only create colorspace baking if toggled on
        if bake_viewer_process:
            if bake_viewer_input_process_node:
                # get input process and connect it to baking
                ipn = get_view_process_node()
                if ipn is not None:
                    ipn.setInput(0, previous_node)
                    previous_node = ipn
                    temporary_nodes.append(ipn)

            dag_node = nuke.createNode("OCIODisplay")
            dag_node.setInput(0, previous_node)
            previous_node = dag_node
            temporary_nodes.append(dag_node)

        # create write node
        write_node = nuke.createNode("Write")
        file = fhead[:-1] + output_name + ".jpg"
        name = "thumbnail"
        path = os.path.join(staging_dir, file).replace("\\", "/")
        instance.data["thumbnail"] = path
        write_node["file"].setValue(path)
        write_node["file_type"].setValue("jpg")
        write_node["raw"].setValue(1)
        write_node.setInput(0, previous_node)
        temporary_nodes.append(write_node)
        tags = ["thumbnail", "publish_on_farm"]

        # retime for
        mid_frame = int((int(last_frame) - int(first_frame)) / 2) \
            + int(first_frame)
        first_frame = int(last_frame) / 2
        last_frame = int(last_frame) / 2

        repre = {
            'name': name,
            'ext': "jpg",
            "outputName": "thumb",
            'files': file,
            "stagingDir": staging_dir,
            "frameStart": first_frame,
            "frameEnd": last_frame,
            "tags": tags
        }
        instance.data["representations"].append(repre)

        # Render frames
        nuke.execute(write_node.name(), int(mid_frame), int(mid_frame))

        self.log.debug(
            "representations: {}".format(instance.data["representations"]))

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)
