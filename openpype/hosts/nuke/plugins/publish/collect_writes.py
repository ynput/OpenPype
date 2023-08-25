import os
import nuke
import pyblish.api
from openpype.hosts.nuke import api as napi
from openpype.pipeline import publish


class CollectNukeWrites(pyblish.api.InstancePlugin,
                        publish.PrepRepresentationPluginMixin,
                        publish.ColormanagedPyblishPluginMixin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.0021
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]
    families = ["render", "prerender", "image"]

    def process(self, instance):
        creator_attributes = instance.data["creator_attributes"]
        group_node = instance.data["transientData"]["node"]

        write_node = self._write_node_helper(instance)
        if write_node is None:
            self.log.warning(
                "Created node '{}' is missing write node!".format(
                    group_node.name()
                )
            )
            return

        # get write file path
        write_file_path = nuke.filename(write_node)
        frame_start, frame_end = self._get_frame_range(write_node)

        # get colorspace and add to version data
        colorspace = napi.get_colorspace_from_node(write_node)

        # split operations by render target
        render_target = creator_attributes["render_target"]

        if render_target == "farm":
            self.add_farm_instance_data(instance)

        elif render_target == "frames":
            file_paths = self.prepare_collection_of_file_paths(
                write_file_path, frame_start, frame_end, only_existing=True
            )

            representation = self.prepare_representation(
                instance, file_paths, frame_start, frame_end
            )

            # QUESTION: should we set colorspace at this moment or downstream?
            self.set_representation_colorspace(
                representation, instance.context,
                colorspace=colorspace
            )
            instance.data["representations"].append(representation)

        elif render_target == "frames_farm":
            file_paths = self.prepare_collection_of_file_paths(
                write_file_path, frame_start, frame_end, only_existing=True
            )

            representation = self.prepare_representation(
                instance, file_paths, frame_start, frame_end
            )
            self.make_farm_publishing_representation(representation)

            # QUESTION: should we set colorspace at this moment or downstream?
            self.set_representation_colorspace(
                representation, instance.context,
                colorspace=colorspace
            )
            instance.data["representations"].append(representation)

            self.add_farm_instance_data(instance)

        # set additional instance data
        self._set_additional_instance_data(
            instance, write_node, frame_start, frame_end, colorspace)

    def _get_frame_range(self, write_node):
        """Get frame range data from instance.

        Args:
            write_node (nuke.Node): write node

        Returns:
            tuple: frame_start, frame_end
        """
        # Get frame range from workfile
        frame_start = int(nuke.root()["first_frame"].getValue())
        frame_end = int(nuke.root()["last_frame"].getValue())

        # Get frame range from write node if activated
        if write_node["use_limit"].getValue():
            frame_start = int(write_node["first"].getValue())
            frame_end = int(write_node["last"].getValue())

        return frame_start, frame_end

    def _set_additional_instance_data(
        self, instance, write_node, frame_start, frame_end, colorspace
    ):
        """Set additional instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            write_node (nuke.Node): write node
            frame_start (int): first frame
            frame_end (int): last frame
            colorspace (str): colorspace
        """
        creator_attributes = instance.data["creator_attributes"]
        family = instance.data["family"]
        render_target = creator_attributes["render_target"]

        # add targeted family to families
        instance.data["families"].append(
            "{}.{}".format(family, render_target)
        )
        self.log.debug("Appending render target to families: {}.{}".format(
            family, render_target)
        )

        # Determine defined file type
        ext = write_node["file_type"].value()

        # get frame range data
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]

        # get output paths
        write_file_path = nuke.filename(write_node)
        output_dir = os.path.dirname(write_file_path)

        # TODO: remove this when we have proper colorspace support
        version_data = {
            "colorspace": colorspace
        }

        instance.data.update({
            "versionData": version_data,
            "path": write_file_path,
            "outputDir": output_dir,
            "ext": ext,
            "colorspace": colorspace
        })

        if family == "render":
            instance.data.update({
                "handleStart": handle_start,
                "handleEnd": handle_end,
                "frameStart": frame_start + handle_start,
                "frameEnd": frame_end - handle_end,
                "frameStartHandle": frame_start,
                "frameEndHandle": frame_end,
            })
        else:
            instance.data.update({
                "handleStart": 0,
                "handleEnd": 0,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartHandle": frame_start,
                "frameEndHandle": frame_end,
            })

        # TODO temporarily set stagingDir as persistent for backward
        # compatibility. This is mainly focused on `renders`folders which
        # were previously not cleaned up (and could be used in read notes)
        # this logic should be removed and replaced with custom staging dir
        instance.data["stagingDir_persistent"] = True

    def _write_node_helper(self, instance):
        """Helper function to get write node from instance.

        Also sets instance transient data with child nodes.

        Args:
            instance (pyblish.api.Instance): pyblish instance

        Returns:
            nuke.Node: write node
        """
        # get all child nodes from group node
        child_nodes = napi.get_instance_group_node_childs(instance)

        # set child nodes to instance transient data
        instance.data["transientData"]["childNodes"] = child_nodes

        write_node = None
        for node_ in child_nodes:
            if node_.Class() == "Write":
                write_node = node_

        if not write_node:
            return None

        # for slate frame extraction
        instance.data["transientData"]["writeNode"] = write_node

        return write_node
