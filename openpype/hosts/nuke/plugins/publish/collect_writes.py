import os
import nuke
import pyblish.api
from openpype.hosts.nuke import api as napi
from openpype.pipeline import expected_files, publish


class CollectNukeWrites(pyblish.api.InstancePlugin,
                        publish.FarmPluginMixin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.0021
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]
    families = ["render", "prerender", "image"]

    # cashing
    _write_nodes = {}

    def process(self, instance):

        group_node = instance.data["transientData"]["node"]
        render_target = instance.data["render_target"]

        write_node = self._write_node_helper(instance)
        first_frame, last_frame = self._get_frame_range(instance)

        if write_node is None:
            self.log.warning(
                "Created node '{}' is missing write node!".format(
                    group_node.name()
                )
            )
            return

        # get colorspace and add to version data
        colorspace = napi.get_colorspace_from_node(write_node)

        if render_target == "frames":
            self._set_representation_with_existing_files(
                instance, first_frame, last_frame, colorspace)

        elif render_target == "frames_farm":
            collected_file_frames = self._set_representation_with_existing_files(
                instance, first_frame, last_frame, colorspace)

            self._set_expected_files(instance, collected_file_frames)

            self.add_farm_instance_data(instance)

        elif render_target == "farm":
            self.add_farm_instance_data(instance)

        # set additional instance data
        self._set_additional_instance_data(
            instance, render_target, first_frame, last_frame, colorspace)

    def _set_representation_with_existing_files(
        self,
        instance,
        first_frame,
        last_frame,
        colorspace
    ):
        """Set existing files data to instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            first_frame (int): first frame
            last_frame (int): last frame
            colorspace (str): colorspace

        Returns:
            list[str]: collected file frames
        """

        collected_file_frames = self._get_collected_frames(
            instance, first_frame, last_frame, )

        representation = self._get_existing_frames_representation(
            instance, instance, first_frame, collected_file_frames, colorspace)

        instance.data["representations"].append(representation)

        return collected_file_frames

    def _set_expected_files(self, instance, collected_file_frames):
        """Set expected files to instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            collected_file_frames (list[str]): collected file name frames
        """
        write_node = self._write_node_helper(instance)

        write_file_path = nuke.filename(write_node)
        output_dir = os.path.dirname(write_file_path)

        instance.data["expectedFiles"] = [
            os.path.join(output_dir, source_file)
            for source_file in collected_file_frames
        ]

    def _get_frame_range(self, instance):
        """Get frame range data from instance.

        Args:
            instance (pyblish.api.Instance): pyblish instance

        Returns:
            tuple: first_frame, last_frame
        """

        write_node = self._write_node_helper(instance)

        # Get frame range from workfile
        first_frame = int(nuke.root()["first_frame"].getValue())
        last_frame = int(nuke.root()["last_frame"].getValue())

        # Get frame range from write node if activated
        if write_node["use_limit"].getValue():
            first_frame = int(write_node["first"].getValue())
            last_frame = int(write_node["last"].getValue())

        return first_frame, last_frame

    def _set_additional_instance_data(
        self, instance, render_target, first_frame, last_frame, colorspace
    ):
        """Set additional instance data.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            render_target (str): render target
            first_frame (int): first frame
            last_frame (int): last frame
            colorspace (str): colorspace
        """
        family = instance.data["family"]

        # add targeted family to families
        instance.data["families"].append(
            "{}.{}".format(family, render_target)
        )
        self.log.debug("Appending render target to families: {}.{}".format(
            family, render_target)
        )

        write_node = self._write_node_helper(instance)

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
                "frameStart": first_frame + handle_start,
                "frameEnd": last_frame - handle_end,
                "frameStartHandle": first_frame,
                "frameEndHandle": last_frame,
            })
        else:
            instance.data.update({
                "handleStart": 0,
                "handleEnd": 0,
                "frameStart": first_frame,
                "frameEnd": last_frame,
                "frameStartHandle": first_frame,
                "frameEndHandle": last_frame,
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
        instance_name = instance.data["name"]

        if self._write_nodes.get(instance_name):
            # return cashed write node
            return self._write_nodes[instance_name]

        # get all child nodes from group node
        child_nodes = napi.get_instance_group_node_childs(instance)

        # set child nodes to instance transient data
        instance.data["transientData"]["childNodes"] = child_nodes

        write_node = None
        for node_ in child_nodes:
            if node_.Class() == "Write":
                write_node = node_

        if write_node:
            # for slate frame extraction
            instance.data["transientData"]["writeNode"] = write_node
            # add to cache
            self._write_nodes[instance_name] = write_node

            return self._write_nodes[instance_name]

    def _get_existing_frames_representation(
        self,
        instance,
        first_frame,
        last_frame,
        collected_file_frames,
        colorspace,
    ):
        """Get existing frames representation.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            first_frame (int): first frame
            last_frame (int): last frame
            collected_file_frames (list[str]): collected file name frames

        Returns:
            dict: representation
        """
        families = set(instance.data["families"] + instance.data["family"])
        write_node = self._write_node_helper(instance)

        write_file_path = nuke.filename(write_node)
        output_dir = os.path.dirname(write_file_path)

        # Determine defined file type
        file_ext = write_node["file_type"].value()

        return expected_files.get_representation_with_expected_files(
            families,
            file_ext,
            output_dir,
            first_frame,
            last_frame,
            collected_file_frames,
            colorspace,
            self.log
        )

    def _get_collected_frames(self, instance, first_frame, last_frame):
        """Get collected frames.

        Args:
            instance (pyblish.api.Instance): pyblish instance
            first_frame (int): first frame
            last_frame (int): last frame

        Returns:
            list[str]: collected file frames
        """

        write_node = self._write_node_helper(instance)

        write_file_path = nuke.filename(write_node)
        output_dir = os.path.dirname(write_file_path)

        # get file path knob
        node_file_knob = write_node["file"]
        # list file paths based on input frames
        expected_paths = list(sorted({
            node_file_knob.evaluate(frame)
            for frame in range(first_frame, last_frame + 1)
        }))

        # convert only to base names
        expected_filenames = {
            os.path.basename(filepath)
            for filepath in expected_paths
        }

        # make sure files are existing at folder
        collected_file_frames = [
            filename
            for filename in os.listdir(output_dir)
            if filename in expected_filenames
        ]

        return collected_file_frames
