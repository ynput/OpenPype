from pyblish import api
import pype


class ExtractPlates(pype.api.Extractor):
    """Extracts plates"""

    order = api.ExtractorOrder
    label = "Extract Plates"
    hosts = ["nukestudio"]
    families = ["plates"]

    def process(self, instance):
        import os
        import hiero.core
        from hiero.ui.nuke_bridge import FnNsFrameServer

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        context = instance.context
        anatomy = context.data.get("anatomy", None)
        padding = int(anatomy.templates['render']['padding'])

        name = instance.data["subset"]
        asset = instance.data["asset"]
        attrs = instance.data["attributes"]
        version = instance.data["version"]

        # staging dir creation
        self.log.debug("creating staging dir")
        self.staging_dir(instance)

        staging_dir = instance.data['stagingDir']

        nukeWriter = hiero.core.nuke.ScriptWriter()

        item = instance.data["item"]

        handles = instance.data["handles"]
        handle_start = instance.data["handleStart"] + handles
        handle_end = instance.data["handleEnd"] + handles

        # frame ranges
        timeline_frame_start = item.timelineIn() - handle_start
        timeline_frame_end = item.timelineOut() + handle_end
        # timeline_frame_duration = timeline_frame_end - timeline_frame_start + 1
        # get sequence from context
        sequence = context.data["activeSequence"]

        # Generate Nuke script
        root_node = hiero.core.nuke.RootNode(
            timeline_frame_start,
            timeline_frame_end,
            fps=sequence.framerate()
        )

        root_node.addProjectSettings(instance.context.data["colorspace"])

        nukeWriter.addNode(root_node)

        '''TrackItem.addToNukeScript(script=, firstFrame=None, additionalNodes=[], additionalNodesCallback=None, includeRetimes=False, retimeMethod=None, startHandle=None, endHandle=None, colourTransform=None, offset=0, nodeLabel=None, includeAnnotations=False, includeEffects=True, outputToSequenceFormat=False)'''
        item.addToNukeScript(
            script=nukeWriter,
            includeRetimes=attrs["includeRetimes"],
            retimeMethod=attrs["retimeMethod"],
            startHandle=handle_start,
            endHandle=handle_end,
            includeEffects=attrs["includeEffects"],
            includeAnnotations=attrs["includeAnnotations"]
        )

        write_knobs = attrs["nodes"]["write"]["attributes"]

        nukescript_file = "{asset}_{name}_v{version}.{ext}".format(
            asset=asset,
            name=name,
            version=version,
            ext="nk"
        )
        nukescript_path = os.path.join(
            staging_dir, nukescript_file
        )

        output_file = "{asset}_{name}_v{version}.%0{padding}d.{ext}".format(
            asset=asset,
            name=name,
            version=version,
            padding=padding,
            ext=write_knobs["file_type"]
        )

        output_path = os.path.join(
            staging_dir, output_file
        )

        write_name = "Write_out"
        write_node = hiero.core.nuke.WriteNode(output_path.replace("\\", "/"))
        write_node.setKnob("name", write_name)
        write_node.setKnob("file_type", write_knobs["file_type"])
        for knob, value in write_knobs.items():
            write_node.setKnob(knob, value)

        nukeWriter.addNode(write_node)

        nukeWriter.writeToDisk(nukescript_path)

        args = [
            nukescript_path,
            "{}-{}".format(timeline_frame_start, timeline_frame_end),
            write_name,
            ["main"]
        ]

        # this will do FnNsFrameServer
        FnNsFrameServer.renderFrames(*args)

        # adding representation for nukescript
        nk_representation = {
            'files': nukescript_file,
            'stagingDir': staging_dir,
            'name': "nukescript-plates",
            'ext': ".nk"
        }
        instance.data["representations"].append(nk_representation)

        # adding representation for plates
        plates_representation = {
            'files': [output_file % i for i in range(
                timeline_frame_start, (timeline_frame_end + 1), 1)],
            'stagingDir': staging_dir,
            'name': write_knobs["file_type"],
            'ext': "." + write_knobs["file_type"]
        }
        instance.data["representations"].append(plates_representation)

        self.log.debug("__ representations: {}".format(
            instance.data["representations"]))

        # adding checking file to context for ExtractPlateCheck(context) plugin
        if not context.data.get("platesCheck", None):
            context.data["platesCheck"] = os.path.join(
                staging_dir, output_file % timeline_frame_end
            )

        # this is just workaround because 'clip' family is filtered
        family = instance.data["family"]
        instance.data["family"] = instance.data["families"][-1]
        instance.data["families"].append(family)
