import pyblish.api
import hiero.core


class CollectVideoTracksEffects(pyblish.api.ContextPlugin):
    """Collect video tracks effects into context."""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Effects from video tracks"

    def process(self, context):
        # taking active sequence
        sequence = context.data['activeSequence']

        # adding ignoring knob keys
        _ignoring_keys = ['invert_mask', 'help', 'mask',
                          'xpos', 'ypos', 'layer', 'process_mask', 'channel',
                          'channels', 'maskChannelMask', 'maskChannelInput',
                          'note_font', 'note_font_size', 'unpremult',
                          'postage_stamp_frame', 'maskChannel', 'export_cc',
                          'select_cccid', 'mix', 'version']

        # creating context attribute
        context.data["effectTrackItems"] = effects = dict()

        # loop trough all videotracks
        for track_index, video_track in enumerate(sequence.videoTracks()):
            # loop trough all available subtracks
            for subtrack_item in video_track.subTrackItems():
                # ignore anything not EffectTrackItem
                if isinstance(subtrack_item[0], hiero.core.EffectTrackItem):
                    et_item = subtrack_item[0]
                    # ignore item if not enabled
                    if et_item.isEnabled():
                        node = et_item.node()
                        node_serialized = {}
                        # loop trough all knobs and collect not ignored
                        # and any with any value
                        for knob in node.knobs().keys():
                            if (knob not in _ignoring_keys) and node[knob].value():
                                node_serialized[knob] = node[knob].value()
                        # add it to the context attribute
                        effects.update({et_item.name(): {
                            "timelineIn": int(et_item.timelineIn()),
                            "timelineOut": int(et_item.timelineOut()),
                            "subTrackIndex": et_item.subTrackIndex(),
                            "trackIndex": track_index,
                            "node": node_serialized
                        }})

        self.log.debug("effects: {}".format(effects))
