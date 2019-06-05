from pyblish import api
import pype


class CollectPlates(api.InstancePlugin):
    """Collect plates"""

    order = api.CollectorOrder + 0.49
    label = "Extract Plates"
    hosts = ["nukestudio"]
    families = ["plates"]

    def process(self, instance):
        import os
        import hiero.core
        # from hiero.ui.nuke_bridge import FnNsFrameServer

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        version_data = dict()
        context = instance.context
        anatomy = context.data.get("anatomy", None)
        padding = int(anatomy.templates['render']['padding'])

        name = instance.data["subset"]
        asset = instance.data["asset"]
        track = instance.data["track"]
        family = instance.data["family"]
        families = instance.data["families"]
        version = instance.data["version"]
        source_path = instance.data["sourcePath"]
        source_file = os.path.basename(source_path)

        # staging dir creation
        staging_dir = instance.data['stagingDir'] = os.path.dirname(
            source_path)


        item = instance.data["item"]

        # get handles
        handles = int(instance.data["handles"])
        handle_start = int(instance.data["handleStart"])
        handle_end = int(instance.data["handleEnd"])

        # get source frames
        source_in = int(instance.data["sourceIn"])
        source_out = int(instance.data["sourceOut"])

        # get source frames
        source_in_h = int(instance.data["sourceInH"])
        source_out_h = int(instance.data["sourceOutH"])

        # get timeline frames
        timeline_in = int(instance.data["timelineIn"])
        timeline_out = int(instance.data["timelineOut"])

        # frame-ranges with handles
        timeline_frame_start = int(instance.data["timelineInHandles"])
        timeline_frame_end = int(instance.data["timelineOutHandles"])


        # get colorspace
        colorspace = item.sourceMediaColourTransform()

        # get sequence from context, and fps
        fps = int(instance.data["fps"])

        # test output
        self.log.debug("__ handles: {}".format(handles))
        self.log.debug("__ handle_start: {}".format(handle_start))
        self.log.debug("__ handle_end: {}".format(handle_end))
        self.log.debug("__ source_in: {}".format(source_in))
        self.log.debug("__ source_out: {}".format(source_out))
        self.log.debug("__ source_in_h: {}".format(source_in_h))
        self.log.debug("__ source_out_h: {}".format(source_out_h))
        self.log.debug("__ timeline_in: {}".format(timeline_in))
        self.log.debug("__ timeline_out: {}".format(timeline_out))
        self.log.debug("__ timeline_frame_start: {}".format(
            timeline_frame_start))
        self.log.debug("__ timeline_frame_end: {}".format(timeline_frame_end))
        self.log.debug("__ colorspace: {}".format(colorspace))
        self.log.debug("__ track: {}".format(track))
        self.log.debug("__ fps: {}".format(fps))
        self.log.debug("__ source_file: {}".format(source_file))
        self.log.debug("__ staging_dir: {}".format(staging_dir))


        # add to data of representation
        version_data.update({
            "handles": handles,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "sourceIn": source_in,
            "sourceOut": source_out,
            "timelineIn": timeline_in,
            "timelineOut": timeline_out,
            "timelineInHandles": timeline_frame_start,
            "timelineOutHandles": timeline_frame_end,
            "fps": fps,
            "colorspace": colorspace,
            "family": family,
            "families": families,
            "asset": asset,
            "subset": name,
            "track": track,
            "version": int(version)
        })
        instance.data["versionData"] = version_data

        try:
            head, padding, ext = source_file.split('.')
            source_first_frame = int(padding)
            padding = len(padding)
            file = "{head}.%0{padding}d.{ext}".format(
                head=head,
                padding=padding,
                ext=ext
            )
            files = [file % i for i in range(
                (source_first_frame + source_in_h),
                ((source_first_frame + source_out_h) + 1), 1)]
        except Exception as e:
            self.log.debug("Exception in file: {}".format(e))
            head, ext = source_file.split('.')
            files = source_file



        # adding representation for plates
        plates_representation = {
            'files': files,
            'stagingDir': staging_dir,
            'name': ext,
            'ext': ext,
        }
        instance.data["representations"].append(plates_representation)


        # this is just workaround because 'clip' family is filtered
        instance.data["family"] = families[-1]
        instance.data["families"].append(family)

        # testing families
        family = instance.data["family"]
        families = instance.data["families"]

        # test prints version_data
        self.log.debug("__ version_data: {}".format(version_data))
        self.log.debug("__ plates_representation: {}".format(
            plates_representation))
        self.log.debug("__ after family: {}".format(family))
        self.log.debug("__ after families: {}".format(families))

        # # this will do FnNsFrameServer
        # FnNsFrameServer.renderFrames(*_args)
