from pyblish import api
import hiero
import math
from openpype.hosts.hiero.api.otio.hiero_export import create_otio_time_range

class PrecollectRetime(api.InstancePlugin):
    """Calculate Retiming of selected track items."""

    order = api.CollectorOrder - 0.578
    label = "Precollect Retime"
    hosts = ["hiero"]
    families = ['retime_']

    def process(self, instance):
        if not instance.data.get("versionData"):
            instance.data["versionData"] = {}

        # get basic variables
        otio_clip = instance.data["otioClip"]

        source_range = otio_clip.source_range
        oc_source_fps = source_range.start_time.rate
        oc_source_in = source_range.start_time.value

        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]
        frame_start = instance.data["frameStart"]

        track_item = instance.data["item"]

        # define basic clip frame range variables
        timeline_in = int(track_item.timelineIn())
        timeline_out = int(track_item.timelineOut())
        source_in = int(track_item.sourceIn())
        source_out = int(track_item.sourceOut())
        speed = track_item.playbackSpeed()

        # calculate available material before retime
        available_in = int(track_item.handleInLength() * speed)
        available_out = int(track_item.handleOutLength() * speed)

        self.log.debug((
            "_BEFORE: \n timeline_in: `{0}`,\n timeline_out: `{1}`, \n "
            "source_in: `{2}`,\n source_out: `{3}`,\n speed: `{4}`,\n "
            "handle_start: `{5}`,\n handle_end: `{6}`").format(
                timeline_in,
                timeline_out,
                source_in,
                source_out,
                speed,
                handle_start,
                handle_end
        ))

        # loop within subtrack items
        time_warp_nodes = []
        source_in_change = 0
        source_out_change = 0
        for s_track_item in track_item.linkedItems():
            if isinstance(s_track_item, hiero.core.EffectTrackItem) \
                    and "TimeWarp" in s_track_item.node().Class():

                # adding timewarp attribute to instance
                time_warp_nodes = []

                # ignore item if not enabled
                if s_track_item.isEnabled():
                    node = s_track_item.node()
                    name = node["name"].value()
                    look_up = node["lookup"].value()
                    animated = node["lookup"].isAnimated()
                    if animated:
                        look_up = [
                            ((node["lookup"].getValueAt(i)) - i)
                            for i in range(
                                (timeline_in - handle_start),
                                (timeline_out + handle_end) + 1)
                        ]
                        # calculate difference
                        diff_in = (node["lookup"].getValueAt(
                            timeline_in)) - timeline_in
                        diff_out = (node["lookup"].getValueAt(
                            timeline_out)) - timeline_out

                        # calculate source
                        source_in_change += diff_in
                        source_out_change += diff_out

                        # calculate speed
                        speed_in = (node["lookup"].getValueAt(timeline_in) / (
                            float(timeline_in) * .01)) * .01
                        speed_out = (node["lookup"].getValueAt(timeline_out) / (
                            float(timeline_out) * .01)) * .01

                        # calculate handles
                        handle_start = int(
                            math.ceil(
                                (handle_start * speed_in * 1000) / 1000.0)
                        )

                        handle_end = int(
                            math.ceil(
                                (handle_end * speed_out * 1000) / 1000.0)
                        )
                        self.log.debug(
                            ("diff_in, diff_out", diff_in, diff_out))
                        self.log.debug(
                            ("source_in_change, source_out_change",
                             source_in_change, source_out_change))

                    time_warp_nodes.append({
                        "Class": "TimeWarp",
                        "name": name,
                        "lookup": look_up
                    })

        self.log.debug(
            "timewarp source in changes: in {}, out {}".format(
                source_in_change, source_out_change))

        # recalculate handles by the speed
        handle_start *= speed
        handle_end *= speed
        self.log.debug("speed: handle_start: '{0}', handle_end: '{1}'".format(
            handle_start, handle_end))

        # recalculate source with timewarp and by the speed
        source_in += int(source_in_change)
        source_out += int(source_out_change * speed)

        source_in_h = int(source_in - math.ceil(
            (handle_start * 1000) / 1000.0))
        source_out_h = int(source_out + math.ceil(
            (handle_end * 1000) / 1000.0))

        self.log.debug(
            "retimed: source_in_h: '{0}', source_out_h: '{1}'".format(
                source_in_h, source_out_h))

        # add all data to Instance
        instance.data["handleStart"] = handle_start
        instance.data["handleEnd"] = handle_end
        instance.data["sourceIn"] = source_in
        instance.data["sourceOut"] = source_out
        instance.data["sourceInH"] = source_in_h
        instance.data["sourceOutH"] = source_out_h
        instance.data["speed"] = speed

        source_handle_start = source_in_h - source_in
        # frame_start = instance.data["frameStart"] + source_handle_start
        duration = source_out_h - source_in_h
        frame_end = int(frame_start + duration - (handle_start + handle_end))

        instance.data["versionData"].update({
            "retime": True,
            "speed": speed,
            "timewarps": time_warp_nodes,
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "handleStart": abs(source_handle_start),
            "handleEnd": source_out_h - source_out
        })
        self.log.debug("versionData: {}".format(instance.data["versionData"]))
        self.log.debug("sourceIn: {}".format(instance.data["sourceIn"]))
        self.log.debug("sourceOut: {}".format(instance.data["sourceOut"]))
        self.log.debug("speed: {}".format(instance.data["speed"]))

        # change otio clip data
        instance.data["otioClip"].source_range = create_otio_time_range(
            oc_source_in, (source_out - source_in + 1), oc_source_fps)
        self.log.debug("otioClip: {}".format(instance.data["otioClip"]))
