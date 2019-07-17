import os
import nuke
import pyblish.api
import pype


class ExtractReviewData(pype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder + 0.01
    label = "Extract Review Data"

    families = ["review"]
    hosts = ["nuke"]

    def process(self, instance):

        # Store selection
        selection = [i for i in nuke.allNodes() if i["selected"].getValue()]
        # Deselect all nodes to prevent external connections
        [i["selected"].setValue(False) for i in nuke.allNodes()]
        self.log.debug("creating staging dir:")
        self.staging_dir(instance)

        self.log.debug("instance: {}".format(instance))
        self.log.debug("instance.data[families]: {}".format(
            instance.data["families"]))

        if "still" not in instance.data["families"]:
            self.render_review_representation(instance,
                                              representation="mov")
            self.render_review_representation(instance,
                                              representation="jpeg")
        else:
            self.render_review_representation(instance, representation="jpeg")

        # Restore selection
        [i["selected"].setValue(False) for i in nuke.allNodes()]
        [i["selected"].setValue(True) for i in selection]

    def render_review_representation(self,
                                     instance,
                                     representation="mov"):

        assert instance.data['representations'][0]['files'], "Instance data files should't be empty!"

        import nuke
        temporary_nodes = []
        stagingDir = instance.data['representations'][0]["stagingDir"].replace("\\", "/")
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
            first_frame = instance.data.get("startFrame", None)
            last_frame = instance.data.get("endFrame", None)

        node = previous_node = nuke.createNode("Read")

        node["file"].setValue(
            os.path.join(stagingDir, fname).replace("\\", "/"))

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
            file = fhead + "baked.mov"
            path = os.path.join(stagingDir, file).replace("\\", "/")
            self.log.debug("Path: {}".format(path))
            instance.data["baked_colorspace_movie"] = path
            write_node["file"].setValue(path)
            write_node["file_type"].setValue("mov")
            write_node["raw"].setValue(1)
            write_node.setInput(0, previous_node)
            temporary_nodes.append(write_node)
            thumbnail = False
            preview = True
            tags = ["review"]

        elif representation in "jpeg":
            file = fhead + "jpeg"
            path = os.path.join(stagingDir, file).replace("\\", "/")
            instance.data["thumbnail"] = path
            write_node["file"].setValue(path)
            write_node["file_type"].setValue("jpeg")
            write_node["raw"].setValue(1)
            write_node.setInput(0, previous_node)
            temporary_nodes.append(write_node)
            thumbnail = True
            preview = False
            tags = ["thumbnail"]

            # retime for
            first_frame = int(last_frame) / 2
            last_frame = int(last_frame) / 2

        repre = {
            'name': representation,
            'ext': representation,
            'files': file,
            "stagingDir": stagingDir,
            "startFrame": first_frame,
            "endFrame": last_frame,
            "anatomy_template": "render",
            "thumbnail": thumbnail,
            "preview": preview,
            "tags": tags
        }
        instance.data["representations"].append(repre)

        # Render frames
        nuke.execute(write_node.name(), int(first_frame), int(last_frame))

        self.log.debug("representations: {}".format(instance.data["representations"]))

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)
