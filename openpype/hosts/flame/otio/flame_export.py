""" compatibility OpenTimelineIO 0.12.0 and newer
"""

import os
import re
import json
import logging
import opentimelineio as otio
from . import utils

import flame
from pprint import pformat

log = logging.getLogger(__name__)


TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio
}
MARKERS_COLOR_MAP = {
    (1.0, 0.0, 0.0): otio.schema.MarkerColor.RED,
    (1.0, 0.5, 0.0): otio.schema.MarkerColor.ORANGE,
    (1.0, 1.0, 0.0): otio.schema.MarkerColor.YELLOW,
    (1.0, 0.5, 1.0): otio.schema.MarkerColor.PINK,
    (1.0, 1.0, 1.0): otio.schema.MarkerColor.WHITE,
    (0.0, 1.0, 0.0): otio.schema.MarkerColor.GREEN,
    (0.0, 1.0, 1.0): otio.schema.MarkerColor.CYAN,
    (0.0, 0.0, 1.0): otio.schema.MarkerColor.BLUE,
    (0.5, 0.0, 0.5): otio.schema.MarkerColor.PURPLE,
    (0.5, 0.0, 1.0): otio.schema.MarkerColor.MAGENTA,
    (0.0, 0.0, 0.0): otio.schema.MarkerColor.BLACK
}
MARKERS_INCLUDE = True


class CTX:
    _fps = None
    _tl_start_frame = None
    project = None
    clips = None

    @classmethod
    def set_fps(cls, new_fps):
        if not isinstance(new_fps, float):
            raise TypeError("Invalid fps type {}".format(type(new_fps)))
        if cls._fps != new_fps:
            cls._fps = new_fps

    @classmethod
    def get_fps(cls):
        return cls._fps

    @classmethod
    def set_tl_start_frame(cls, number):
        if not isinstance(number, int):
            raise TypeError("Invalid timeline start frame type {}".format(
                type(number)))
        if cls._tl_start_frame != number:
            cls._tl_start_frame = number

    @classmethod
    def get_tl_start_frame(cls):
        return cls._tl_start_frame


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
        return dict(dict(item.metadata)) if item.metadata else {}
    return {}


def create_time_effects(otio_clip, speed):
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


def _get_marker_color(flame_colour):
    # clamp colors to closes half numbers
    _flame_colour = [
        (lambda x: round(x * 2) / 2)(c)
        for c in flame_colour]

    for color, otio_color_type in MARKERS_COLOR_MAP.items():
        if _flame_colour == list(color):
            return otio_color_type

    return otio.schema.MarkerColor.RED


def _get_flame_markers(item):
    output_markers = []

    time_in = item.record_in.relative_frame

    for marker in item.markers:
        log.debug(marker)
        start_frame = marker.location.get_value().relative_frame

        start_frame = (start_frame - time_in) + 1

        marker_data = {
            "name": marker.name.get_value(),
            "duration": marker.duration.get_value().relative_frame,
            "comment": marker.comment.get_value(),
            "start_frame": start_frame,
            "colour": marker.colour.get_value()
        }

        output_markers.append(marker_data)

    return output_markers


def create_otio_markers(otio_item, item):
    markers = _get_flame_markers(item)
    for marker in markers:
        frame_rate = CTX.get_fps()

        marked_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                marker["start_frame"],
                frame_rate
            ),
            duration=otio.opentime.RationalTime(
                marker["duration"],
                frame_rate
            )
        )

        # testing the comment if it is not containing json string
        check_if_json = re.findall(
            re.compile(r"[{:}]"),
            marker["comment"]
        )

        # to identify this as json, at least 3 items in the list should
        # be present ["{", ":", "}"]
        metadata = {}
        if len(check_if_json) >= 3:
            # this is json string
            try:
                # capture exceptions which are related to strings only
                metadata.update(
                    json.loads(marker["comment"])
                )
            except ValueError as msg:
                log.error("Marker json conversion: {}".format(msg))
        else:
            metadata["comment"] = marker["comment"]

        otio_marker = otio.schema.Marker(
            name=marker["name"],
            color=_get_marker_color(
                marker["colour"]),
            marked_range=marked_range,
            metadata=metadata
        )

        otio_item.markers.append(otio_marker)


def create_otio_reference(clip_data, duration, fps=None):
    metadata = _get_metadata(clip_data)

    # get file info for path and start frame
    frame_start = 0
    fps = fps or CTX.get_fps()

    path = clip_data["fpath"]

    file_name = os.path.basename(path)
    file_head, extension = os.path.splitext(file_name)

    # get padding and other file infos
    log.debug("_ path: {}".format(path))

    otio_ex_ref_item = None

    is_sequence = frame_number = utils.get_frame_from_filename(file_name)
    if is_sequence:
        file_head = file_name.split(frame_number)[:-1]
        frame_start = int(frame_number)
        padding = len(frame_number)

        metadata.update({
            "isSequence": True,
            "padding": padding
        })

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
                    duration,
                    fps
                )
            )
        except AttributeError:
            pass

    if not otio_ex_ref_item:
        dirname, file_name = os.path.split(path)
        file_name = utils.get_reformated_filename(file_name, padded=False)
        reformated_path = os.path.join(dirname, file_name)
        # in case old OTIO or video file create `ExternalReference`
        otio_ex_ref_item = otio.schema.ExternalReference(
            target_url=reformated_path,
            available_range=create_otio_time_range(
                frame_start,
                duration,
                fps
            )
        )

    # add metadata to otio item
    add_otio_metadata(otio_ex_ref_item, clip_data, **metadata)

    return otio_ex_ref_item


def create_otio_clip(clip_data):
    from openpype.hosts.flame.api import MediaInfoFile

    segment = clip_data["PySegment"]

    # calculate source in
    media_info = MediaInfoFile(clip_data["fpath"], **{
        "logger": log
    })
    media_timecode_start = media_info.start_frame
    media_fps = media_info.fps

    # define first frame
    first_frame = media_timecode_start or utils.get_frame_from_filename(
        clip_data["fpath"]) or 0

    _clip_source_in = int(clip_data["source_in"])
    _clip_source_out = int(clip_data["source_out"])
    _clip_record_duration = int(clip_data["record_duration"])

    # first solve if the reverse timing
    speed = 1
    if clip_data["source_in"] > clip_data["source_out"]:
        source_in = _clip_source_out - int(first_frame)
        source_out = _clip_source_in - int(first_frame)
        speed = -1
    else:
        source_in = _clip_source_in - int(first_frame)
        source_out = _clip_source_out - int(first_frame)

    source_duration = (source_out - source_in + 1)

    # secondly check if any change of speed
    if source_duration != _clip_record_duration:
        retime_speed = source_duration / _clip_record_duration
        speed *= retime_speed

    # create media reference
    media_reference = create_otio_reference(
        clip_data, source_duration, media_fps)

    # creatae source range
    source_range = create_otio_time_range(
        source_in,
        _clip_record_duration,
        CTX.get_fps()
    )

    otio_clip = otio.schema.Clip(
        name=clip_data["segment_name"],
        source_range=source_range,
        media_reference=media_reference
    )

    # Add markers
    if MARKERS_INCLUDE:
        create_otio_markers(otio_clip, segment)

    if speed != 1:
        create_time_effects(otio_clip, speed)

    return otio_clip


def create_otio_gap(gap_start, clip_start, tl_start_frame, fps):
    return otio.schema.Gap(
        source_range=create_otio_time_range(
            gap_start,
            (clip_start - tl_start_frame) - gap_start,
            fps
        )
    )


def _get_colourspace_policy():

    output = {}
    # get policies project path
    policy_dir = "/opt/Autodesk/project/{}/synColor/policy".format(
        CTX.project.name
    )
    log.debug(policy_dir)
    policy_fp = os.path.join(policy_dir, "policy.cfg")

    if not os.path.exists(policy_fp):
        return output

    with open(policy_fp) as file:
        dict_conf = dict(line.strip().split(' = ', 1) for line in file)
        output.update(
            {"openpype.flame.{}".format(k): v for k, v in dict_conf.items()}
        )
    return output


def _create_otio_timeline(sequence):

    metadata = _get_metadata(sequence)

    # find colour policy files and add them to metadata
    colorspace_policy = _get_colourspace_policy()
    metadata.update(colorspace_policy)

    metadata.update({
        "openpype.timeline.width": int(sequence.width),
        "openpype.timeline.height": int(sequence.height),
        "openpype.timeline.pixelAspect": 1
    })

    rt_start_time = create_otio_rational_time(
        CTX.get_tl_start_frame(), CTX.get_fps())

    return otio.schema.Timeline(
        name=str(sequence.name)[1:-1],
        global_start_time=rt_start_time,
        metadata=metadata
    )


def create_otio_track(track_type, track_name):
    return otio.schema.Track(
        name=track_name,
        kind=TRACK_TYPES[track_type]
    )


def add_otio_gap(clip_data, otio_track, prev_out):
    gap_length = clip_data["record_in"] - prev_out
    if prev_out != 0:
        gap_length -= 1

    gap = otio.opentime.TimeRange(
        duration=otio.opentime.RationalTime(
            gap_length,
            CTX.get_fps()
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


def _get_shot_tokens_values(clip, tokens):
    old_value = None
    output = {}

    old_value = clip.shot_name.get_value()

    for token in tokens:
        clip.shot_name.set_value(token)
        _key = re.sub("[ <>]", "", token)

        try:
            output[_key] = int(clip.shot_name.get_value())
        except ValueError:
            output[_key] = clip.shot_name.get_value()

    clip.shot_name.set_value(old_value)

    return output


def _get_segment_attributes(segment):

    log.debug("Segment name|hidden: {}|{}".format(
        segment.name.get_value(), segment.hidden
    ))
    if (
        segment.name.get_value() == ""
        or segment.hidden.get_value()
    ):
        return None

    # Add timeline segment to tree
    clip_data = {
        "segment_name": segment.name.get_value(),
        "segment_comment": segment.comment.get_value(),
        "shot_name": segment.shot_name.get_value(),
        "tape_name": segment.tape_name,
        "source_name": segment.source_name,
        "fpath": segment.file_path,
        "PySegment": segment
    }

    # add all available shot tokens
    shot_tokens = _get_shot_tokens_values(
        segment,
        ["<colour space>", "<width>", "<height>", "<depth>"]
    )
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

    CTX.project = get_current_flame_project()

    # get current timeline
    CTX.set_fps(
        float(str(sequence.frame_rate)[:-4]))

    tl_start_frame = utils.timecode_to_frames(
        str(sequence.start_time).replace("+", ":"),
        CTX.get_fps()
    )
    CTX.set_tl_start_frame(tl_start_frame)

    # convert timeline to otio
    otio_timeline = _create_otio_timeline(sequence)

    # create otio tracks and clips
    for ver in sequence.versions:
        for track in ver.tracks:
            # avoid all empty tracks
            # or hidden tracks
            if (
                len(track.segments) == 0
                or track.hidden.get_value()
            ):
                continue

            # convert track to otio
            otio_track = create_otio_track(
                "video", str(track.name)[1:-1])

            all_segments = []
            for segment in track.segments:
                clip_data = _get_segment_attributes(segment)
                if not clip_data:
                    continue
                all_segments.append(clip_data)

            segments_ordered = dict(enumerate(all_segments))
            log.debug("_ segments_ordered: {}".format(
                pformat(segments_ordered)
            ))
            if not segments_ordered:
                continue

            for itemindex, segment_data in segments_ordered.items():
                log.debug("_ itemindex: {}".format(itemindex))

                # Add Gap if needed
                prev_item = (
                    segment_data
                    if itemindex == 0
                    else segments_ordered[itemindex - 1]
                )
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
