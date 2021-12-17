""" compatibility OpenTimelineIO 0.12.0 and newer
"""

import os
import re
import sys
import ast
import logging
import opentimelineio as otio
from . import utils

import flame
from pprint import pformat

reload(utils)

log = logging.getLogger(__name__)

self = sys.modules[__name__]
self.track_types = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}
self.fps = None
self.seq_frame_start = None
self.project = None
self.clips = None
self.marker_color_map = {
    "magenta": otio.schema.MarkerColor.MAGENTA,
    "red": otio.schema.MarkerColor.RED,
    "yellow": otio.schema.MarkerColor.YELLOW,
    "green": otio.schema.MarkerColor.GREEN,
    "cyan": otio.schema.MarkerColor.CYAN,
    "blue": otio.schema.MarkerColor.BLUE,
}
self.include_tags = True


def flatten(_list):
    for item in _list:
        if isinstance(item, (list, tuple)):
            for sub_item in flatten(item):
                yield sub_item
        else:
            yield item


def get_current_flame_project():
    project = flame.project.current_project
    return project


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
        if not item.metadata:
            return {}
        return {key: value for key, value in dict(item.metadata)}
    return {}


def create_time_effects(otio_clip, track_item):
    # get all subtrack items
    subTrackItems = flatten(track_item.parent().subTrackItems())
    speed = track_item.playbackSpeed()

    otio_effect = None
    # retime on track item
    if speed != 1.:
        # make effect
        otio_effect = otio.schema.LinearTimeWarp()
        otio_effect.name = "Speed"
        otio_effect.time_scalar = speed
        otio_effect.metadata = {}

    # freeze frame effect
    if speed == 0.:
        otio_effect = otio.schema.FreezeFrame()
        otio_effect.name = "FreezeFrame"
        otio_effect.metadata = {}

    if otio_effect:
        # add otio effect to clip effects
        otio_clip.effects.append(otio_effect)

    # loop trought and get all Timewarps
    for effect in subTrackItems:
        if ((track_item not in effect.linkedItems())
                and (len(effect.linkedItems()) > 0)):
            continue
        # avoid all effect which are not TimeWarp and disabled
        if "TimeWarp" not in effect.name():
            continue

        if not effect.isEnabled():
            continue

        node = effect.node()
        name = node["name"].value()

        # solve effect class as effect name
        _name = effect.name()
        if "_" in _name:
            effect_name = re.sub(r"(?:_)[_0-9]+", "", _name)  # more numbers
        else:
            effect_name = re.sub(r"\d+", "", _name)  # one number

        metadata = {}
        # add knob to metadata
        for knob in ["lookup", "length"]:
            value = node[knob].value()
            animated = node[knob].isAnimated()
            if animated:
                value = [
                    ((node[knob].getValueAt(i)) - i)
                    for i in range(
                        track_item.timelineIn(), track_item.timelineOut() + 1)
                ]

            metadata[knob] = value

        # make effect
        otio_effect = otio.schema.TimeEffect()
        otio_effect.name = name
        otio_effect.effect_name = effect_name
        otio_effect.metadata = metadata

        # add otio effect to clip effects
        otio_clip.effects.append(otio_effect)


def get_marker_color(tag):
    icon = tag.icon()
    pat = r'icons:Tag(?P<color>\w+)\.\w+'

    res = re.search(pat, icon)
    if res:
        color = res.groupdict().get('color')
        if color.lower() in self.marker_color_map:
            return self.marker_color_map[color.lower()]

    return otio.schema.MarkerColor.RED


def create_otio_markers(otio_item, item):
    for tag in item.tags():
        if not tag.visible():
            continue

        if tag.name() == 'Copy':
            # Hiero adds this tag to a lot of clips
            continue

        frame_rate = utils.get_rate(item) or self.fps

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
        # add tag metadata but remove "tag." string
        metadata = {}

        for key, value in tag.metadata().dict().items():
            _key = key.replace("tag.", "")

            try:
                # capture exceptions which are related to strings only
                _value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                _value = value

            metadata.update({_key: _value})

        # Store the source item for future import assignment
        metadata['hiero_source_type'] = item.__class__.__name__

        marker = otio.schema.Marker(
            name=tag.name(),
            color=get_marker_color(tag),
            marked_range=marked_range,
            metadata=metadata
        )

        otio_item.markers.append(marker)


def create_otio_reference(clip_data):
    metadata = _get_metadata(clip_data)

    # get file info for path and start frame
    frame_start = 0
    fps = self.fps

    path = clip_data["fpath"]

    reel_clip = None
    match_reel_clip = [
        clip for clip in self.clips
        if clip["fpath"] == path
    ]
    if match_reel_clip:
        reel_clip = match_reel_clip.pop()
        fps = reel_clip["fps"]

    file_name = os.path.basename(path)
    file_head, extension = os.path.splitext(file_name)

    # get padding and other file infos
    log.debug("_ path: {}".format(path))

    is_sequence = padding = utils.get_frame_from_path(path)
    if is_sequence:
        number = utils.get_frame_from_path(path)
        file_head = file_name.split(number)[:-1]
        frame_start = int(number)

    frame_duration = clip_data["source_duration"]

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
    add_otio_metadata(otio_ex_ref_item, clip_data, **metadata)

    return otio_ex_ref_item


def create_otio_clip(clip_data):

    media_reference = create_otio_reference(clip_data)
    # calculate source in
    first_frame = utils.get_frame_from_path(clip_data["fpath"]) or 0
    source_in = int(clip_data["source_in"]) - int(first_frame)
    source_range = create_otio_time_range(
        source_in,
        clip_data["record_duration"],
        self.fps
    )

    otio_clip = otio.schema.Clip(
        name=clip_data["segment_name"],
        source_range=source_range,
        media_reference=media_reference
    )

    # # Add tags as markers
    # if self.include_tags:
    #     create_otio_markers(otio_clip, track_item)
    #     create_otio_markers(otio_clip, track_item.source())

    # # only if video
    # if not clip.mediaSource().hasAudio():
    #     # Add effects to clips
    #     create_time_effects(otio_clip, track_item)

    return otio_clip


def create_otio_gap(gap_start, clip_start, tl_start_frame, fps):
    return otio.schema.Gap(
        source_range=create_otio_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            fps
        )
    )

def get_clips_in_reels(project):
    output_clips = []
    project_desktop = project.current_workspace.desktop

    for reel_group in project_desktop.reel_groups:
        for reel in reel_group.reels:
            for clip in reel.clips:
                clip_data = {
                    "PyClip": clip,
                    "fps": float(str(clip.frame_rate)[:-4])
                }

                attrs = [
                    "name", "width", "height",
                    "ratio", "sample_rate", "bit_depth"
                ]

                for attr in attrs:
                    val = getattr(clip, attr)
                    clip_data[attr] = val

                version = clip.versions[-1]
                track = version.tracks[-1]
                for segment in track.segments:
                    segment_data = get_segment_attributes(segment)
                    clip_data.update(segment_data)

                output_clips.append(clip_data)

    return output_clips

def _create_otio_timeline(sequence):

    metadata = _get_metadata(sequence)

    metadata.update({
        "openpype.timeline.width": int(sequence.width),
        "openpype.timeline.height": int(sequence.height),
        "openpype.timeline.pixelAspect": 1,  # noqa
        # "openpype.project.useOCIOEnvironmentOverride": project.useOCIOEnvironmentOverride(),  # noqa
        # "openpype.project.lutSetting16Bit": project.lutSetting16Bit(),
        # "openpype.project.lutSetting8Bit": project.lutSetting8Bit(),
        # "openpype.project.lutSettingFloat": project.lutSettingFloat(),
        # "openpype.project.lutSettingLog": project.lutSettingLog(),
        # "openpype.project.lutSettingViewer": project.lutSettingViewer(),
        # "openpype.project.lutSettingWorkingSpace": project.lutSettingWorkingSpace(),  # noqa
        # "openpype.project.lutUseOCIOForExport": project.lutUseOCIOForExport(),
        # "openpype.project.ocioConfigName": project.ocioConfigName(),
        # "openpype.project.ocioConfigPath": project.ocioConfigPath()
    })

    rt_start_time = create_otio_rational_time(
        self.seq_frame_start, self.fps)

    return otio.schema.Timeline(
        name=str(sequence.name)[1:-1],
        global_start_time=rt_start_time,
        metadata=metadata
    )


def create_otio_track(track_type, track_name):
    return otio.schema.Track(
        name=track_name,
        kind=self.track_types[track_type]
    )


def add_otio_gap(clip_data, otio_track, prev_out):
    gap_length = clip_data["record_in"] - prev_out
    if prev_out != 0:
        gap_length -= 1

    gap = otio.opentime.TimeRange(
        duration=otio.opentime.RationalTime(
            gap_length,
            self.fps
        )
    )
    otio_gap = otio.schema.Gap(source_range=gap)
    otio_track.append(otio_gap)


def add_otio_metadata(otio_item, item, **kwargs):
    metadata = _get_metadata(item)

    # add additional metadata from kwargs
    if kwargs:
        metadata.update(kwargs)

    # add metadata to otio item metadata
    for key, value in metadata.items():
        otio_item.metadata.update({key: value})

def get_markers(item, segment=True):
    output_markers = []

    if segment:
        segment_tl_in = item.record_in.relative_frame

    for marker in item.markers:
        log.debug(marker)
        start_frame = marker.location.get_value().relative_frame

        if segment:
            start_frame = (start_frame - segment_tl_in) + 1

        marker_data = {
            "name": marker.name.get_value(),
            "duration": marker.duration.get_value().relative_frame,
            "comment": marker.comment.get_value(),
            "start_frame": start_frame,
            "colour": marker.colour.get_value()
        }

        output_markers.append(marker_data)

    return output_markers

def get_shot_tokens_values(clip, tokens):
    old_value = None
    output = {}

    shot_name = getattr(clip, "shot_name")

    if not shot_name:
        return output

    old_value = shot_name.get_value()

    for token in tokens:
        shot_name.set_value(token)
        _key = re.sub("[ <>]", "", token)
        try:
            output[_key] = int(shot_name.get_value())
        except:
            output[_key] = shot_name.get_value()

    shot_name.set_value(old_value)

    return output

def get_segment_attributes(segment):
    # log.debug(dir(segment))

    markers = get_markers(segment)

    if str(segment.name)[1:-1] == "":
        return None

    # Add timeline segment to tree
    clip_data = {
        "segment_name": segment.name.get_value(),
        "segment_comment": segment.comment.get_value(),
        "tape_name": segment.tape_name,
        "source_name": segment.source_name,
        "fpath": segment.file_path,
        "PySegment": segment
    }

    # add all available shot tokens
    shot_tokens = get_shot_tokens_values(segment, [
        "<colour space>", "<width>", "<height>", "<depth>",
    ])
    clip_data.update(shot_tokens)

    # populate shot source metadata
    segment_attrs = [
        "record_duration", "record_in", "record_out",
        "source_duration", "source_in", "source_out"
    ]
    segment_attrs_data = {}
    for attr in segment_attrs:
        if not hasattr(segment, attr):
            continue
        _value = getattr(segment, attr)
        segment_attrs_data[attr] = str(_value).replace("+", ":")

        if attr in ["record_in", "record_out"]:
            clip_data[attr] = _value.relative_frame
        else:
            clip_data[attr] = _value.frame

    clip_data["segment_timecodes"] = segment_attrs_data

    return clip_data

def create_otio_timeline(sequence):
    log.info(dir(sequence))
    log.info(sequence.attributes)

    self.project = get_current_flame_project()
    self.clips = get_clips_in_reels(self.project)

    log.debug(pformat(
        self.clips
    ))

    # get current timeline
    self.fps = float(str(sequence.frame_rate)[:-4])
    self.seq_frame_start = utils.timecode_to_frames(
            str(sequence.start_time).replace("+", ":"),
            self.fps)

    # convert timeline to otio
    otio_timeline = _create_otio_timeline(sequence)

    # create otio tracks and clips
    for ver in sequence.versions:
        for track in ver.tracks:
            if len(track.segments) == 0 and track.hidden:
                return None

            # convert track to otio
            otio_track = create_otio_track(
                "video", str(track.name)[1:-1])

            all_segments = []
            for segment in track.segments:
                clip_data = get_segment_attributes(segment)
                if not clip_data:
                    continue
                all_segments.append(clip_data)

            segments_ordered = {
                itemindex: clip_data
                for itemindex, clip_data in enumerate(
                    all_segments)
            }
            log.debug("_ segments_ordered: {}".format(
                pformat(segments_ordered)
            ))
            if not segments_ordered:
                continue

            for itemindex, segment_data in segments_ordered.items():
                log.debug("_ itemindex: {}".format(itemindex))

                # Add Gap if needed
                if itemindex == 0:
                    # if it is first track item at track then add
                    # it to previouse item
                    prev_item = segment_data

                else:
                    # get previouse item
                    prev_item = segments_ordered[itemindex - 1]

                log.debug("_ segment_data: {}".format(segment_data))

                # calculate clip frame range difference from each other
                clip_diff = segment_data["record_in"] - prev_item["record_out"]

                # add gap if first track item is not starting
                # at first timeline frame
                if itemindex == 0 and segment_data["record_in"] > 0:
                    add_otio_gap(segment_data, otio_track, 0)

                # or add gap if following track items are having
                # frame range differences from each other
                elif itemindex and clip_diff != 1:
                    add_otio_gap(
                        segment_data, otio_track, prev_item["record_out"])

                # create otio clip and add it to track
                otio_clip = create_otio_clip(segment_data)
                otio_track.append(otio_clip)

                log.debug("_ otio_clip: {}".format(otio_clip))

                # create otio marker
                # create otio metadata

            # add track to otio timeline
            otio_timeline.tracks.append(otio_track)

    return otio_timeline


def write_to_file(otio_timeline, path):
    otio.adapters.write_to_file(otio_timeline, path)
