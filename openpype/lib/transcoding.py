import os
import re
import logging
import collections
import tempfile

from .execute import run_subprocess
from .vendor_bin_utils import (
    get_oiio_tools_path,
    is_oiio_supported
)


def get_transcode_temp_directory():
    """Creates temporary folder for transcoding.

    Its local, in case of farm it is 'local' to the farm machine.

    Should be much faster, needs to be cleaned up later.
    """
    return os.path.normpath(
        tempfile.mkdtemp(prefix="op_transcoding_")
    )


def get_oiio_info_for_input(filepath, logger=None):
    """Call oiiotool to get information about input and return stdout."""
    args = [
        get_oiio_tools_path(), "--info", "-v", filepath
    ]
    return run_subprocess(args, logger=logger)


def parse_oiio_info(oiio_info):
    """Create an object based on output from oiiotool.

    Removes quotation marks from compression value. Parse channels into
    dictionary - key is channel name value is determined type of channel
    (e.g. 'uint', 'float').

    Args:
        oiio_info (str): Output of calling "oiiotool --info -v <path>"

    Returns:
        dict: Loaded data from output.
    """
    lines = [
        line.strip()
        for line in oiio_info.split("\n")
    ]
    # Each line should contain information about one key
    #   key - value are separated with ": "
    oiio_sep = ": "
    data_map = {}
    for line in lines:
        parts = line.split(oiio_sep)
        if len(parts) < 2:
            continue
        key = parts.pop(0)
        value = oiio_sep.join(parts)
        data_map[key] = value

    if "compression" in data_map:
        value = data_map["compression"]
        data_map["compression"] = value.replace("\"", "")

    channels_info = {}
    channels_value = data_map.get("channel list") or ""
    if channels_value:
        channels = channels_value.split(", ")
        type_regex = re.compile(r"(?P<name>[^\(]+) \((?P<type>[^\)]+)\)")
        for channel in channels:
            match = type_regex.search(channel)
            if not match:
                channel_name = channel
                channel_type = "uint"
            else:
                channel_name = match.group("name")
                channel_type = match.group("type")
            channels_info[channel_name] = channel_type
    data_map["channels_info"] = channels_info
    return data_map


def get_convert_rgb_channels(channels_info):
    """Get first available RGB(A) group from channels info.

    ## Examples
    ```
    # Ideal situation
    channels_info: {
        "R": ...,
        "G": ...,
        "B": ...,
        "A": ...
    }
    ```
    Result will be `("R", "G", "B", "A")`

    ```
    # Not ideal situation
    channels_info: {
        "beauty.red": ...,
        "beuaty.green": ...,
        "beauty.blue": ...,
        "depth.Z": ...
    }
    ```
    Result will be `("beauty.red", "beauty.green", "beauty.blue", None)`

    Returns:
        NoneType: There is not channel combination that matches RGB
            combination.
        tuple: Tuple of 4 channel names defying channel names for R, G, B, A
            where A can be None.
    """
    rgb_by_main_name = collections.defaultdict(dict)
    main_name_order = [""]
    for channel_name in channels_info.keys():
        name_parts = channel_name.split(".")
        rgb_part = name_parts.pop(-1).lower()
        main_name = ".".join(name_parts)
        if rgb_part in ("r", "red"):
            rgb_by_main_name[main_name]["R"] = channel_name
        elif rgb_part in ("g", "green"):
            rgb_by_main_name[main_name]["G"] = channel_name
        elif rgb_part in ("b", "blue"):
            rgb_by_main_name[main_name]["B"] = channel_name
        elif rgb_part in ("a", "alpha"):
            rgb_by_main_name[main_name]["A"] = channel_name
        else:
            continue
        if main_name not in main_name_order:
            main_name_order.append(main_name)

    output = None
    for main_name in main_name_order:
        colors = rgb_by_main_name.get(main_name) or {}
        red = colors.get("R")
        green = colors.get("G")
        blue = colors.get("B")
        alpha = colors.get("A")
        if red is not None and green is not None and blue is not None:
            output = (red, green, blue, alpha)
            break

    return output


def should_convert_for_ffmpeg(src_filepath):
    """Find out if input should be converted for ffmpeg.

    Currently cares only about exr inputs and is based on OpenImageIO.

    Returns:
        bool/NoneType: True if should be converted, False if should not and
            None if can't determine.
    """
    # Care only about exr at this moment
    ext = os.path.splitext(src_filepath)[-1].lower()
    if ext != ".exr":
        return False

    # Can't determine if should convert or not without oiio_tool
    if not is_oiio_supported():
        return None

    # Load info about info from oiio tool
    oiio_info = get_oiio_info_for_input(src_filepath)
    input_info = parse_oiio_info(oiio_info)

    # Check compression
    compression = input_info["compression"]
    if compression in ("dwaa", "dwab"):
        return True

    # Check channels
    channels_info = input_info["channels_info"]
    review_channels = get_convert_rgb_channels(channels_info)
    if review_channels is None:
        return None

    return False


def convert_for_ffmpeg(
    first_input_path,
    output_dir,
    input_frame_start,
    input_frame_end,
    logger=None
):
    """Contert source file to format supported in ffmpeg.

    Currently can convert only exrs.

    Args:
        first_input_path (str): Path to first file of a sequence or a single
            file path for non-sequential input.
        output_dir (str): Path to directory where output will be rendered.
            Must not be same as input's directory.
        input_frame_start (int): Frame start of input.
        input_frame_end (int): Frame end of input.
        logger (logging.Logger): Logger used for logging.

    Raises:
        ValueError: If input filepath has extension not supported by function.
            Currently is supported only ".exr" extension.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    ext = os.path.splitext(first_input_path)[1].lower()
    if ext != ".exr":
        raise ValueError((
            "Function 'convert_for_ffmpeg' currently support only"
            " \".exr\" extension. Got \"{}\"."
        ).format(ext))

    is_sequence = False
    if input_frame_start is not None and input_frame_end is not None:
        is_sequence = int(input_frame_end) != int(input_frame_start)

    oiio_info = get_oiio_info_for_input(first_input_path)
    input_info = parse_oiio_info(oiio_info)

    # Change compression only if source compression is "dwaa" or "dwab"
    #   - they're not supported in ffmpeg
    compression = input_info["compression"]
    if compression in ("dwaa", "dwab"):
        compression = "none"

    # Prepare subprocess arguments
    oiio_cmd = [
        get_oiio_tools_path(),
        "--compression", compression,
        first_input_path
    ]

    channels_info = input_info["channels_info"]
    review_channels = get_convert_rgb_channels(channels_info)
    if review_channels is None:
        raise ValueError(
            "Couldn't find channels that can be used for conversion."
        )

    red, green, blue, alpha = review_channels
    channels_arg = "R={},G={},B={}".format(red, green, blue)
    if alpha is not None:
        channels_arg += ",A={}".format(alpha)
    oiio_cmd.append("--ch")
    oiio_cmd.append(channels_arg)

    # Add frame definitions to arguments
    if is_sequence:
        oiio_cmd.append("--frames")
        oiio_cmd.append("{}-{}".format(input_frame_start, input_frame_end))

    # Add last argument - path to output
    base_file_name = os.path.basename(first_input_path)
    output_path = os.path.join(output_dir, base_file_name)
    oiio_cmd.append("-o")
    oiio_cmd.append(output_path)

    logger.debug("Conversion command: {}".format(" ".join(oiio_cmd)))
    run_subprocess(oiio_cmd, logger=logger)
