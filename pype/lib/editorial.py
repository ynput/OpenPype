import re
from opentimelineio import opentime
from opentimelineio.opentime import (
    to_frames, RationalTime, TimeRange)


def otio_range_to_frame_range(otio_range):
    start = to_frames(
        otio_range.start_time, otio_range.start_time.rate)
    end = start + to_frames(
        otio_range.duration, otio_range.duration.rate) - 1
    return start, end


def otio_range_with_handles(otio_range, instance):
    handle_start = instance.data["handleStart"]
    handle_end = instance.data["handleEnd"]
    handles_duration = handle_start + handle_end
    fps = float(otio_range.start_time.rate)
    start = to_frames(otio_range.start_time, fps)
    duration = to_frames(otio_range.duration, fps)

    return TimeRange(
        start_time=RationalTime((start - handle_start), fps),
        duration=RationalTime((duration + handles_duration), fps)
    )


def is_overlapping_otio_ranges(test_otio_range, main_otio_range, strict=False):
    test_start, test_end = otio_range_to_frame_range(test_otio_range)
    main_start, main_end = otio_range_to_frame_range(main_otio_range)
    covering_exp = bool(
        (test_start <= main_start) and (test_end >= main_end)
    )
    inside_exp = bool(
        (test_start >= main_start) and (test_end <= main_end)
    )
    overlaying_right_exp = bool(
        (test_start <= main_end) and (test_end >= main_end)
    )
    overlaying_left_exp = bool(
        (test_end >= main_start) and (test_start <= main_start)
    )

    if not strict:
        return any((
            covering_exp,
            inside_exp,
            overlaying_right_exp,
            overlaying_left_exp
        ))
    else:
        return covering_exp


def convert_to_padded_path(path, padding):
    """
    Return correct padding in sequence string

    Args:
        path (str): path url or simple file name
        padding (int): number of padding

    Returns:
        type: string with reformated path

    Example:
        convert_to_padded_path("plate.%d.exr") > plate.%04d.exr

    """
    if "%d" in path:
        path = re.sub("%d", "%0{padding}d".format(padding=padding), path)
    return path


def trim_media_range(media_range, source_range):
    """
    Trim input media range with clip source range.

    Args:
        media_range (otio.opentime.TimeRange): available range of media
        source_range (otio.opentime.TimeRange): clip required range

    Returns:
        otio.opentime.TimeRange: trimmed media range

    """
    rw_media_start = RationalTime(
        media_range.start_time.value + source_range.start_time.value,
        media_range.start_time.rate
    )
    rw_media_duration = RationalTime(
        source_range.duration.value,
        media_range.duration.rate
    )
    return TimeRange(
        rw_media_start, rw_media_duration)


def range_from_frames(start, duration, fps):
    """
    Returns otio time range.

    Args:
        start (int): frame start
        duration (int): frame duration
        fps (float): frame range

    Returns:
        otio.opentime.TimeRange: crated range

    """
    return TimeRange(
        RationalTime(start, fps),
        RationalTime(duration, fps)
    )


def frames_to_secons(frames, framerate):
    """
    Returning secons.

    Args:
        frames (int): frame
        framerate (flaot): frame rate

    Returns:
        float: second value

    """
    rt = opentime.from_frames(frames, framerate)
    return opentime.to_seconds(rt)
