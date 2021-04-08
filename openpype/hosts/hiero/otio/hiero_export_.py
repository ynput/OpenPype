""" compatibility OpenTimelineIO 0.12.0 and older
"""

import os
import re
import sys
import opentimelineio as otio
from . import utils
import hiero.core
import hiero.ui

self = sys.modules[__name__]
self.track_types = {
    hiero.core.VideoTrack: otio.schema.TrackKind.Video,
    hiero.core.AudioTrack: otio.schema.TrackKind.Audio
}
self.project_fps = None
self.marker_color_map = {
    "magenta": otio.schema.MarkerColor.MAGENTA,
    "red": otio.schema.MarkerColor.RED,
    "yellow": otio.schema.MarkerColor.YELLOW,
    "green": otio.schema.MarkerColor.GREEN,
    "cyan": otio.schema.MarkerColor.CYAN,
    "blue": otio.schema.MarkerColor.BLUE,
}
self.timeline = None
self.include_tags = None


def create_otio_rational_time(frame, fps):
    return otio.opentime.RationalTime(
        float(frame),
        float(fps)
    )


def create_otio_time_range(start_frame, frame_duration, fps):
    return otio.opentime.TimeRange(
        start_time=create_otio_rational_time(start_frame, fps),
        duration=create_otio_rational_time(frame_duration, fps)
    )


def _get_metadata(item):
    if hasattr(item, 'metadata'):
        return {key: value for key, value in item.metadata().items()}
    return {}


def create_otio_reference(clip):
    metadata = _get_metadata(clip)
    media_source = clip.mediaSource()

    # get file info for path and start frame
    file_info = media_source.fileinfos().pop()
    frame_start = file_info.startFrame()
    path = file_info.filename()

    # get padding and other file infos
    padding = media_source.filenamePadding()
    file_head = media_source.filenameHead()
    is_sequence = not media_source.singleFile()
    frame_duration = media_source.duration()
    fps = utils.get_rate(clip)
    extension = os.path.splitext(path)[-1]

    if is_sequence:
        metadata.update({
            "isSequence": True,
            "padding": padding
        })

    otio_ex_ref_item = None

    if is_sequence:
        # if it is file sequence try to create `ImageSequenceReference`
        # the OTIO might not be compatible so return nothing and do it old way
        try:
            dirname = os.path.dirname(path)
            otio_ex_ref_item = otio.schema.ImageSequenceReference(
                target_url_base=dirname + os.sep,
                name_prefix=file_head,
                name_suffix=extension,
                start_frame=frame_start,
                frame_zero_padding=padding,
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
        reformat_path = utils.get_reformated_path(path, padded=False)
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
    add_otio_metadata(otio_ex_ref_item, media_source, **metadata)

    return otio_ex_ref_item


def get_marker_color(tag):
    icon = tag.icon()
    pat = r'icons:Tag(?P<color>\w+)\.\w+'

    res = re.search(pat, icon)
    if res:
        color = res.groupdict().get('color')
        if color.lower() in self.marker_color_map:
            return self.marker_color_map[color.lower()]

    return otio.schema.MarkerColor.RED


def create_otio_markers(otio_item, track_item):
    for tag in track_item.tags():
        if not tag.visible():
            continue

        if tag.name() == 'Copy':
            # Hiero adds this tag to a lot of clips
            continue

        frame_rate = utils.get_rate(track_item)

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
        metadata['Hiero']['source_type'] = track_item.__class__.__name__

        marker = otio.schema.Marker(
            name=tag.name(),
            color=get_marker_color(tag),
            marked_range=marked_range,
            metadata=metadata
        )

        otio_item.markers.append(marker)


def create_otio_clip(track_item):
    clip = track_item.source()
    source_in = track_item.sourceIn()
    duration = track_item.sourceDuration()
    fps = utils.get_rate(track_item)
    name = track_item.name()

    media_reference = create_otio_reference(clip)
    source_range = create_otio_time_range(
        int(source_in),
        int(duration),
        fps
    )

    otio_clip = otio.schema.Clip(
        name=name,
        source_range=source_range,
        media_reference=media_reference
    )
    create_otio_markers(otio_clip, track_item)

    return otio_clip


def create_otio_gap(gap_start, clip_start, tl_start_frame, fps):
    return otio.schema.Gap(
        source_range=create_otio_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            fps
        )
    )


def _create_otio_timeline():
    metadata = _get_metadata(self.timeline)
    start_time = create_otio_rational_time(
        self.timeline.timecodeStart(), self.project_fps)

    return otio.schema.Timeline(
        name=self.timeline.name(),
        global_start_time=start_time,
        metadata=metadata
    )


def _get_metadata_media_pool_item(media_pool_item):
    data = dict()
    data.update({k: v for k, v in media_pool_item.GetMetadata().items()})
    property = media_pool_item.GetClipProperty() or {}
    for name, value in property.items():
        if "Resolution" in name and "" != value:
            width, height = value.split("x")
            data.update({
                "width": int(width),
                "height": int(height)
            })
        if "PAR" in name and "" != value:
            try:
                data.update({"pixelAspect": float(value)})
            except ValueError:
                if "Square" in value:
                    data.update({"pixelAspect": float(1)})
                else:
                    data.update({"pixelAspect": float(1)})

    return data


def create_otio_track(track_type, track_name):
    return otio.schema.Track(
        name=track_name,
        kind=self.track_types[track_type]
    )


def add_otio_gap(clip_start, otio_track, item_start_frame):
    # if gap between track start and clip start
    if clip_start > otio_track.available_range().duration.value:
        # create gap and add it to track
        otio_track.append(
            create_otio_gap(
                otio_track.available_range().duration.value,
                item_start_frame,
                self.timeline.timecodeStart(),
                self.project_fps
            )
        )


def add_otio_metadata(otio_item, media_source, **kwargs):
    metadata = _get_metadata(media_source)

    # add additional metadata from kwargs
    if kwargs:
        metadata.update(kwargs)

    # add metadata to otio item metadata
    for key, value in metadata.items():
        otio_item.metadata.update({key: value})


def create_otio_timeline():

    # get current timeline
    self.timeline = hiero.ui.activeSequence()
    self.project_fps = self.timeline.framerate().toFloat()

    # convert timeline to otio
    otio_timeline = _create_otio_timeline()

    # loop all defined track types
    for track in self.hiero_sequence.items():
        # skip if track is disabled
        if not track.isEnabled():
            continue

        # convert track to otio
        otio_track = create_otio_track(
            type(track), track.name())

        for itemindex, track_item in enumerate(track):
            # skip offline track items
            if not track_item.isMediaPresent():
                continue

            # skip if track item is disabled
            if not track_item.isEnabled():
                continue

            # calculate real clip start
            clip_start = track_item.timelineIn()

            add_otio_gap(
                clip_start, otio_track, clip_start)

            # create otio clip and add it to track
            otio_clip = create_otio_clip(track_item)
            otio_track.append(otio_clip)

        # add track to otio timeline
        otio_timeline.tracks.append(otio_track)

    return otio_timeline


def write_to_file(otio_timeline, path):
    otio.adapters.write_to_file(otio_timeline, path)
