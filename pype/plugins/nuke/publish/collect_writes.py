import os
import nuke
import pyblish.api


@pyblish.api.log
class CollectNukeWrites(pyblish.api.InstancePlugin):
    """Collect all write nodes."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect Writes"
    hosts = ["nuke", "nukeassist"]
    families = ["write"]

    # preset attributes
    sync_workfile_version = True

    def process(self, instance):
        families = instance.data["families"]

        node = None
        for x in instance:
            if x.Class() == "Write":
                node = x

        if node is None:
            return

        self.log.debug("checking instance: {}".format(instance))

        # Determine defined file type
        ext = node["file_type"].value()

        # Determine output type
        output_type = "img"
        if ext == "mov":
            output_type = "mov"

        # Get frame range
        handle_start = instance.context.data["handleStart"]
        handle_end = instance.context.data["handleEnd"]
        first_frame = int(nuke.root()["first_frame"].getValue())
        last_frame = int(nuke.root()["last_frame"].getValue())
        frame_length = int(
            last_frame - first_frame + 1
        )

        if node["use_limit"].getValue():
            first_frame = int(node["first"].getValue())
            last_frame = int(node["last"].getValue())

        # get path
        path = nuke.filename(node)
        output_dir = os.path.dirname(path)
        self.log.debug('output dir: {}'.format(output_dir))

        if not next((f for f in families
                     if "prerender" in f),
                    None) and self.sync_workfile_version:
            # get version to instance for integration
            instance.data['version'] = instance.context.data["version"]

            self.log.debug('Write Version: %s' % instance.data('version'))

        # create label
        name = node.name()
        # Include start and end render frame in label
        label = "{0} ({1}-{2})".format(
            name,
            int(first_frame),
            int(last_frame)
        )

        if [fm for fm in families
                if fm in ["render", "prerender"]]:
            if "representations" not in instance.data:
                instance.data["representations"] = list()

                representation = {
                    'name': ext,
                    'ext': ext,
                    "stagingDir": output_dir
                }

            try:
                collected_frames = [f for f in os.listdir(output_dir)
                                    if ext in f]
                if collected_frames:
                    collected_frames_len = len(collected_frames)
                    frame_start_str = "%0{}d".format(
                        len(str(last_frame))) % first_frame
                    representation['frameStart'] = frame_start_str

                    # in case slate is expected and not yet rendered
                    self.log.debug("_ frame_length: {}".format(frame_length))
                    self.log.debug(
                        "_ collected_frames_len: {}".format(
                            collected_frames_len))
                    # this will only run if slate frame is not already
                    # rendered from previews publishes
                    if "slate" in instance.data["families"] \
                            and (frame_length == collected_frames_len) \
                            and ("prerender" not in instance.data["families"]):
                        frame_slate_str = "%0{}d".format(
                            len(str(last_frame))) % (first_frame - 1)
                        slate_frame = collected_frames[0].replace(
                            frame_start_str, frame_slate_str)
                        collected_frames.insert(0, slate_frame)

                representation['files'] = collected_frames
                instance.data["representations"].append(representation)
            except Exception:
                instance.data["representations"].append(representation)
                self.log.debug("couldn't collect frames: {}".format(label))

        # Add version data to instance
        version_data = {
            "colorspace": node["colorspace"].value(),
        }

        instance.data["family"] = "write"
        group_node = [x for x in instance if x.Class() == "Group"][0]
        deadlineChunkSize = 1
        if "deadlineChunkSize" in group_node.knobs():
            deadlineChunkSize = group_node["deadlineChunkSize"].value()

        deadlinePriority = 50
        if "deadlinePriority" in group_node.knobs():
            deadlinePriority = group_node["deadlinePriority"].value()

        families = [f for f in instance.data["families"] if "write" not in f]

        instance.data.update({
            "versionData": version_data,
            "path": path,
            "outputDir": output_dir,
            "ext": ext,
            "label": label,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": first_frame + handle_start,
            "frameEnd": last_frame - handle_end,
            "frameStartHandle": first_frame,
            "frameEndHandle": last_frame,
            "outputType": output_type,
            "family": "write",
            "families": families,
            "colorspace": node["colorspace"].value(),
            "deadlineChunkSize": deadlineChunkSize,
            "deadlinePriority": deadlinePriority
        })

        if "render" in families:
            instance.data["family"] = "render2d"
            if "render" not in families:
                instance.data["families"].insert(0, "render")

        if "prerender" in families:
            instance.data.update({
                "family": "prerender",
                "families": []
            })

        self.log.debug("families: {}".format(families))

        self.log.debug("instance.data: {}".format(instance.data))
