import re
import opentimelineio as otio
import logging
log = logging.getLogger(__name__)

FRAME_PATTERN = re.compile(r"[\._](\d+)[\.]")


def timecode_to_frames(timecode, framerate):
    rt = otio.opentime.from_timecode(timecode, framerate)
    return int(otio.opentime.to_frames(rt))


def frames_to_timecode(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_timecode(rt)


def frames_to_seconds(frames, framerate):
    rt = otio.opentime.from_frames(frames, framerate)
    return otio.opentime.to_seconds(rt)


def get_reformated_filename(filename, padded=True):
    """
    Return fixed python expression path

    Args:
        filename (str): file name

    Returns:
        type: string with reformated path

    Example:
        get_reformated_filename("plate.1001.exr") > plate.%04d.exr

    """
    found = FRAME_PATTERN.search(filename)

    if not found:
        log.info("File name is not sequence: {}".format(filename))
        return filename

    padding = get_padding_from_filename(filename)

    replacement = "%0{}d".format(padding) if padded else "%d"
    start_idx, end_idx = found.span(1)

    return replacement.join(
        [filename[:start_idx], filename[end_idx:]]
    )


def get_padding_from_filename(filename):
    """
    Return padding number from Flame path style

    Args:
        filename (str): file name

    Returns:
        int: padding number

    Example:
        get_padding_from_filename("plate.0001.exr") > 4

    """
    found = get_frame_from_filename(filename)

    return len(found) if found else None


def get_frame_from_filename(filename):
    """
    Return sequence number from Flame path style

    Args:
        filename (str): file name

    Returns:
        int: sequence frame number

    Example:
        def get_frame_from_filename(path):
            ("plate.0001.exr") > 0001

    """

    found = re.findall(FRAME_PATTERN, filename)

    return found.pop() if found else None
