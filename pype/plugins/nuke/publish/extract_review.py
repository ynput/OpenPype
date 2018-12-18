import os
import nuke
import pyblish.api
import pype


class ExtractDataForReview(pype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.01
    label = "Data for review"
    optional = True

    families = ["write"]
    hosts = ["nuke"]
    family_targets = [".local", ".review"]

    def process(self, instance):

        families = [f for f in instance.data["families"]
                    for search in self.family_targets
                    if search in f]
        if not families:
            return

        # Store selection
        selection = [i for i in nuke.allNodes() if i["selected"].getValue()]

        # Deselect all nodes to prevent external connections
        [i["selected"].setValue(False) for i in nuke.allNodes()]

        self.staging_dir(instance)
        self.render_review_representation(instance,
                                          representation="mov")
        self.transcode_mov(instance)
        self.render_review_representation(instance,
                                          representation="jpeg")
        # Restore selection
        [i["selected"].setValue(False) for i in nuke.allNodes()]
        [i["selected"].setValue(True) for i in selection]

    def transcode_mov(self, instance):
        import subprocess

        collection = instance.data["collection"]
        staging_dir = instance.data["stagingDir"]
        file_name = collection.format("{head}mov")

        review_mov = os.path.join(staging_dir, file_name)

        if instance.data.get("baked_colorspace_movie"):
            args = [
                "ffmpeg", "-y",
                "-i", instance.data["baked_colorspace_movie"],
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-timecode", "00:00:00:01",
            ]

        args.append(review_mov)

        self.log.debug("Executing args: {0}".format(args))

        self.log.info("transcoding review mov: {0}".format(review_mov))
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            cwd=os.path.dirname(args[-1])
        )

        output = p.communicate()[0]

        if p.returncode != 0:
            raise ValueError(output)

        self.log.debug("Removing `{0}`...".format(
            instance.data["baked_colorspace_movie"]))
        os.remove(instance.data["baked_colorspace_movie"])

        instance.data["files"].append(file_name)

    def render_review_representation(self,
                                     instance,
                                     representation="mov"):

        assert instance.data['files'], "Instance data files should't be empty!"

        import clique
        import nuke
        temporary_nodes = []
        staging_dir = instance.data["stagingDir"]

        collection = instance.data.get("collection", None)

        if not collection:
            collections, remainder = clique.assemble(*instance.data['files'])
            collection = collections[0]
            instance.data["collection"] = collection

        # Create nodes
        first_frame = min(collection.indexes)
        last_frame = max(collection.indexes)

        self.log.warning("first_frame: {}".format(first_frame))
        self.log.warning("last_frame: {}".format(last_frame))

        node = previous_node = nuke.createNode("Read")

        node["file"].setValue(
            os.path.join(staging_dir,
                         os.path.basename(collection.format(
                             "{head}{padding}{tail}"))).replace("\\", "/"))

        node["first"].setValue(first_frame)
        node["origfirst"].setValue(first_frame)
        node["last"].setValue(last_frame)
        node["origlast"].setValue(last_frame)
        temporary_nodes.append(node)

        reformat_node = nuke.createNode("Reformat")
        reformat_node["format"].setValue("HD_1080")
        reformat_node["resize"].setValue("fit")
        reformat_node["filter"].setValue("Lanczos6")
        reformat_node["black_outside"].setValue(True)
        reformat_node.setInput(0, previous_node)
        previous_node = reformat_node
        temporary_nodes.append(reformat_node)

        viewer_process_node = nuke.ViewerProcess.node()
        dag_node = None
        if viewer_process_node:
            dag_node = nuke.createNode(viewer_process_node.Class())
            dag_node.setInput(0, previous_node)
            previous_node = dag_node
            temporary_nodes.append(dag_node)
            # Copy viewer process values
            excludedKnobs = ["name", "xpos", "ypos"]
            for item in viewer_process_node.knobs().keys():
                if item not in excludedKnobs and item in dag_node.knobs():
                    x1 = viewer_process_node[item]
                    x2 = dag_node[item]
                    x2.fromScript(x1.toScript(False))
        else:
            self.log.warning("No viewer node found.")

        # create write node
        write_node = nuke.createNode("Write")

        if representation in "mov":
            file = collection.format("{head}baked.mov")
            path = os.path.join(staging_dir, file).replace("\\", "/")
            instance.data["baked_colorspace_movie"] = path
            write_node["file"].setValue(path)
            write_node["file_type"].setValue("mov")
            write_node["raw"].setValue(1)
            write_node.setInput(0, previous_node)
            temporary_nodes.append(write_node)

        elif representation in "jpeg":
            file = collection.format("{head}jpeg")
            path = os.path.join(staging_dir, file).replace("\\", "/")
            instance.data["thumbnail"] = path
            write_node["file"].setValue(path)
            write_node["file_type"].setValue("jpeg")
            write_node["raw"].setValue(1)
            write_node.setInput(0, previous_node)
            temporary_nodes.append(write_node)

            # retime for
            first_frame = int(last_frame)/2
            last_frame = int(last_frame)/2
            # add into files for integration as representation
            instance.data["files"].append(file)

        # Render frames
        nuke.execute(write_node.name(), int(first_frame), int(last_frame))

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)
