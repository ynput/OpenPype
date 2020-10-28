import pyblish.api
import re


class CollectVideoTracksLuts(pyblish.api.InstancePlugin):
    """Collect video tracks effects into context."""

    order = pyblish.api.CollectorOrder + 0.1015
    label = "Collect Soft Lut Effects"
    families = ["clip"]

    def process(self, instance):

        self.log.debug(
            "Finding soft effect for subset: `{}`".format(
                instance.data.get("subset")))

        # taking active sequence
        subset = instance.data.get("subset")

        if not subset:
            return

        track_effects = instance.context.data.get("trackEffects", {})
        track_index = instance.data["trackIndex"]
        effects = instance.data["effects"]

        # creating context attribute
        self.effects = {"assignTo": subset, "effects": dict()}

        for sitem in effects:
            self.add_effect(instance, track_index, sitem)

        for t_index, sitems in track_effects.items():
            for sitem in sitems:
                if not t_index > track_index:
                    continue
                self.log.debug(">> sitem: `{}`".format(sitem))
                self.add_effect(instance, t_index, sitem)

        if self.effects["effects"]:
            instance.data["effectTrackItems"] = self.effects

        if len(instance.data.get("effectTrackItems", {}).keys()) > 0:
            instance.data["families"] += ["lut"]
            self.log.debug(
                "effects.keys: {}".format(
                    instance.data.get("effectTrackItems", {}).keys()))
            self.log.debug(
                "effects: {}".format(
                    instance.data.get("effectTrackItems", {})))

    def add_effect(self, instance, track_index, item):
        track = item.parentTrack().name()
        # node serialization
        node = item.node()
        node_serialized = self.node_serialisation(instance, node)

        # collect timelineIn/Out
        effect_t_in = int(item.timelineIn())
        effect_t_out = int(item.timelineOut())

        node_name = item.name()
        node_class = re.sub(r"\d+", "", node_name)

        self.effects["effects"].update({node_name: {
            "class": node_class,
            "timelineIn": effect_t_in,
            "timelineOut": effect_t_out,
            "subTrackIndex": item.subTrackIndex(),
            "trackIndex": track_index,
            "track": track,
            "node": node_serialized
        }})

    def node_serialisation(self, instance, node):
        node_serialized = {}
        timeline_in_h = instance.data["clipInH"]
        timeline_out_h = instance.data["clipOutH"]

        # adding ignoring knob keys
        _ignoring_keys = ['invert_mask', 'help', 'mask',
                          'xpos', 'ypos', 'layer', 'process_mask', 'channel',
                          'channels', 'maskChannelMask', 'maskChannelInput',
                          'note_font', 'note_font_size', 'unpremult',
                          'postage_stamp_frame', 'maskChannel', 'export_cc',
                          'select_cccid', 'mix', 'version', 'matrix']

        # loop trough all knobs and collect not ignored
        # and any with any value
        for knob in node.knobs().keys():
            # skip nodes in ignore keys
            if knob in _ignoring_keys:
                continue

            # get animation if node is animated
            if node[knob].isAnimated():
                # grab animation including handles
                knob_anim = [node[knob].getValueAt(i)
                             for i in range(timeline_in_h, timeline_out_h + 1)]

                node_serialized[knob] = knob_anim
            else:
                node_serialized[knob] = node[knob].value()

        return node_serialized
