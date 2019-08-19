import pyblish.api
import hiero.core


class CollectVideoTracksLuts(pyblish.api.InstancePlugin):
    """Collect video tracks effects into context."""

    order = pyblish.api.CollectorOrder + 0.1015
    label = "Collect Soft Lut Effects"
    families = ["clip"]

    def process(self, instance):

        self.log.debug("Finding soft effect for subset: `{}`".format(instance.data.get("subset")))

        # taking active sequence
        subset = instance.data["subset"]
        sequence = instance.context.data['activeSequence']
        effects_on_tracks = instance.context.data.get("subTrackUsedTracks")
        sub_track_items = instance.context.data.get("subTrackItems")
        track = instance.data["track"]

        timeline_in_h = instance.data["clipInH"]
        timeline_out_h = instance.data["clipOutH"]
        timeline_in = instance.data["clipIn"]
        timeline_out = instance.data["clipOut"]

        # adding ignoring knob keys
        _ignoring_keys = ['invert_mask', 'help', 'mask',
                          'xpos', 'ypos', 'layer', 'process_mask', 'channel',
                          'channels', 'maskChannelMask', 'maskChannelInput',
                          'note_font', 'note_font_size', 'unpremult',
                          'postage_stamp_frame', 'maskChannel', 'export_cc',
                          'select_cccid', 'mix', 'version']

        # creating context attribute
        effects = {"assignTo": subset, "effects": dict()}

        for subtrack_item in sub_track_items:
            sub_track = subtrack_item.parentTrack().name()

            # ignore anything not EffectTrackItem
            if not isinstance(subtrack_item, hiero.core.EffectTrackItem):
                continue
            et_item = subtrack_item

            # ignore item if not enabled
            if not et_item.isEnabled():
                continue

            node = et_item.node()
            node_serialized = {}
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

            # pick track index from subTrackItem
            pick_sub_track = [indx for indx, vt
                              in enumerate(sequence.videoTracks())
                              if vt.name() in sub_track]
            # pick track index from trackItem
            pick_track = [indx for indx, vt in enumerate(sequence.videoTracks())
                          if vt.name() in track]
            # collect timelineIn/Out
            effect_t_in = int(et_item.timelineIn())
            effect_t_out = int(et_item.timelineOut())

            # controle if parent track has video trackItems
            items_check = et_item.parent().items()

            # filter out all track items under any track with effects
            # also filter out track item bellow
            if (pick_track[0] in effects_on_tracks) and (pick_sub_track[0] >= pick_track[0]):
                if (effect_t_in == timeline_in) and (effect_t_out == timeline_out):
                    effects["effects"].update({et_item.name(): {
                        "timelineIn": effect_t_in,
                        "timelineOut": effect_t_out,
                        "subTrackIndex": et_item.subTrackIndex(),
                        "trackIndex": pick_track[0],
                        "node": node_serialized
                    }})
                # for subTrackItem on track without any trackItems
                elif len(items_check) == 0:
                    effects["effects"].update({et_item.name(): {
                        "timelineIn": effect_t_in,
                        "timelineOut": effect_t_out,
                        "subTrackIndex": et_item.subTrackIndex(),
                        "trackIndex": pick_track[0],
                        "node": node_serialized
                    }})

        instance.data["effectTrackItems"] = effects
        if len(instance.data.get("effectTrackItems", {}).keys()) > 0:
            instance.data["families"] += ["lut"]
            self.log.debug("effects.keys: {}".format(instance.data.get("effectTrackItems", {}).keys()))
            self.log.debug("effects: {}".format(instance.data.get("effectTrackItems", {})))
