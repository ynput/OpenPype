from pyblish import api
from pyblish_bumpybox import inventory


class ExtractReview(api.InstancePlugin):
    """Extracts movie for review"""

    order = inventory.get_order(__file__, "ExtractReview")
    label = "NukeStudio Review"
    optional = True
    hosts = ["nukestudio"]
    families = ["review"]

    def process(self, instance):
        import os
        import time

        import hiero.core
        from hiero.exporters.FnExportUtil import writeSequenceAudioWithHandles

        nukeWriter = hiero.core.nuke.ScriptWriter()

        item = instance.data["item"]

        handles = instance.data["handles"]

        sequence = item.parent().parent()

        output_path = os.path.abspath(
            os.path.join(
                instance.context.data["currentFile"], "..", "workspace"
            )
        )

        # Generate audio
        audio_file = os.path.join(
            output_path, "{0}.wav".format(instance.data["name"])
        )

        writeSequenceAudioWithHandles(
            audio_file,
            sequence,
            item.timelineIn(),
            item.timelineOut(),
            handles,
            handles
        )

        # Generate Nuke script
        root_node = hiero.core.nuke.RootNode(
            item.timelineIn() - handles,
            item.timelineOut() + handles,
            fps=sequence.framerate()
        )

        root_node.addProjectSettings(instance.context.data["colorspace"])

        nukeWriter.addNode(root_node)

        item.addToNukeScript(
            script=nukeWriter,
            includeRetimes=True,
            retimeMethod="Frame",
            startHandle=handles,
            endHandle=handles
        )

        movie_path = os.path.join(
            output_path, "{0}.mov".format(instance.data["name"])
        )
        write_node = hiero.core.nuke.WriteNode(movie_path.replace("\\", "/"))
        self.log.info("__ write_node: {0}".format(write_node))
        write_node.setKnob("file_type", "mov")
        write_node.setKnob("colorspace", instance.context.data["colorspace"]["lutSettingFloat"])
        write_node.setKnob("meta_codec", "ap4h")
        write_node.setKnob("mov64_codec", "ap4h")
        write_node.setKnob("mov64_bitrate", 400000)
        write_node.setKnob("mov64_bitrate_tolerance", 40000000)
        write_node.setKnob("mov64_quality_min", 2)
        write_node.setKnob("mov64_quality_max", 31)
        write_node.setKnob("mov64_gop_size", 12)
        write_node.setKnob("mov64_b_frames", 0)
        write_node.setKnob("raw", True )
        write_node.setKnob("mov64_audiofile", audio_file.replace("\\", "/"))
        write_node.setKnob("mov32_fps", sequence.framerate())
        nukeWriter.addNode(write_node)

        nukescript_path = movie_path.replace(".mov", ".nk")
        nukeWriter.writeToDisk(nukescript_path)

        process = hiero.core.nuke.executeNukeScript(
            nukescript_path,
            open(movie_path.replace(".mov", ".log"), "w")
        )

        while process.poll() is None:
            time.sleep(0.5)

        assert os.path.exists(movie_path), "Creating review failed."

        instance.data["output_path"] = movie_path
        instance.data["review_family"] = "mov"
