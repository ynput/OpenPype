import re
import opentimelineio as otio
import logging
log = logging.getLogger(__name__)


def timecode_to_frames(timecode, framerate):
    rt = otio.opentime.from_timecode(timecode, framerate)
    return int(otio.opentime.to_frames(rt))


def frames_to_timecode(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_timecode(rt)


def frames_to_seconds(frames, framerate):
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
    padding = get_padding_from_path(path)
    found = get_frame_from_path(path)

    if not found:
        log.info("Path is not sequence: {}".format(path))
        return path

    if padded:
        path = path.replace(found, "%0{}d".format(padding))
    else:
        path = path.replace(found, "%d")

    return path


def get_padding_from_path(path):
    """
    Return padding number from Flame path style

    Args:
        path (str): path url or simple file name

    Returns:
        int: padding number

    Example:
        get_padding_from_path("plate.0001.exr") > 4

    """
    found = get_frame_from_path(path)

    if found:
        return len(found)
    else:
        return None


def get_frame_from_path(path):
    """
    Return sequence number from Flame path style

    Args:
        path (str): path url or simple file name

    Returns:
        int: sequence frame number

    Example:
        def get_frame_from_path(path):
            ("plate.0001.exr") > 0001

    """
    frame_pattern = re.compile(r"[._](\d+)[.]")

    found = re.findall(frame_pattern, path)

    if found:
        return found.pop()
    else:
        return None
