import re


def timecode_to_frames(timecode, framerate):
    parts = zip((
        3600 * framerate,
        60 * framerate,
        framerate, 1
    ), timecode.split(":"))
    return sum(
        f * int(t) for f, t in parts
    )


def frames_to_timecode(frames, framerate):
    return '{0:02d}:{1:02d}:{2:02d}:{3:02d}'.format(
        int(frames / (3600 * framerate)),
        int(frames / (60 * framerate) % 60),
        int(frames / framerate % 60),
        int(frames % framerate))


def get_reformated_path(path, padded=True):
    """
    Return fixed python expression path

    Args:
        path (str): path url or simple file name

    Returns:
        type: string with reformated path

    Example:
        get_reformated_path("plate.[0001-1008].exr") > plate.%04d.exr

    """
    num_pattern = "(\\[\\d+\\-\\d+\\])"
    padding_pattern = "(\\d+)(?=-)"
    if "[" in path:
        padding = len(re.findall(padding_pattern, path).pop())
        if padded:
            path = re.sub(num_pattern, f"%0{padding}d", path)
        else:
            path = re.sub(num_pattern, f"%d", path)
    return path


def get_padding_from_path(path):
    """
    Return padding number from DaVinci Resolve sequence path style

    Args:
        path (str): path url or simple file name

    Returns:
        int: padding number

    Example:
        get_padding_from_path("plate.[0001-1008].exr") > 4

    """
    padding_pattern = "(\\d+)(?=-)"
    if "[" in path:
        return len(re.findall(padding_pattern, path).pop())

    return None
