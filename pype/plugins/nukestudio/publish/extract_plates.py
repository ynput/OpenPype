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

        repr_data = dict()
        context = instance.context
        anatomy = context.data.get("anatomy", None)
        padding = int(anatomy.templates['render']['padding'])

        name = instance.data["subset"]
        asset = instance.data["asset"]
        track = instance.data["track"]
        family = instance.data["family"]
        families = instance.data["families"]
        attrs = instance.data["attributes"]
        version = instance.data["version"]

        # staging dir creation
        self.log.debug("creating staging dir")
        self.staging_dir(instance)

        staging_dir = instance.data['stagingDir']

        Nuke_writer = hiero.core.nuke.ScriptWriter()

        item = instance.data["item"]

        # get handles
        handles = int(instance.data["handles"])
        handle_start = int(instance.data["handleStart"] + handles)
        handle_end = int(instance.data["handleEnd"] + handles)

        # get timeline frames
        timeline_in = int(item.timelineIn())
        timeline_out = int(item.timelineOut())

        # frame-ranges with handles
        timeline_frame_start = timeline_in - handle_start
        timeline_frame_end = timeline_out + handle_end

        # get colorspace
        colorspace = instance.context.data["colorspace"]

        # get sequence from context, and fps
        sequence = context.data["activeSequence"]
        fps = int(str(sequence.framerate()))

        frame_start = instance.data["frameStart"] - handle_start
        frame_end = frame_start + (timeline_frame_end - timeline_frame_start)
        instance.data["startFrame"] = frame_start
        instance.data["endFrame"] = frame_end

        # test output
        self.log.debug("__ handles: {}".format(handles))
        self.log.debug("__ handle_start: {}".format(handle_start))
        self.log.debug("__ handle_end: {}".format(handle_end))
        self.log.debug("__ timeline_in: {}".format(timeline_in))
        self.log.debug("__ timeline_out: {}".format(timeline_out))
        self.log.debug("__ timeline_frame_start: {}".format(
            timeline_frame_start))
        self.log.debug("__ timeline_frame_end: {}".format(timeline_frame_end))
        self.log.debug("__ frame_start: {}".format(frame_start))
        self.log.debug("__ frame_end: {}".format(frame_end))
        self.log.debug("__ colorspace: {}".format(colorspace))
        self.log.debug("__ track: {}".format(track))
        self.log.debug("__ fps: {}".format(fps))

        # Generate Nuke script
        write_name = "Write_out"

        # root node
        root_node = hiero.core.nuke.RootNode(
            frame_start,
            frame_end,
            fps=fps
        )

        root_node.addProjectSettings(colorspace)

        # create write node and link it to root node
        Nuke_writer.addNode(root_node)
        '''TrackItem.addToNukeScript(script=, firstFrame=None, additionalNodes=[], additionalNodesCallback=None, includeRetimes=False, retimeMethod=None, startHandle=None, endHandle=None, colourTransform=None, offset=0, nodeLabel=None, includeAnnotations=False, includeEffects=True, outputToSequenceFormat=False)'''
        item.addToNukeScript(
            script=Nuke_writer,
            firstFrame=frame_start,
            includeRetimes=attrs["includeRetimes"],
            retimeMethod=attrs["retimeMethod"],
            startHandle=handle_start,
            endHandle=handle_end,
            includeEffects=attrs["includeEffects"],
            includeAnnotations=attrs["includeAnnotations"]
        )

        write_knobs = attrs["nodes"]["write"]["attributes"]

        # TODO: take template from anatomy
        nukescript_file = "{asset}_{name}_v{version}.{ext}".format(
            asset=asset,
            name=name,
            version=version,
            ext="nk"
        )
        nukescript_path = os.path.join(
            staging_dir, nukescript_file
        )

        # TODO: take template from anatomy
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

        write_node = hiero.core.nuke.WriteNode(output_path.replace("\\", "/"))
        write_node.setKnob("name", write_name)
        write_node.setKnob("file_type", write_knobs["file_type"])
        for knob, value in write_knobs.items():
            write_node.setKnob(knob, value)

        Nuke_writer.addNode(write_node)

        Nuke_writer.writeToDisk(nukescript_path)

        # test prints
        self.log.debug("__ output_file: {}".format(output_file))
        self.log.debug("__ output_path: {}".format(output_path))
        self.log.debug("__ nukescript_file: {}".format(nukescript_file))
        self.log.debug("__ nukescript_path: {}".format(nukescript_path))
        self.log.debug("__ write_knobs: {}".format(write_knobs))
        self.log.debug("__ write_name: {}".format(write_name))
        self.log.debug("__ Nuke_writer: {}".format(Nuke_writer))

        # create rendering arguments for FnNsFrameServer
        _args = [
            nukescript_path,
            "{}-{}".format(frame_start, frame_end),
            write_name,
            ["main"]
        ]

        # add to data of representation
        repr_data.update({
            "handles": handles,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "timelineIn": timeline_in,
            "timelineOut": timeline_out,
            "timelineInHandles": timeline_frame_start,
            "timelineOutHandles": timeline_frame_end,
            "compFrameIn": frame_start,
            "compFrameOut": frame_end,
            "fps": fps,
            "colorspace": write_knobs["colorspace"],
            "nukeScriptFileName": nukescript_file,
            "nukeWriteFileName": output_file,
            "nukeWriteName": write_name,
            "FnNsFrameServer_renderFrames_args": str(_args),
            "family": family,
            "families": families,
            "asset": asset,
            "subset": name,
            "track": track,
            "version": int(version)
        })

        # adding representation for nukescript
        nk_representation = {
            'files': nukescript_file,
            'stagingDir': staging_dir,
            'name': "nk",
            'ext': "nk",
            "data": repr_data
        }
        instance.data["representations"].append(nk_representation)

        # adding representation for plates
        plates_representation = {
            'files': [output_file % i for i in range(
                frame_start, (frame_end + 1), 1)],
            'stagingDir': staging_dir,
            'name': write_knobs["file_type"],
            'ext': write_knobs["file_type"],
            "data": repr_data
        }
        instance.data["representations"].append(plates_representation)

        # adding checking file to context for ExtractPlateCheck(context) plugin
        context.data["platesCheck"] = os.path.join(
            staging_dir, output_file % frame_end
        )

        if not context.data.get("frameServerRenderQueue"):
            context.data["frameServerRenderQueue"] = list()

        # add to render queue list
        context.data["frameServerRenderQueue"].append(_args)

        # test prints
        self.log.debug("__ before family: {}".format(family))
        self.log.debug("__ before families: {}".format(families))

        # this is just workaround because 'clip' family is filtered
        instance.data["family"] = families[-1]
        instance.data["families"].append(family)

        # testing families
        family = instance.data["family"]
        families = instance.data["families"]

        # test prints repr_data
        self.log.debug("__ repr_data: {}".format(repr_data))
        self.log.debug("__ nk_representation: {}".format(nk_representation))
        self.log.debug("__ plates_representation: {}".format(
            plates_representation))
        self.log.debug("__ after family: {}".format(family))
        self.log.debug("__ after families: {}".format(families))

        # this will do FnNsFrameServer
        FnNsFrameServer.renderFrames(*_args)
