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
