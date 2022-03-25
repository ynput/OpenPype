import os
import nuke
import pyblish.api
import openpype
from openpype.hosts.nuke.api.lib import maintained_selection


class ExtractSlateFrame(openpype.api.Extractor):
    """Extracts movie and thumbnail with baked in luts

    must be run after extract_render_local.py

    """

    order = pyblish.api.ExtractorOrder - 0.001
    label = "Extract Slate Frame"

    families = ["slate"]
    hosts = ["nuke"]


    def process(self, instance):
        if hasattr(self, "viewer_lut_raw"):
            self.viewer_lut_raw = self.viewer_lut_raw
        else:
            self.viewer_lut_raw = False

        with maintained_selection():
            self.log.debug("instance: {}".format(instance))
            self.log.debug("instance.data[families]: {}".format(
                instance.data["families"]))

            self.render_slate(instance)

    def render_slate(self, instance):
        node_subset_name = instance.data.get("name", None)
        node = instance[0]  # group node
        #TODO: have a more general approach. this assumes
        # slate is connected to render instance node now
        # and thus we get the source node as first input of slate.
        # This is needed since we modified the slate logic,
        # to copy itself after the lut. It made no sense to us to
        # have the lut break the colors and text on slate. 
        source_node = instance.data.get("slateNode").input(0)
        self.log.info("Creating staging dir...")

        if "representations" not in instance.data:
            instance.data["representations"] = list()

        staging_dir = os.path.normpath(
            os.path.dirname(instance.data['path']))

        instance.data["stagingDir"] = staging_dir

        self.log.info(
            "StagingDir `{0}`...".format(instance.data["stagingDir"]))

        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        frame_length = int(
            (frame_end - frame_start + 1) + (handle_start + handle_end)
        )

        temporary_nodes = []
        collection = instance.data.get("collection", None)

        if collection:
            # get path
            fname = os.path.basename(collection.format(
                "{head}{padding}{tail}"))
            fhead = collection.format("{head}")

            collected_frames_len = int(len(collection.indexes))

            # get first and last frame
            first_frame = min(collection.indexes) - 1
            self.log.info('frame_length: {}'.format(frame_length))
            self.log.info(
                'len(collection.indexes): {}'.format(collected_frames_len)
            )
            if ("slate" in instance.data["families"]) \
                    and (frame_length != collected_frames_len):
                first_frame += 1

            last_frame = first_frame
        else:
            fname = os.path.basename(instance.data.get("path", None))
            fhead = os.path.splitext(fname)[0] + "."
            first_frame = instance.data.get("frameStartHandle", None) - 1
            last_frame = first_frame

        if "#" in fhead:
            fhead = fhead.replace("#", "")[:-1]

        previous_node = source_node
<<<<<<< HEAD

        timecode_holder = nuke.createNode(
            "FrameHold",
            "name {}".format("OP_timecode_holder"))
        timecode_holder["firstFrame"].setValue(first_frame + 1)
        timecode_holder.setInput(0, previous_node)
        temporary_nodes.append(timecode_holder)

        slate_timecode = nuke.createNode(
            "AddTimeCode",
            "name {}".format("OP_slate_timecode"))
        slate_timecode["startcode"].setValue("[metadata -n OP_timecode_holder input/timecode]")
        slate_timecode["useFrame"].setValue(True)
        slate_timecode["frame"].setValue(first_frame + 1)
        slate_timecode.setInput(0, previous_node)
        previous_node = slate_timecode
        temporary_nodes.append(slate_timecode)

        instance.data.get("slateNode").setInput(0, previous_node)
=======
>>>>>>> 8782c048aad03605f8aa44544dbcaba0cdef974a

        # get input process and connect it to baking
        ipn = self.get_view_process_node()
        if ipn is not None:
            ipn.setInput(0, previous_node)
            previous_node = ipn
            temporary_nodes.append(ipn)

        if not self.viewer_lut_raw:
            dag_node = nuke.createNode("OCIODisplay")
            dag_node.setInput(0, previous_node)
            previous_node = dag_node
            temporary_nodes.append(dag_node)
        
        slate_node = self.get_slate_node(instance)
        if slate_node is not None:
            slate_node.setInput(0, previous_node)
            previous_node = slate_node
            temporary_nodes.append(slate_node)

        # create write node
        write_node = nuke.createNode("Write")
        file = fhead + "slate.dpx"
        path = os.path.join(staging_dir, file).replace("\\", "/")
        instance.data["slateFrame"] = path
        write_node["file"].setValue(path)
        write_node["file_type"].setValue("dpx")
        write_node["raw"].setValue(1)
        write_node.setInput(0, previous_node)
        temporary_nodes.append(write_node)

        # fill slate node with comments
        self.add_comment_slate_node(instance)

        # Render frames
        nuke.execute(write_node.name(), int(first_frame), int(last_frame))
        # also render slate as sequence frame
        nuke.execute(node_subset_name, int(first_frame), int(last_frame))

        self.log.debug(
            "slate frame path: {}".format(instance.data["slateFrame"]))

        instance.data.get("slateNode").setInput(0, source_node)

        # Clean up
        for node in temporary_nodes:
            nuke.delete(node)


    def get_slate_node(self, instance):

        #Same code execution as the view process selection.
        if nuke.selectedNodes():
            [n.setSelected(False) for n in nuke.selectedNodes()]
        slate_orig = instance.data.get("slateNode")
        slate_orig.setSelected(True)
        nuke.nodeCopy('%clipboard%')
        [n.setSelected(False) for n in nuke.selectedNodes()]  # Deselect all
        nuke.nodePaste('%clipboard%')
        slate = nuke.selectedNode()
        return slate


    def get_view_process_node(self):

        # Select only the target node
        if nuke.selectedNodes():
            [n.setSelected(False) for n in nuke.selectedNodes()]

        ipn_orig = None
        for v in [n for n in nuke.allNodes()
                  if "Viewer" in n.Class()]:
            ip = v['input_process'].getValue()
            ipn = v['input_process_node'].getValue()
            if "VIEWER_INPUT" not in ipn and ip:
                ipn_orig = nuke.toNode(ipn)
                ipn_orig.setSelected(True)

        if ipn_orig:
            nuke.nodeCopy('%clipboard%')

            [n.setSelected(False) for n in nuke.selectedNodes()]  # Deselect all

            nuke.nodePaste('%clipboard%')

            ipn = nuke.selectedNode()

            return ipn

    def add_comment_slate_node(self, instance):
        node = instance.data.get("slateNode")
        if not node:
            return

        comment = instance.context.data.get("comment")
        intent_value = instance.context.data.get("intent")
        if intent_value and isinstance(intent_value, dict):
            intent_value = intent_value.get("value")

        try:
            if node["f_submission_note"].getValue() == "":
                node["f_submission_note"].setValue(comment)
            if node["f_submission_note"].getValue() == "":
                node["f_submitting_for"].setValue(intent_value or "")
        except NameError:
            return
        instance.data.pop("slateNode")
