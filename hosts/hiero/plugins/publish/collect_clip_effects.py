import re
import pyblish.api


class CollectClipEffects(pyblish.api.InstancePlugin):
    """Collect soft effects instances."""

    order = pyblish.api.CollectorOrder - 0.078
    label = "Collect Clip Effects Instances"
    families = ["clip"]

    def process(self, instance):
        family = "effect"
        effects = {}
        review = instance.data.get("review")
        review_track_index = instance.context.data.get("reviewTrackIndex")
        item = instance.data["item"]

        # frame range
        self.handle_start = instance.data["handleStart"]
        self.handle_end = instance.data["handleEnd"]
        self.clip_in = int(item.timelineIn())
        self.clip_out = int(item.timelineOut())
        self.clip_in_h = self.clip_in - self.handle_start
        self.clip_out_h = self.clip_out + self.handle_end

        track_item = instance.data["item"]
        track = track_item.parent()
        track_index = track.trackIndex()
        tracks_effect_items = instance.context.data.get("tracksEffectItems")
        clip_effect_items = instance.data.get("clipEffectItems")

        # add clips effects to track's:
        if clip_effect_items:
            tracks_effect_items[track_index] = clip_effect_items

        # process all effects and divide them to instance
        for _track_index, sub_track_items in tracks_effect_items.items():
            # skip if track index is the same as review track index
            if review and review_track_index == _track_index:
                continue
            for sitem in sub_track_items:
                effect = None
                # make sure this subtrack item is relative of track item
                if ((track_item not in sitem.linkedItems())
                        and (len(sitem.linkedItems()) > 0)):
                    continue

                if not (track_index <= _track_index):
                    continue

                effect = self.add_effect(_track_index, sitem)

                if effect:
                    effects.update(effect)

        # skip any without effects
        if not effects:
            return

        subset = instance.data.get("subset")
        effects.update({"assignTo": subset})

        subset_split = re.findall(r'[A-Z][^A-Z]*', subset)

        if len(subset_split) > 0:
            root_name = subset.replace(subset_split[0], "")
            subset_split.insert(0, root_name.capitalize())

        subset_split.insert(0, "effect")

        name = "".join(subset_split)

        # create new instance and inherit data
        data = {}
        for key, value in instance.data.items():
            if "clipEffectItems" in key:
                continue
            data[key] = value

        # change names
        data["subset"] = name
        data["family"] = family
        data["families"] = [family]
        data["name"] = data["subset"] + "_" + data["asset"]
        data["label"] = "{} - {}".format(
            data['asset'], data["subset"]
        )
        data["effects"] = effects

        # create new instance
        _instance = instance.context.create_instance(**data)
        self.log.info("Created instance `{}`".format(_instance))
        self.log.debug("instance.data `{}`".format(_instance.data))

    def test_overlap(self, effect_t_in, effect_t_out):
        covering_exp = bool(
            (effect_t_in <= self.clip_in)
            and (effect_t_out >= self.clip_out)
        )
        overlaying_right_exp = bool(
            (effect_t_in < self.clip_out)
            and (effect_t_out >= self.clip_out)
        )
        overlaying_left_exp = bool(
            (effect_t_out > self.clip_in)
            and (effect_t_in <= self.clip_in)
        )

        return any((
            covering_exp,
            overlaying_right_exp,
            overlaying_left_exp
        ))

    def add_effect(self, track_index, sitem):
        track = sitem.parentTrack().name()
        # node serialization
        node = sitem.node()
        node_serialized = self.node_serialisation(node)
        node_name = sitem.name()

        if "_" in node_name:
            node_class = re.sub(r"(?:_)[_0-9]+", "", node_name)  # more numbers
        else:
            node_class = re.sub(r"\d+", "", node_name)  # one number

        # collect timelineIn/Out
        effect_t_in = int(sitem.timelineIn())
        effect_t_out = int(sitem.timelineOut())

        if not self.test_overlap(effect_t_in, effect_t_out):
            return

        self.log.debug("node_name: `{}`".format(node_name))
        self.log.debug("node_class: `{}`".format(node_class))

        return {node_name: {
            "class": node_class,
            "timelineIn": effect_t_in,
            "timelineOut": effect_t_out,
            "subTrackIndex": sitem.subTrackIndex(),
            "trackIndex": track_index,
            "track": track,
            "node": node_serialized
        }}

    def node_serialisation(self, node):
        node_serialized = {}

        # adding ignoring knob keys
        _ignoring_keys = ['invert_mask', 'help', 'mask',
                          'xpos', 'ypos', 'layer', 'process_mask', 'channel',
                          'channels', 'maskChannelMask', 'maskChannelInput',
                          'note_font', 'note_font_size', 'unpremult',
                          'postage_stamp_frame', 'maskChannel', 'export_cc',
                          'select_cccid', 'mix', 'version', 'matrix']

        # loop through all knobs and collect not ignored
        # and any with any value
        for knob in node.knobs().keys():
            # skip nodes in ignore keys
            if knob in _ignoring_keys:
                continue

            # get animation if node is animated
            if node[knob].isAnimated():
                # grab animation including handles
                knob_anim = [node[knob].getValueAt(i)
                             for i in range(
                             self.clip_in_h, self.clip_out_h + 1)]

                node_serialized[knob] = knob_anim
            else:
                node_serialized[knob] = node[knob].value()

        return node_serialized
