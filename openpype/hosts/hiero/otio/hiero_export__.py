#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Daniel Flehner Heen"
__credits__ = ["Jakub Jezek", "Daniel Flehner Heen"]

import os
import sys
import re
import hiero.core
import hiero.ui
import opentimelineio as otio


# build modul class
self = sys.modules[__name__]

self.marker_color_map = {
    "magenta": otio.schema.MarkerColor.MAGENTA,
    "red": otio.schema.MarkerColor.RED,
    "yellow": otio.schema.MarkerColor.YELLOW,
    "green": otio.schema.MarkerColor.GREEN,
    "cyan": otio.schema.MarkerColor.CYAN,
    "blue": otio.schema.MarkerColor.BLUE,
}
self.hiero_sequence = None
self.include_tags = None


def get_rate(item):
    if not hasattr(item, 'framerate'):
        item = item.sequence()

    num, den = item.framerate().toRational()
    rate = float(num) / float(den)

    if rate.is_integer():
        return rate

    return round(rate, 2)


def get_clip_ranges(trackitem):
    # Get rate from source or sequence
    if trackitem.source().mediaSource().hasVideo():
        rate_item = trackitem.source()

    else:
        rate_item = trackitem.sequence()

    source_rate = get_rate(rate_item)

    # Reversed video/audio
    if trackitem.playbackSpeed() < 0:
        start = trackitem.sourceOut()

    else:
        start = trackitem.sourceIn()

    source_start_time = otio.opentime.RationalTime(
        start,
        source_rate
    )
    source_duration = otio.opentime.RationalTime(
        trackitem.duration(),
        source_rate
    )

    source_range = otio.opentime.TimeRange(
        start_time=source_start_time,
        duration=source_duration
    )

    hiero_clip = trackitem.source()

    available_range = None
    if hiero_clip.mediaSource().isMediaPresent():
        start_time = otio.opentime.RationalTime(
            hiero_clip.mediaSource().startTime(),
            source_rate
        )
        duration = otio.opentime.RationalTime(
            hiero_clip.mediaSource().duration(),
            source_rate
        )
        available_range = otio.opentime.TimeRange(
            start_time=start_time,
            duration=duration
        )

    return source_range, available_range


def add_gap(trackitem, otio_track, prev_out):
    gap_length = trackitem.timelineIn() - prev_out
    if prev_out != 0:
        gap_length -= 1

    rate = get_rate(trackitem.sequence())
    gap = otio.opentime.TimeRange(
        duration=otio.opentime.RationalTime(
            gap_length,
            rate
        )
    )
    otio_gap = otio.schema.Gap(source_range=gap)
    otio_track.append(otio_gap)


def get_marker_color(tag):
    icon = tag.icon()
    pat = r'icons:Tag(?P<color>\w+)\.\w+'

    res = re.search(pat, icon)
    if res:
        color = res.groupdict().get('color')
        if color.lower() in self.marker_color_map:
            return self.marker_color_map[color.lower()]

    return otio.schema.MarkerColor.RED


def add_markers(hiero_item, otio_item):
    for tag in hiero_item.tags():
        if not tag.visible():
            continue

        if tag.name() == 'Copy':
            # Hiero adds this tag to a lot of clips
            continue

        frame_rate = get_rate(hiero_item)

        marked_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                tag.inTime(),
                frame_rate
            ),
            duration=otio.opentime.RationalTime(
                int(tag.metadata().dict().get('tag.length', '0')),
                frame_rate
            )
        )

        metadata = dict(
            Hiero=tag.metadata().dict()
        )
        # Store the source item for future import assignment
        metadata['Hiero']['source_type'] = hiero_item.__class__.__name__

        marker = otio.schema.Marker(
            name=tag.name(),
            color=get_marker_color(tag),
            marked_range=marked_range,
            metadata=metadata
        )

        otio_item.markers.append(marker)


def add_clip(trackitem, otio_track, itemindex):
    hiero_clip = trackitem.source()

    # Add Gap if needed
    if itemindex == 0:
        prev_item = trackitem

    else:
        prev_item = trackitem.parent().items()[itemindex - 1]

    clip_diff = trackitem.timelineIn() - prev_item.timelineOut()

    if itemindex == 0 and trackitem.timelineIn() > 0:
        add_gap(trackitem, otio_track, 0)

    elif itemindex and clip_diff != 1:
        add_gap(trackitem, otio_track, prev_item.timelineOut())

    # Create Clip
    source_range, available_range = get_clip_ranges(trackitem)

    otio_clip = otio.schema.Clip(
        name=trackitem.name(),
        source_range=source_range
    )

    media_reference = create_otio_reference(hiero_clip)

    otio_clip.media_reference = media_reference

    # Add Time Effects
    playbackspeed = trackitem.playbackSpeed()
    if playbackspeed != 1:
        if playbackspeed == 0:
            time_effect = otio.schema.FreezeFrame()

        else:
            time_effect = otio.schema.LinearTimeWarp(
                time_scalar=playbackspeed
            )
        otio_clip.effects.append(time_effect)

    # Add tags as markers
    if self.include_tags:
        add_markers(trackitem, otio_clip)
        add_markers(trackitem.source(), otio_clip)

    otio_track.append(otio_clip)

    # Add Transition if needed
    if trackitem.inTransition() or trackitem.outTransition():
        add_transition(trackitem, otio_track)

def _get_metadata(hiero_object):
    metadata = hiero_object.metadata()
    return {key: value for key, value in metadata.items()}

def create_otio_reference(hiero_clip):
    metadata = _get_metadata(hiero_clip)
    mp_clip_property = media_pool_item.GetClipProperty()
    path = mp_clip_property["File Path"]
    reformat_path = utils.get_reformated_path(path, padded=True)
    padding = utils.get_padding_from_path(path)

    if padding:
        metadata.update({
            "isSequence": True,
            "padding": padding
        })

    # get clip property regarding to type
    mp_clip_property = media_pool_item.GetClipProperty()
    fps = float(mp_clip_property["FPS"])
    if mp_clip_property["Type"] == "Video":
        frame_start = int(mp_clip_property["Start"])
        frame_duration = int(mp_clip_property["Frames"])
    else:
        audio_duration = str(mp_clip_property["Duration"])
        frame_start = 0
        frame_duration = int(utils.timecode_to_frames(
            audio_duration, float(fps)))

    otio_ex_ref_item = None

    if padding:
        # if it is file sequence try to create `ImageSequenceReference`
        # the OTIO might not be compatible so return nothing and do it old way
        try:
            dirname, filename = os.path.split(path)
            collection = clique.parse(filename, '{head}[{ranges}]{tail}')
            padding_num = len(re.findall("(\\d+)(?=-)", filename).pop())
            otio_ex_ref_item = otio.schema.ImageSequenceReference(
                target_url_base=dirname + os.sep,
                name_prefix=collection.format("{head}"),
                name_suffix=collection.format("{tail}"),
                start_frame=frame_start,
                frame_zero_padding=padding_num,
                rate=fps,
                available_range=create_otio_time_range(
                    frame_start,
                    frame_duration,
                    fps
                )
            )
        except AttributeError:
            pass

    if not otio_ex_ref_item:
        # in case old OTIO or video file create `ExternalReference`
        otio_ex_ref_item = otio.schema.ExternalReference(
            target_url=reformat_path,
            available_range=create_otio_time_range(
                frame_start,
                frame_duration,
                fps
            )
        )

    # add metadata to otio item
    add_otio_metadata(otio_ex_ref_item, hiero_clip, **metadata)

    return otio_ex_ref_item


def add_otio_metadata(otio_item, hiero_clip, **kwargs):
    mp_metadata = hiero_clip.GetMetadata()
    # add additional metadata from kwargs
    if kwargs:
        mp_metadata.update(kwargs)

    # add metadata to otio item metadata
    for key, value in mp_metadata.items():
        otio_item.metadata.update({key: value})

def add_transition(trackitem, otio_track):
    transitions = []

    if trackitem.inTransition():
        if trackitem.inTransition().alignment().name == 'kFadeIn':
            transitions.append(trackitem.inTransition())

    if trackitem.outTransition():
        transitions.append(trackitem.outTransition())

    for transition in transitions:
        alignment = transition.alignment().name

        if alignment == 'kFadeIn':
            in_offset_frames = 0
            out_offset_frames = (
                transition.timelineOut() - transition.timelineIn()
            ) + 1

        elif alignment == 'kFadeOut':
            in_offset_frames = (
                trackitem.timelineOut() - transition.timelineIn()
            ) + 1
            out_offset_frames = 0

        elif alignment == 'kDissolve':
            in_offset_frames = (
                transition.inTrackItem().timelineOut() -
                transition.timelineIn()
            )
            out_offset_frames = (
                transition.timelineOut() -
                transition.outTrackItem().timelineIn()
            )

        else:
            # kUnknown transition is ignored
            continue

        rate = trackitem.source().framerate().toFloat()
        in_time = otio.opentime.RationalTime(in_offset_frames, rate)
        out_time = otio.opentime.RationalTime(out_offset_frames, rate)

        otio_transition = otio.schema.Transition(
            name=alignment,    # Consider placing Hiero name in metadata
            transition_type=otio.schema.TransitionTypes.SMPTE_Dissolve,
            in_offset=in_time,
            out_offset=out_time
        )

        if alignment == 'kFadeIn':
            otio_track.insert(-1, otio_transition)

        else:
            otio_track.append(otio_transition)


def add_tracks():
    for track in self.hiero_sequence.items():
        if isinstance(track, hiero.core.AudioTrack):
            kind = otio.schema.TrackKind.Audio

        else:
            kind = otio.schema.TrackKind.Video

        otio_track = otio.schema.Track(name=track.name(), kind=kind)

        for itemindex, trackitem in enumerate(track):
            if isinstance(trackitem.source(), hiero.core.Clip):
                add_clip(trackitem, otio_track, itemindex)

        self.otio_timeline.tracks.append(otio_track)

    # Add tags as markers
    if self.include_tags:
        add_markers(self.hiero_sequence, self.otio_timeline.tracks)


def create_OTIO(sequence=None):
    self.hiero_sequence = sequence or hiero.ui.activeSequence()
    self.otio_timeline = otio.schema.Timeline()

    # Set global start time based on sequence
    self.otio_timeline.global_start_time = otio.opentime.RationalTime(
        self.hiero_sequence.timecodeStart(),
        self.hiero_sequence.framerate().toFloat()
    )
    self.otio_timeline.name = self.hiero_sequence.name()

    add_tracks()

    return self.otio_timeline
