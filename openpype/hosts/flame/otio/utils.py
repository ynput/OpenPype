import re
import opentimelineio as otio


def timecode_to_frames(timecode, framerate):
    rt = otio.opentime.from_timecode(timecode, framerate)
    return int(otio.opentime.to_frames(rt))


def frames_to_timecode(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_timecode(rt)


def frames_to_secons(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_seconds(rt)


def get_reformated_path(path, padded=True):
    """
    Return fixed python expression path

    Args:
        path (str): path url or simple file name

    Returns:
        type: string with reformated path

    Example:
        get_reformated_path("plate.1001.exr") > plate.%04d.exr

    """
    num_pattern = re.compile(r"[._](\d+)[.]")
    padding = get_padding_from_path(path)

    if padded:
        path = re.sub(num_pattern, "%0{}d".format(padding), path)
    else:
        path = re.sub(num_pattern, "%d", path)

    return path


def get_padding_from_path(path):
    """
    Return padding number from DaVinci Resolve sequence path style

    Args:
        path (str): path url or simple file name

    Returns:
        int: padding number

    Example:
        get_padding_from_path("plate.0001.exr") > 4

    """
    padding_pattern = re.compile(r"[._](\d+)[.]")

    found = re.findall(padding_pattern, path).pop()

    if found:
        return len(found)
    else:
        return None