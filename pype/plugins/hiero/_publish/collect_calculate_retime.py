from pyblish import api
import hiero
import math


class CollectCalculateRetime(api.InstancePlugin):
    """Calculate Retiming of selected track items."""

    order = api.CollectorOrder + 0.02
    label = "Collect Calculate Retiming"
    hosts = ["hiero"]
    families = ['retime']

    def process(self, instance):
        margin_in = instance.data["retimeMarginIn"]
        margin_out = instance.data["retimeMarginOut"]
        self.log.debug("margin_in: '{0}', margin_out: '{1}'".format(margin_in, margin_out))

        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        track_item = instance.data["item"]

        # define basic clip frame range variables
        timeline_in = int(track_item.timelineIn())
        timeline_out = int(track_item.timelineOut())
        source_in = int(track_item.sourceIn())
        source_out = int(track_item.sourceOut())
        speed = track_item.playbackSpeed()
        self.log.debug("_BEFORE: \n timeline_in: `{0}`,\n timeline_out: `{1}`,\
        \n source_in: `{2}`,\n source_out: `{3}`,\n speed: `{4}`,\n handle_start: `{5}`,\n handle_end: `{6}`".format(
            timeline_in,
            timeline_out,
            source_in,
            source_out,
            speed,
            handle_start,
            handle_end
        ))

        # loop withing subtrack items
        source_in_change = 0
        source_out_change = 0
        for s_track_item in track_item.linkedItems():
            if isinstance(s_track_item, hiero.core.EffectTrackItem) \
                    and "TimeWarp" in s_track_item.node().Class():

                # adding timewarp attribute to instance
                if not instance.data.get("timeWarpNodes", None):
                    instance.data["timeWarpNodes"] = list()

                # ignore item if not enabled
                if s_track_item.isEnabled():
                    node = s_track_item.node()
                    name = node["name"].value()
                    look_up = node["lookup"].value()
                    animated = node["lookup"].isAnimated()
                    if animated:
                        look_up = [((node["lookup"].getValueAt(i)) - i)
                                   for i in range((timeline_in - handle_start), (timeline_out + handle_end) + 1)
                                   ]
                        # calculate differnce
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
                            ("source_in_change, source_out_change", source_in_change, source_out_change))

                instance.data["timeWarpNodes"].append({"Class": "TimeWarp",
                                                       "name": name,
                                                       "lookup": look_up})

        self.log.debug((source_in_change, source_out_change))
        # recalculate handles by the speed
        handle_start *= speed
        handle_end *= speed
        self.log.debug("speed: handle_start: '{0}', handle_end: '{1}'".format(handle_start, handle_end))

        source_in += int(source_in_change)
        source_out += int(source_out_change * speed)
        handle_start += (margin_in)
        handle_end += (margin_out)
        self.log.debug("margin: handle_start: '{0}', handle_end: '{1}'".format(handle_start, handle_end))

        # add all data to Instance
        instance.data["sourceIn"] = source_in
        instance.data["sourceOut"] = source_out
        instance.data["sourceInH"] = int(source_in - math.ceil(
            (handle_start * 1000) / 1000.0))
        instance.data["sourceOutH"] = int(source_out + math.ceil(
            (handle_end * 1000) / 1000.0))
        instance.data["speed"] = speed

        self.log.debug("timeWarpNodes: {}".format(instance.data["timeWarpNodes"]))
        self.log.debug("sourceIn: {}".format(instance.data["sourceIn"]))
        self.log.debug("sourceOut: {}".format(instance.data["sourceOut"]))
        self.log.debug("speed: {}".format(instance.data["speed"]))
