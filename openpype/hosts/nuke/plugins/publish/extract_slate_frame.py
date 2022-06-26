import os
import nuke
import copy

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

    # Settings values
    # - can be extended by other attributes from node in the future
    key_value_mapping = {
        "f_submission_note": [True, "{comment}"],
        "f_submitting_for": [True, "{intent[value]}"],
        "f_vfx_scope_of_work": [False, ""]
    }

    def process(self, instance):
        if hasattr(self, "viewer_lut_raw"):
            self.viewer_lut_raw = self.viewer_lut_raw
        else:
            self.viewer_lut_raw = False

        if hasattr(self, "vwip_before_slate"):
            self.vwip_before_slate = self.vwip_before_slate
        else:
            self.vwip_before_slate = False

        with maintained_selection():
            self.log.debug("instance: {}".format(instance))
            self.log.debug("instance.data[families]: {}".format(
                instance.data["families"]))

            self.render_slate(instance)

    def render_slate(self, instance):
        node_subset_name = instance.data.get("name", None)
        node = instance[0]  # group node
        # get the slate node
        slate_node = instance.data.get("slateNode")
        # get the last comp node before slate
        last_comp_node = slate_node.input(0)

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
                    and (frame_length < collected_frames_len):
                first_frame += 1

            last_frame = first_frame
        else:
            fname = os.path.basename(instance.data.get("path", None))
            fhead = os.path.splitext(fname)[0] + "."
            first_frame = instance.data.get("frameStartHandle", None) - 1
            last_frame = first_frame

        if "#" in fhead:
            fhead = fhead.replace("#", "")[:-1]

        # Create a text file in staging dir to use as a
        # clipboard space. This fixes the erratic
        # behaviour nuke has with system clipboard '%clipboard%'
        # when used from openpype context.
        instance.data["clipboard"] = os.path.join(
            instance.data["stagingDir"],
            "{0}clipboard.txt".format(fhead)
        )

        # get the current viewer viewing lut, there seems to be
        # no setting in op that is relevant to this.
        # This is actually stored as an enum value, so it just works
        # with the viewer profile enum. The good side effect is that
        # ACES is quite inconsistent in nuke when presenting profile names,
        # So this prevents parsing errors when dealing with strings.
        viewer_lut = int(
            nuke.activeViewer().node()["viewerProcess"].getValue())

        # start from last comp node
        if self.vwip_before_slate:
            previous_node = last_comp_node
        else:
            previous_node = node

        self.clear_selection()

        # get input process and connect it to baking
        ipn = self.get_view_process_node(instance)
        if ipn is not None:
            ipn.setInput(0, previous_node)
            previous_node = ipn
            temporary_nodes.append(ipn)

        # compensate source to not have a double viewer lut applied
        # this is needed since baking viewer process happens now
        # before the slate and not after.
        if not self.viewer_lut_raw and self.vwip_before_slate:
            invlut_node = nuke.createNode("OCIODisplay")
            invlut_node.setInput(0, previous_node)
            invlut_node["view"].setValue(viewer_lut)
            invlut_node["invert"].setValue(True)
            previous_node = invlut_node
            temporary_nodes.append(invlut_node)

        # Copy the slate node after IPN because it does not make
        # any sense to apply luts to the slate.
        # It also helps to reformat the slate if it's set up
        # to be relative to source resolution.
        if self.vwip_before_slate:
            slate = self.get_slate_node(instance)
            if slate is not None:
                slate.setInput(0, previous_node)
                previous_node = slate
                temporary_nodes.append(slate)

        if not self.viewer_lut_raw:
            dag_node = nuke.createNode("OCIODisplay")
            dag_node.setInput(0, previous_node)
            dag_node["view"].setValue(viewer_lut)
            previous_node = dag_node
            temporary_nodes.append(dag_node)

        # create write node
        write_node = nuke.createNode("Write")
        file = fhead + "slate.png"
        path = os.path.join(staging_dir, file).replace("\\", "/")
        instance.data["slateFrame"] = path
        write_node["file"].setValue(path)
        write_node["file_type"].setValue("png")
        write_node["raw"].setValue(1)
        write_node.setInput(0, previous_node)
        temporary_nodes.append(write_node)

        # fill slate node with comments
        self.add_comment_slate_node(instance)

        # Reconnect slate OP output to slate for safety

        # Render frames
        nuke.execute(write_node.name(), int(first_frame), int(last_frame))
        # also render slate as sequence frame
        nuke.execute(node_subset_name, int(first_frame), int(last_frame))

        self.log.debug(
            "slate frame path: {}".format(instance.data["slateFrame"]))

        # Clean up (renamed to avoid naming collisions
        # with OP render node)
        for tmpnode in temporary_nodes:
            nuke.delete(tmpnode)

        slate_node.setInput(0, last_comp_node)
        node.setInput(0, slate_node)

    # Commodity function to clear selections.
    def clear_selection(self):
        if nuke.selectedNodes():
            for n in nuke.selectedNodes():
                n.setSelected(False)

    def get_view_process_node(self, instance):
        # get the clipboard temp file
        clipboard = instance.data["clipboard"]
        # Select only the target node
        self.clear_selection()
        ipn_orig = None
        for v in [n for n in nuke.allNodes()
                  if "Viewer" in n.Class()]:
            ip = v['input_process'].getValue()
            ipn = v['input_process_node'].getValue()
            if "VIEWER_INPUT" not in ipn and ip:
                ipn_orig = nuke.toNode(ipn)

        if ipn_orig:
            ipn_orig.setSelected(True)
            nuke.nodeCopy(clipboard)
            self.clear_selection()
            nuke.nodePaste(clipboard)
            ipn = nuke.selectedNode()
            return ipn

    def get_slate_node(self, instance):
        # get the clipboard temp file
        clipboard = instance.data["clipboard"]
        # Select only the target node
        self.clear_selection()
        slate_orig = None
        slate_orig = instance.data.get("slateNode")

        if slate_orig:
            slate_orig.setSelected(True)
            nuke.nodeCopy(clipboard)
            self.clear_selection()
            nuke.nodePaste(clipboard)
            slate = nuke.selectedNode()
            return slate

    def add_comment_slate_node(self, instance):
        node = instance.data.get("slateNode")
        if not node:
            return

        comment = instance.context.data.get("comment")
        intent = instance.context.data.get("intent")
        if not isinstance(intent, dict):
            intent = {
                "label": intent,
                "value": intent
            }

        fill_data = copy.deepcopy(instance.data["anatomyData"])
        fill_data.update({
            "custom": copy.deepcopy(
                instance.data.get("customData") or {}
            ),
            "comment": comment,
            "intent": intent
        })

        for key, value in self.key_value_mapping.items():
            enabled, template = value
            if not enabled:
                self.log.debug("Key \"{}\" is disabled".format(key))
                continue

            try:
                value = template.format(**fill_data)

            except ValueError:
                self.log.warning(
                    "Couldn't fill template \"{}\" with data: {}".format(
                        template, fill_data
                    ),
                    exc_info=True
                )
                continue

            except KeyError:
                self.log.warning(
                    (
                        "Template contains unknown key."
                        " Template \"{}\" Data: {}"
                    ).format(template, fill_data),
                    exc_info=True
                )
                continue

            try:
                node[key].setValue(value)
                self.log.info("Change key \"{}\" to value \"{}\"".format(
                    key, value
                ))
            except NameError:
                self.log.warning((
                    "Failed to set value \"{}\" on node attribute \"{}\""
                ).format(value))
