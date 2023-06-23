import os
from pprint import pformat
import nuke
import pyblish.api
from openpype.hosts.nuke import api as napi
from openpype.pipeline import publish


class CollectNukeWrites(pyblish.api.InstancePlugin,
                        publish.ColormanagedPyblishPluginMixin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.0021
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]
    families = ["render", "prerender", "image"]

    def process(self, instance):
        self.log.debug(pformat(instance.data))
        creator_attributes = instance.data["creator_attributes"]
        instance.data.update(creator_attributes)

        group_node = instance.data["transientData"]["node"]
        render_target = instance.data["render_target"]
        family = instance.data["family"]
        families = instance.data["families"]

        # add targeted family to families
        instance.data["families"].append(
            "{}.{}".format(family, render_target)
        )
        if instance.data.get("review"):
            instance.data["families"].append("review")

        child_nodes = napi.get_instance_group_node_childs(instance)
        instance.data["transientData"]["childNodes"] = child_nodes

        write_node = None
        for x in child_nodes:
            if x.Class() == "Write":
                write_node = x

        if write_node is None:
            self.log.warning(
                "Created node '{}' is missing write node!".format(
                    group_node.name()
                )
            )
            return

        instance.data["writeNode"] = write_node
        self.log.debug("checking instance: {}".format(instance))

        # Determine defined file type
        ext = write_node["file_type"].value()

        # Get frame range
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = int(nuke.root()["first_frame"].getValue())
        last_frame = int(nuke.root()["last_frame"].getValue())
        frame_length = int(last_frame - first_frame + 1)

        if write_node["use_limit"].getValue():
            first_frame = int(write_node["first"].getValue())
            last_frame = int(write_node["last"].getValue())

        write_file_path = nuke.filename(write_node)
        output_dir = os.path.dirname(write_file_path)

        # get colorspace and add to version data
        colorspace = napi.get_colorspace_from_node(write_node)

        self.log.debug('output dir: {}'.format(output_dir))

        if render_target == "frames":
            representation = {
                'name': ext,
                'ext': ext,
                "stagingDir": output_dir,
                "tags": []
            }

            # get file path knob
            node_file_knob = write_node["file"]
            # list file paths based on input frames
            expected_paths = list(sorted({
                node_file_knob.evaluate(frame)
                for frame in range(first_frame, last_frame + 1)
            }))

            # convert only to base names
            expected_filenames = [
                os.path.basename(filepath)
                for filepath in expected_paths
            ]

            # make sure files are existing at folder
            collected_frames = [
                filename
                for filename in os.listdir(output_dir)
                if filename in expected_filenames
            ]

            if collected_frames:
                collected_frames_len = len(collected_frames)
                frame_start_str = "%0{}d".format(
                    len(str(last_frame))) % first_frame
                representation['frameStart'] = frame_start_str

                # in case slate is expected and not yet rendered
                self.log.debug("_ frame_length: {}".format(frame_length))
                self.log.debug("_ collected_frames_len: {}".format(
                    collected_frames_len))

                # this will only run if slate frame is not already
                # rendered from previews publishes
                if (
                    "slate" in families
                    and frame_length == collected_frames_len
                    and family == "render"
                ):
                    frame_slate_str = (
                        "{{:0{}d}}".format(len(str(last_frame)))
                    ).format(first_frame - 1)

                    slate_frame = collected_frames[0].replace(
                        frame_start_str, frame_slate_str)
                    collected_frames.insert(0, slate_frame)

                if collected_frames_len == 1:
                    representation['files'] = collected_frames.pop()
                else:
                    representation['files'] = collected_frames

                # inject colorspace data
                self.set_representation_colorspace(
                    representation, instance.context,
                    colorspace=colorspace
                )

            instance.data["representations"].append(representation)
            self.log.info("Publishing rendered frames ...")

        elif render_target == "farm":
            farm_keys = ["farm_chunk", "farm_priority", "farm_concurrency"]
            for key in farm_keys:
                # Skip if key is not in creator attributes
                if key not in creator_attributes:
                    continue
                # Add farm attributes to instance
                instance.data[key] = creator_attributes[key]

            # Farm rendering
            instance.data["transfer"] = False
            instance.data["farm"] = True
            self.log.info("Farm rendering ON ...")

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

        # make sure rendered sequence on farm will
        # be used for extract review
        if not instance.data.get("review"):
            instance.data["useSequenceForReview"] = False

        self.log.debug("instance.data: {}".format(pformat(instance.data)))
