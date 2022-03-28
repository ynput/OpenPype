import os
import re
import clique
from .import_utils import discover_host_vendor_module

try:
    import opentimelineio as otio
    from opentimelineio import opentime as _ot
except ImportError:
    if not os.environ.get("AVALON_APP"):
        raise
    otio = discover_host_vendor_module("opentimelineio")
    _ot = discover_host_vendor_module("opentimelineio.opentime")


def otio_range_to_frame_range(otio_range):
    start = _ot.to_frames(
        otio_range.start_time, otio_range.start_time.rate)
    end = start + _ot.to_frames(
        otio_range.duration, otio_range.duration.rate) - 1
    return start, end


def otio_range_with_handles(otio_range, instance):
    handle_start = instance.data["handleStart"]
    handle_end = instance.data["handleEnd"]
    handles_duration = handle_start + handle_end
    fps = float(otio_range.start_time.rate)
    start = _ot.to_frames(otio_range.start_time, fps)
    duration = _ot.to_frames(otio_range.duration, fps)

    return _ot.TimeRange(
        start_time=_ot.RationalTime((start - handle_start), fps),
        duration=_ot.RationalTime((duration + handles_duration), fps)
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
        media_range (otio._ot._ot.TimeRange): available range of media
        source_range (otio._ot._ot.TimeRange): clip required range

    Returns:
        otio._ot._ot.TimeRange: trimmed media range

    """
    rw_media_start = _ot.RationalTime(
        media_range.start_time.value + source_range.start_time.value,
        media_range.start_time.rate
    )
    rw_media_duration = _ot.RationalTime(
        source_range.duration.value,
        media_range.duration.rate
    )
    return _ot.TimeRange(
        rw_media_start, rw_media_duration)


def range_from_frames(start, duration, fps):
    """
    Returns otio time range.

    Args:
        start (int): frame start
        duration (int): frame duration
        fps (float): frame range

    Returns:
        otio._ot._ot.TimeRange: created range

    """
    return _ot.TimeRange(
        _ot.RationalTime(start, fps),
        _ot.RationalTime(duration, fps)
    )


def frames_to_secons(frames, framerate):
    """
    Returning secons.

    Args:
        frames (int): frame
        framerate (float): frame rate

    Returns:
        float: second value

    """
    rt = _ot.from_frames(frames, framerate)
    return _ot.to_seconds(rt)


def frames_to_timecode(frames, framerate):
    rt = _ot.from_frames(frames, framerate)
    return _ot.to_timecode(rt)


def make_sequence_collection(path, otio_range, metadata):
    """
    Make collection from path otio range and otio metadata.

    Args:
        path (str): path to image sequence with `%d`
        otio_range (otio._ot._ot.TimeRange): range to be used
        metadata (dict): data where padding value can be found

    Returns:
        list: dir_path (str): path to sequence, collection object

    """
    if "%" not in path:
        return None
    file_name = os.path.basename(path)
    dir_path = os.path.dirname(path)
    head = file_name.split("%")[0]
    tail = os.path.splitext(file_name)[-1]
    first, last = otio_range_to_frame_range(otio_range)
    collection = clique.Collection(
        head=head, tail=tail, padding=metadata["padding"])
    collection.indexes.update([i for i in range(first, (last + 1))])
    return dir_path, collection


def _sequence_resize(source, length):
    step = float(len(source) - 1) / (length - 1)
    for i in range(length):
        low, ratio = divmod(i * step, 1)
        high = low + 1 if ratio > 0 else low
        yield (1 - ratio) * source[int(low)] + ratio * source[int(high)]


def get_media_range_with_retimes(otio_clip, handle_start, handle_end):
    source_range = otio_clip.source_range
    available_range = otio_clip.available_range()
    media_in = available_range.start_time.value
    media_out = available_range.end_time_inclusive().value

    # modifiers
    time_scalar = 1.
    offset_in = 0
    offset_out = 0
    time_warp_nodes = []

    # Check for speed effects and adjust playback speed accordingly
    for effect in otio_clip.effects:
        if isinstance(effect, otio.schema.LinearTimeWarp):
            time_scalar = effect.time_scalar

        elif isinstance(effect, otio.schema.FreezeFrame):
            # For freeze frame, playback speed must be set after range
            time_scalar = 0.

        elif isinstance(effect, otio.schema.TimeEffect):
            # For freeze frame, playback speed must be set after range
            name = effect.name
            effect_name = effect.effect_name
            if "TimeWarp" not in effect_name:
                continue
            metadata = effect.metadata
            lookup = metadata.get("lookup")
            if not lookup:
                continue

            # time warp node
            tw_node = {
                "Class": "TimeWarp",
                "name": name
            }
            tw_node.update(metadata)

            # get first and last frame offsets
            offset_in += lookup[0]
            offset_out += lookup[-1]

            # add to timewarp nodes
            time_warp_nodes.append(tw_node)

    # multiply by time scalar
    offset_in *= time_scalar
    offset_out *= time_scalar

    # filip offset if reversed speed
    if time_scalar < 0:
        _offset_in = offset_out
        _offset_out = offset_in
        offset_in = _offset_in
        offset_out = _offset_out

    # scale handles
    handle_start *= abs(time_scalar)
    handle_end *= abs(time_scalar)

    # filip handles if reversed speed
    if time_scalar < 0:
        _handle_start = handle_end
        _handle_end = handle_start
        handle_start = _handle_start
        handle_end = _handle_end

    source_in = source_range.start_time.value

    media_in_trimmed = (
        media_in + source_in + offset_in)
    media_out_trimmed = (
        media_in + source_in + (
            ((source_range.duration.value - 1) * abs(
                time_scalar)) + offset_out))

    # calculate available handles
    if (media_in_trimmed - media_in) < handle_start:
        handle_start = (media_in_trimmed - media_in)
    if (media_out - media_out_trimmed) < handle_end:
        handle_end = (media_out - media_out_trimmed)

    # create version data
    version_data = {
        "versionData": {
            "retime": True,
            "speed": time_scalar,
            "timewarps": time_warp_nodes,
            "handleStart": handle_start,
            "handleEnd": handle_end
        }
    }

    returning_dict = {
        "mediaIn": media_in_trimmed,
        "mediaOut": media_out_trimmed,
        "handleStart": handle_start,
        "handleEnd": handle_end
    }

    # add version data only if retime
    if time_warp_nodes or time_scalar != 1.:
        returning_dict.update(version_data)

    return returning_dict


def get_offset_timecode(source_tc, fps, offset=-1):
    """
    Returns a timecode plus offset in frames.
    Handles drop frame rates automatically, treats 23.98
    and 23.976 as 24 fps.
    for more info check this very informative page:
    https://www.davidheidelberger.com/2010/06/10/drop-frame-timecode/
    """
    frame = tc_to_frame(source_tc, fps)
    frame += offset
    return frame_to_tc(frame, fps)


def str_to_number(s):
    """
    Converts a string to a correctly cast number (float or int)
    """
    if isinstance(s, str):
        try:
            val = float(s)
            if val.is_integer(): 
                return int(val)
            return val
        except:
            val = s
    else:
        val = s
    return val


def check_drop_frame(fps):
    """
    Returns if a framerate is non drop-frame or drop-frame.
    Treats 23.976 and 23.98 as 24 (so non drop-frame)
    since there's too little deviation to be meaningful.
    """
    is_drop = False
    real_fps = str_to_number(fps)
    if isinstance(real_fps, float):
        if real_fps > 24:
            is_drop = True
    return is_drop


def tc_to_frame(tc, fps):
    """
    Returns correct frame number for any given timecode
    and fps. Correctly infers if it's drop frame or not
    """
    tc_split = list(map(int, tc.split(":")))
    hours = tc_split[0]
    minutes = tc_split[1]
    seconds = tc_split[2]
    frames = tc_split[3]

    is_drop = check_drop_frame(fps)
    real_fps = str_to_number(fps)
    tb = real_fps
    
    if isinstance(real_fps, float):
        tb = round(tb)
    
    if is_drop:
        df = round(tb * 0.066666)
        computed_frame = (
            ((tb * 60 * 60 * hours) + 
            (tb * 60 * minutes) + 
            (tb * seconds) +
            frames) -
            ((df * (((60 * hours) + minutes) -
            (((60 * hours) + minutes) // 10))))
        )
    else:
        computed_frame = (
            (tb * 60 * 60 * hours) +
            (tb * 60 * minutes) +
            (tb * seconds) +
            frames
        )
    return computed_frame


def frame_to_tc(frame, fps):
    """
    Returns a formed timecode from frame number
    and fps. Correctly infers if it's drop of not
    """
    is_drop = check_drop_frame(fps)
    real_fps = str_to_number(fps)
    tb = real_fps
    
    if isinstance(real_fps, float):
        tb = round(tb)
    
    if is_drop:
        df = round(real_fps * 0.066666)
        frames_per_hour = round(real_fps * 60 * 60)
        frames_per_24_hours = frames_per_hour * 24 
        frames_per_10_minutes = round(real_fps * 60 * 10)
        frames_per_minute = (tb * 60) - df

        if frame < 0:
            frame = frames_per_24_hours + frame
        frame = frame % frames_per_24_hours
        d = frame // frames_per_10_minutes 
        m = frame % frames_per_10_minutes
        
        if m > df:
            frame = (frame + (df * 9 * d) +
                df * ((m - df) // frames_per_minute))
        else:
            frame = frame + df * 9 * d
        
        hours = (((frame // tb) // 60) // 60)
        minutes = ((frame // tb) // 60) % 60
        seconds = (frame // tb) % 60
        frames = frame % tb

        return "{}:{}:{};{}".format(hours, minutes, seconds, frames)

    else:           
        if (frame < 0):
            frame = frame + (tb * 60 * 60 * 24)
        
        frame = frame % (tb * 60 * 60 * 24)
        remainder = frame

        hours = remainder // (tb * 60 * 60)
        remainder = remainder - (hours * (tb * 60 * 60))
        minutes = remainder // (tb * 60)
        remainder = remainder - (minutes * (tb * 60))
        seconds = remainder // tb
        frames = remainder - (seconds * tb)

        return "{}:{}:{}:{}".format(hours, minutes, seconds, frames)
        