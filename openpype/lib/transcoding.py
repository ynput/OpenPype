import os
import re
import logging
import json
import collections
import tempfile
import subprocess
import platform

import xml.etree.ElementTree

from .execute import run_subprocess
from .vendor_bin_utils import (
    get_ffmpeg_tool_args,
    get_oiio_tool_args,
    is_oiio_supported,
)

# Max length of string that is supported by ffmpeg
MAX_FFMPEG_STRING_LEN = 8196
# Not allowed symbols in attributes for ffmpeg
NOT_ALLOWED_FFMPEG_CHARS = ("\"", )

# OIIO known xml tags
STRING_TAGS = {
    "format"
}
INT_TAGS = {
    "x", "y", "z",
    "width", "height", "depth",
    "full_x", "full_y", "full_z",
    "full_width", "full_height", "full_depth",
    "tile_width", "tile_height", "tile_depth",
    "nchannels",
    "alpha_channel",
    "z_channel",
    "deep",
    "subimages",
}

XML_CHAR_REF_REGEX_HEX = re.compile(r"&#x?[0-9a-fA-F]+;")

# Regex to parse array attributes
ARRAY_TYPE_REGEX = re.compile(r"^(int|float|string)\[\d+\]$")

IMAGE_EXTENSIONS = {
    ".ani", ".anim", ".apng", ".art", ".bmp", ".bpg", ".bsave",
    ".cal", ".cin", ".cpc", ".cpt", ".dds", ".dpx", ".ecw", ".exr",
    ".fits", ".flic", ".flif", ".fpx", ".gif", ".hdri", ".hevc",
    ".icer", ".icns", ".ico", ".cur", ".ics", ".ilbm", ".jbig", ".jbig2",
    ".jng", ".jpeg", ".jpeg-ls", ".jpeg-hdr", ".2000", ".jpg",
    ".kra", ".logluv", ".mng", ".miff", ".nrrd", ".ora",
    ".pam", ".pbm", ".pgm", ".ppm", ".pnm", ".pcx", ".pgf",
    ".pictor", ".png", ".psd", ".psb", ".psp", ".qtvr",
    ".ras", ".rgbe", ".sgi", ".tga",
    ".tif", ".tiff", ".tiff/ep", ".tiff/it", ".ufo", ".ufp",
    ".wbmp", ".webp", ".xr", ".xt", ".xbm", ".xcf", ".xpm", ".xwd"
}

VIDEO_EXTENSIONS = {
    ".3g2", ".3gp", ".amv", ".asf", ".avi", ".drc", ".f4a", ".f4b",
    ".f4p", ".f4v", ".flv", ".gif", ".gifv", ".m2v", ".m4p", ".m4v",
    ".mkv", ".mng", ".mov", ".mp2", ".mp4", ".mpe", ".mpeg", ".mpg",
    ".mpv", ".mxf", ".nsv", ".ogg", ".ogv", ".qt", ".rm", ".rmvb",
    ".roq", ".svi", ".vob", ".webm", ".wmv", ".yuv"
}


def get_transcode_temp_directory():
    """Creates temporary folder for transcoding.

    Its local, in case of farm it is 'local' to the farm machine.

    Should be much faster, needs to be cleaned up later.
    """
    return os.path.normpath(
        tempfile.mkdtemp(prefix="op_transcoding_")
    )


def get_oiio_info_for_input(filepath, logger=None, subimages=False):
    """Call oiiotool to get information about input and return stdout.

    Stdout should contain xml format string.
    """
    args = get_oiio_tool_args(
        "oiiotool",
        "--info",
        "-v"
    )
    if subimages:
        args.append("-a")

    args.extend(["-i:infoformat=xml", filepath])

    output = run_subprocess(args, logger=logger)
    output = output.replace("\r\n", "\n")

    xml_started = False
    subimages_lines = []
    lines = []
    for line in output.split("\n"):
        if not xml_started:
            if not line.startswith("<"):
                continue
            xml_started = True

        if xml_started:
            lines.append(line)
            if line == "</ImageSpec>":
                subimages_lines.append(lines)
                lines = []
                xml_started = False

    if not subimages_lines:
        raise ValueError(
            "Failed to read input file \"{}\".\nOutput:\n{}".format(
                filepath, output
            )
        )

    output = []
    for subimage_lines in subimages_lines:
        xml_text = "\n".join(subimage_lines)
        output.append(parse_oiio_xml_output(xml_text, logger=logger))

    if subimages:
        return output
    return output[0]


class RationalToInt:
    """Rational value stored as division of 2 integers using string."""

    def __init__(self, string_value):
        parts = string_value.split("/")
        top = float(parts[0])
        bottom = 1.0
        if len(parts) != 1:
            bottom = float(parts[1])

        self._value = float(top) / float(bottom)
        self._string_value = string_value

    @property
    def value(self):
        return self._value

    @property
    def string_value(self):
        return self._string_value

    def __format__(self, *args, **kwargs):
        return self._string_value.__format__(*args, **kwargs)

    def __float__(self):
        return self._value

    def __str__(self):
        return self._string_value

    def __repr__(self):
        return "<{}> {}".format(self.__class__.__name__, self._string_value)


def convert_value_by_type_name(value_type, value, logger=None):
    """Convert value to proper type based on type name.

    In some cases value types have custom python class.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Simple types
    if value_type == "string":
        return value

    if value_type == "int":
        return int(value)

    if value_type in ("float", "double"):
        return float(value)

    # Vectors will probably have more types
    if value_type in ("vec2f", "float2", "float2d"):
        return [float(item) for item in value.split(",")]

    # Matrix should be always have square size of element 3x3, 4x4
    # - are returned as list of lists
    if value_type in ("matrix", "matrixd"):
        output = []
        current_index = -1
        parts = value.split(",")
        parts_len = len(parts)
        if parts_len == 1:
            divisor = 1
        elif parts_len == 4:
            divisor = 2
        elif parts_len == 9:
            divisor = 3
        elif parts_len == 16:
            divisor = 4
        else:
            logger.info("Unknown matrix resolution {}. Value: \"{}\"".format(
                parts_len, value
            ))
            for part in parts:
                output.append(float(part))
            return output

        for idx, item in enumerate(parts):
            list_index = idx % divisor
            if list_index > current_index:
                current_index = list_index
                output.append([])
            output[list_index].append(float(item))
        return output

    if value_type == "rational2i":
        return RationalToInt(value)

    if value_type in ("vector", "vectord"):
        parts = [part.strip() for part in value.split(",")]
        output = []
        for part in parts:
            if part == "-nan":
                output.append(None)
                continue
            try:
                part = float(part)
            except ValueError:
                pass
            output.append(part)
        return output

    if value_type == "timecode":
        return value

    # Array of other types is converted to list
    re_result = ARRAY_TYPE_REGEX.findall(value_type)
    if re_result:
        array_type = re_result[0]
        output = []
        for item in value.split(","):
            output.append(
                convert_value_by_type_name(array_type, item, logger=logger)
            )
        return output

    logger.debug((
        "Dev note (missing implementation):"
        " Unknown attrib type \"{}\". Value: {}"
    ).format(value_type, value))
    return value


def parse_oiio_xml_output(xml_string, logger=None):
    """Parse xml output from OIIO info command."""
    output = {}
    if not xml_string:
        return output

    # Fix values with ampresand (lazy fix)
    # - oiiotool exports invalid xml which ElementTree can't handle
    #   e.g. "&#01;"
    # WARNING: this will affect even valid character entities. If you need
    #   those values correctly, this must take care of valid character ranges.
    #   See https://github.com/pypeclub/OpenPype/pull/2729
    matches = XML_CHAR_REF_REGEX_HEX.findall(xml_string)
    for match in matches:
        new_value = match.replace("&", "&amp;")
        xml_string = xml_string.replace(match, new_value)

    if logger is None:
        logger = logging.getLogger("OIIO-xml-parse")

    tree = xml.etree.ElementTree.fromstring(xml_string)
    attribs = {}
    output["attribs"] = attribs
    for child in tree:
        tag_name = child.tag
        if tag_name == "attrib":
            attrib_def = child.attrib
            value = convert_value_by_type_name(
                attrib_def["type"], child.text, logger=logger
            )

            attribs[attrib_def["name"]] = value
            continue

        # Channels are stored as tex on each child
        if tag_name == "channelnames":
            value = []
            for channel in child:
                value.append(channel.text)

        # Convert known integer type tags to int
        elif tag_name in INT_TAGS:
            value = int(child.text)

        # Keep value of known string tags
        elif tag_name in STRING_TAGS:
            value = child.text

        # Keep value as text for unknown tags
        # - feel free to add more tags
        else:
            value = child.text
            logger.debug((
                "Dev note (missing implementation):"
                " Unknown tag \"{}\". Value \"{}\""
            ).format(tag_name, value))

        output[child.tag] = value

    return output


def get_review_info_by_layer_name(channel_names):
    """Get channels info grouped by layer name.

    Finds all layers in channel names and returns list of dictionaries with
    information about channels in layer.
    Example output (not real world example):
        [
            {
                "name": "Main",
                "review_channels": {
                    "R": "Main.red",
                    "G": "Main.green",
                    "B": "Main.blue",
                    "A": None,
                }
            },
            {
                "name": "Composed",
                "review_channels": {
                    "R": "Composed.R",
                    "G": "Composed.G",
                    "B": "Composed.B",
                    "A": "Composed.A",
                }
            },
            ...
        ]

    Args:
        channel_names (list[str]): List of channel names.

    Returns:
        list[dict]: List of channels information.
    """

    layer_names_order = []
    rgba_by_layer_name = collections.defaultdict(dict)
    channels_by_layer_name = collections.defaultdict(dict)

    for channel_name in channel_names:
        layer_name = ""
        last_part = channel_name
        if "." in channel_name:
            layer_name, last_part = channel_name.rsplit(".", 1)

        channels_by_layer_name[layer_name][channel_name] = last_part
        if last_part.lower() not in {
            "r", "red",
            "g", "green",
            "b", "blue",
            "a", "alpha"
        }:
            continue

        if layer_name not in layer_names_order:
            layer_names_order.append(layer_name)
        # R, G, B or A
        channel = last_part[0].upper()
        rgba_by_layer_name[layer_name][channel] = channel_name

    # Put empty layer to the beginning of the list
    # - if input has R, G, B, A channels they should be used for review
    if "" in layer_names_order:
        layer_names_order.remove("")
        layer_names_order.insert(0, "")

    output = []
    for layer_name in layer_names_order:
        rgba_layer_info = rgba_by_layer_name[layer_name]
        red = rgba_layer_info.get("R")
        green = rgba_layer_info.get("G")
        blue = rgba_layer_info.get("B")
        if not red or not green or not blue:
            continue
        output.append({
            "name": layer_name,
            "review_channels": {
                "R": red,
                "G": green,
                "B": blue,
                "A": rgba_layer_info.get("A"),
            }
        })
    return output


def get_convert_rgb_channels(channel_names):
    """Get first available RGB(A) group from channels info.

    ## Examples
    ```
    # Ideal situation
    channels_info: [
        "R", "G", "B", "A"
    ]
    ```
    Result will be `("R", "G", "B", "A")`

    ```
    # Not ideal situation
    channels_info: [
        "beauty.red",
        "beauty.green",
        "beauty.blue",
        "depth.Z"
    ]
    ```
    Result will be `("beauty.red", "beauty.green", "beauty.blue", None)`

    Args:
        channel_names (list[str]): List of channel names.

    Returns:
        Union[NoneType, tuple[str, str, str, Union[str, None]]]: Tuple of
            4 channel names defying channel names for R, G, B, A or None
            if there is not any layer with RGB combination.
    """

    channels_info = get_review_info_by_layer_name(channel_names)
    for item in channels_info:
        review_channels = item["review_channels"]
        return (
            review_channels["R"],
            review_channels["G"],
            review_channels["B"],
            review_channels["A"]
        )
    return None


def get_review_layer_name(src_filepath):
    """Find layer name that could be used for review.

    Args:
        src_filepath (str): Path to input file.

    Returns:
        Union[str, None]: Layer name of None.
    """

    ext = os.path.splitext(src_filepath)[-1].lower()
    if ext != ".exr":
        return None

    # Load info about file from oiio tool
    input_info = get_oiio_info_for_input(src_filepath)
    if not input_info:
        return None

    channel_names = input_info["channelnames"]
    channels_info = get_review_info_by_layer_name(channel_names)
    for item in channels_info:
        # Layer name can be '', when review channels are 'R', 'G', 'B'
        #   without layer
        return item["name"] or None
    return None


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

    # Load info about file from oiio tool
    input_info = get_oiio_info_for_input(src_filepath)
    if not input_info:
        return None

    subimages = input_info.get("subimages")
    if subimages is not None and subimages > 1:
        return True

    # Check compression
    compression = input_info["attribs"].get("compression")
    if compression in ("dwaa", "dwab"):
        return True

    # Check channels
    channel_names = input_info["channelnames"]
    review_channels = get_convert_rgb_channels(channel_names)
    if review_channels is None:
        return None

    for attr_value in input_info["attribs"].values():
        if not isinstance(attr_value, str):
            continue

        if len(attr_value) > MAX_FFMPEG_STRING_LEN:
            return True

        for char in NOT_ALLOWED_FFMPEG_CHARS:
            if char in attr_value:
                return True
    return False


# Deprecated since 2022 4 20
# - Reason - Doesn't convert sequences right way: Can't handle gaps, reuse
#       first frame for all frames and changes filenames when input
#       is sequence.
# - use 'convert_input_paths_for_ffmpeg' instead
def convert_for_ffmpeg(
    first_input_path,
    output_dir,
    input_frame_start=None,
    input_frame_end=None,
    logger=None
):
    """Convert source file to format supported in ffmpeg.

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

    logger.warning((
        "DEPRECATED: 'openpype.lib.transcoding.convert_for_ffmpeg' is"
        " deprecated function of conversion for FFMpeg. Please replace usage"
        " with 'openpype.lib.transcoding.convert_input_paths_for_ffmpeg'"
    ))

    ext = os.path.splitext(first_input_path)[1].lower()
    if ext != ".exr":
        raise ValueError((
            "Function 'convert_for_ffmpeg' currently support only"
            " \".exr\" extension. Got \"{}\"."
        ).format(ext))

    is_sequence = False
    if input_frame_start is not None and input_frame_end is not None:
        is_sequence = int(input_frame_end) != int(input_frame_start)

    input_info = get_oiio_info_for_input(first_input_path, logger=logger)

    # Change compression only if source compression is "dwaa" or "dwab"
    #   - they're not supported in ffmpeg
    compression = input_info["attribs"].get("compression")
    if compression in ("dwaa", "dwab"):
        compression = "none"

    # Prepare subprocess arguments
    oiio_cmd = get_oiio_tool_args(
        "oiiotool",
        # Don't add any additional attributes
        "--nosoftwareattrib",
    )
    # Add input compression if available
    if compression:
        oiio_cmd.extend(["--compression", compression])

    # Collect channels to export
    input_arg, channels_arg = get_oiio_input_and_channel_args(input_info)

    oiio_cmd.extend([
        input_arg, first_input_path,
        # Tell oiiotool which channels should be put to top stack (and output)
        "--ch", channels_arg,
        # Use first subimage
        "--subimage", "0"
    ])

    # Add frame definitions to arguments
    if is_sequence:
        oiio_cmd.extend([
            "--frames", "{}-{}".format(input_frame_start, input_frame_end)
        ])

    for attr_name, attr_value in input_info["attribs"].items():
        if not isinstance(attr_value, str):
            continue

        # Remove attributes that have string value longer than allowed length
        #   for ffmpeg or when contain prohibited symbols
        erase_reason = "Missing reason"
        erase_attribute = False
        if len(attr_value) > MAX_FFMPEG_STRING_LEN:
            erase_reason = "has too long value ({} chars).".format(
                len(attr_value)
            )
            erase_attribute = True

        if not erase_attribute:
            for char in NOT_ALLOWED_FFMPEG_CHARS:
                if char in attr_value:
                    erase_attribute = True
                    erase_reason = (
                        "contains unsupported character \"{}\"."
                    ).format(char)
                    break

        if erase_attribute:
            # Set attribute to empty string
            logger.info((
                "Removed attribute \"{}\" from metadata because {}."
            ).format(attr_name, erase_reason))
            oiio_cmd.extend(["--eraseattrib", attr_name])

    # Add last argument - path to output
    if is_sequence:
        ext = os.path.splitext(first_input_path)[1]
        base_filename = "tmp.%{:0>2}d{}".format(
            len(str(input_frame_end)), ext
        )
    else:
        base_filename = os.path.basename(first_input_path)
    output_path = os.path.join(output_dir, base_filename)
    oiio_cmd.extend([
        "-o", output_path
    ])

    logger.debug("Conversion command: {}".format(" ".join(oiio_cmd)))
    run_subprocess(oiio_cmd, logger=logger)


def convert_input_paths_for_ffmpeg(
    input_paths,
    output_dir,
    logger=None
):
    """Convert source file to format supported in ffmpeg.

    Currently can convert only exrs. The input filepaths should be files
    with same type. Information about input is loaded only from first found
    file.

    Filenames of input files are kept so make sure that output directory
    is not the same directory as input files have.
    - This way it can handle gaps and can keep input filenames without handling
        frame template

    Args:
        input_paths (str): Paths that should be converted. It is expected that
            contains single file or image sequence of same type.
        output_dir (str): Path to directory where output will be rendered.
            Must not be same as input's directory.
        logger (logging.Logger): Logger used for logging.

    Raises:
        ValueError: If input filepath has extension not supported by function.
            Currently is supported only ".exr" extension.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    first_input_path = input_paths[0]
    ext = os.path.splitext(first_input_path)[1].lower()

    if ext != ".exr":
        raise ValueError((
            "Function 'convert_for_ffmpeg' currently support only"
            " \".exr\" extension. Got \"{}\"."
        ).format(ext))

    input_info = get_oiio_info_for_input(first_input_path, logger=logger)

    # Change compression only if source compression is "dwaa" or "dwab"
    #   - they're not supported in ffmpeg
    compression = input_info["attribs"].get("compression")
    if compression in ("dwaa", "dwab"):
        compression = "none"

    # Collect channels to export
    input_arg, channels_arg = get_oiio_input_and_channel_args(input_info)

    for input_path in input_paths:
        # Prepare subprocess arguments
        oiio_cmd = get_oiio_tool_args(
            "oiiotool",
            # Don't add any additional attributes
            "--nosoftwareattrib",
        )
        # Add input compression if available
        if compression:
            oiio_cmd.extend(["--compression", compression])

        oiio_cmd.extend([
            input_arg, input_path,
            # Tell oiiotool which channels should be put to top stack
            #   (and output)
            "--ch", channels_arg,
            # Use first subimage
            "--subimage", "0"
        ])

        for attr_name, attr_value in input_info["attribs"].items():
            if not isinstance(attr_value, str):
                continue

            # Remove attributes that have string value longer than allowed
            #   length for ffmpeg or when containing prohibited symbols
            erase_reason = "Missing reason"
            erase_attribute = False
            if len(attr_value) > MAX_FFMPEG_STRING_LEN:
                erase_reason = "has too long value ({} chars).".format(
                    len(attr_value)
                )
                erase_attribute = True

            if not erase_attribute:
                for char in NOT_ALLOWED_FFMPEG_CHARS:
                    if char in attr_value:
                        erase_attribute = True
                        erase_reason = (
                            "contains unsupported character \"{}\"."
                        ).format(char)
                        break

            if erase_attribute:
                # Set attribute to empty string
                logger.info((
                    "Removed attribute \"{}\" from metadata because {}."
                ).format(attr_name, erase_reason))
                oiio_cmd.extend(["--eraseattrib", attr_name])

        # Add last argument - path to output
        base_filename = os.path.basename(input_path)
        output_path = os.path.join(output_dir, base_filename)
        oiio_cmd.extend([
            "-o", output_path
        ])

        logger.debug("Conversion command: {}".format(" ".join(oiio_cmd)))
        run_subprocess(oiio_cmd, logger=logger)


# FFMPEG functions
def get_ffprobe_data(path_to_file, logger=None):
    """Load data about entered filepath via ffprobe.

    Args:
        path_to_file (str): absolute path
        logger (logging.Logger): injected logger, if empty new is created
    """
    if not logger:
        logger = logging.getLogger(__name__)
    logger.debug(
        "Getting information about input \"{}\".".format(path_to_file)
    )
    ffprobe_args = get_ffmpeg_tool_args("ffprobe")
    args = ffprobe_args + [
        "-hide_banner",
        "-loglevel", "fatal",
        "-show_error",
        "-show_format",
        "-show_streams",
        "-show_programs",
        "-show_chapters",
        "-show_private_data",
        "-print_format", "json",
        path_to_file
    ]

    logger.debug("FFprobe command: {}".format(
        subprocess.list2cmdline(args)
    ))
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if platform.system().lower() == "windows":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )

    popen = subprocess.Popen(args, **kwargs)

    popen_stdout, popen_stderr = popen.communicate()
    if popen_stdout:
        logger.debug("FFprobe stdout:\n{}".format(
            popen_stdout.decode("utf-8")
        ))

    if popen_stderr:
        logger.warning("FFprobe stderr:\n{}".format(
            popen_stderr.decode("utf-8")
        ))

    return json.loads(popen_stdout)


def get_ffprobe_streams(path_to_file, logger=None):
    """Load streams from entered filepath via ffprobe.

    Args:
        path_to_file (str): absolute path
        logger (logging.Logger): injected logger, if empty new is created
    """
    return get_ffprobe_data(path_to_file, logger)["streams"]


def get_ffmpeg_format_args(ffprobe_data, source_ffmpeg_cmd=None):
    """Copy format from input metadata for output.

    Args:
        ffprobe_data(dict): Data received from ffprobe.
        source_ffmpeg_cmd(str): Command that created input if available.
    """
    input_format = ffprobe_data.get("format") or {}
    if input_format.get("format_name") == "mxf":
        return _ffmpeg_mxf_format_args(ffprobe_data, source_ffmpeg_cmd)
    return []


def _ffmpeg_mxf_format_args(ffprobe_data, source_ffmpeg_cmd):
    input_format = ffprobe_data["format"]
    format_tags = input_format.get("tags") or {}
    operational_pattern_ul = format_tags.get("operational_pattern_ul") or ""
    output = []
    if operational_pattern_ul == "060e2b34.04010102.0d010201.10030000":
        output.extend(["-f", "mxf_opatom"])
    return output


def get_ffmpeg_codec_args(ffprobe_data, source_ffmpeg_cmd=None, logger=None):
    """Copy codec from input metadata for output.

    Args:
        ffprobe_data(dict): Data received from ffprobe.
        source_ffmpeg_cmd(str): Command that created input if available.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    video_stream = None
    no_audio_stream = None
    for stream in ffprobe_data["streams"]:
        codec_type = stream["codec_type"]
        if codec_type == "video":
            video_stream = stream
            break
        elif no_audio_stream is None and codec_type != "audio":
            no_audio_stream = stream

    if video_stream is None:
        if no_audio_stream is None:
            logger.warning(
                "Couldn't find stream that is not an audio file."
            )
            return []
        logger.info(
            "Didn't find video stream. Using first non audio stream."
        )
        video_stream = no_audio_stream

    codec_name = video_stream.get("codec_name")
    # Codec "prores"
    if codec_name == "prores":
        return _ffmpeg_prores_codec_args(video_stream, source_ffmpeg_cmd)

    # Codec "h264"
    if codec_name == "h264":
        return _ffmpeg_h264_codec_args(video_stream, source_ffmpeg_cmd)

    # Coded DNxHD
    if codec_name == "dnxhd":
        return _ffmpeg_dnxhd_codec_args(video_stream, source_ffmpeg_cmd)

    output = []
    if codec_name:
        output.extend(["-codec:v", codec_name])

    bit_rate = video_stream.get("bit_rate")
    if bit_rate:
        output.extend(["-b:v", bit_rate])

    pix_fmt = video_stream.get("pix_fmt")
    if pix_fmt:
        output.extend(["-pix_fmt", pix_fmt])

    output.extend(["-g", "1"])

    return output


def _ffmpeg_prores_codec_args(stream_data, source_ffmpeg_cmd):
    output = []

    tags = stream_data.get("tags") or {}
    encoder = tags.get("encoder") or ""
    if encoder.endswith("prores_ks"):
        codec_name = "prores_ks"

    elif encoder.endswith("prores_aw"):
        codec_name = "prores_aw"

    else:
        codec_name = "prores"

    output.extend(["-codec:v", codec_name])

    pix_fmt = stream_data.get("pix_fmt")
    if pix_fmt:
        output.extend(["-pix_fmt", pix_fmt])

    # Rest of arguments is prores_kw specific
    if codec_name == "prores_ks":
        codec_tag_to_profile_map = {
            "apco": "proxy",
            "apcs": "lt",
            "apcn": "standard",
            "apch": "hq",
            "ap4h": "4444",
            "ap4x": "4444xq"
        }
        codec_tag_str = stream_data.get("codec_tag_string")
        if codec_tag_str:
            profile = codec_tag_to_profile_map.get(codec_tag_str)
            if profile:
                output.extend(["-profile:v", profile])

    return output


def _ffmpeg_h264_codec_args(stream_data, source_ffmpeg_cmd):
    output = ["-codec:v", "h264"]

    # Use arguments from source if are available source arguments
    if source_ffmpeg_cmd:
        copy_args = (
            "-crf",
            "-b:v", "-vb",
            "-minrate", "-minrate:",
            "-maxrate", "-maxrate:",
            "-bufsize", "-bufsize:"
        )
        args = source_ffmpeg_cmd.split(" ")
        for idx, arg in enumerate(args):
            if arg in copy_args:
                output.extend([arg, args[idx + 1]])

    pix_fmt = stream_data.get("pix_fmt")
    if pix_fmt:
        output.extend(["-pix_fmt", pix_fmt])

    output.extend(["-intra", "-g", "1"])
    return output


def _ffmpeg_dnxhd_codec_args(stream_data, source_ffmpeg_cmd):
    output = ["-codec:v", "dnxhd"]

    # Use source profile (profiles in metadata are not usable in args directly)
    profile = stream_data.get("profile") or ""
    # Lower profile and replace space with underscore
    cleaned_profile = profile.lower().replace(" ", "_")

    # TODO validate this statement
    # Looks like using 'dnxhd' profile must have set bit rate and in that case
    #   should be used bitrate from source.
    # - related attributes 'bit_rate_defined', 'bit_rate_must_be_defined'
    bit_rate_must_be_defined = True
    dnx_profiles = {
        "dnxhd",
        "dnxhr_lb",
        "dnxhr_sq",
        "dnxhr_hq",
        "dnxhr_hqx",
        "dnxhr_444"
    }
    if cleaned_profile in dnx_profiles:
        if cleaned_profile != "dnxhd":
            bit_rate_must_be_defined = False
        output.extend(["-profile:v", cleaned_profile])

    pix_fmt = stream_data.get("pix_fmt")
    if pix_fmt:
        output.extend(["-pix_fmt", pix_fmt])

    # Use arguments from source if are available source arguments
    bit_rate_defined = False
    if source_ffmpeg_cmd:
        # Define bitrate arguments
        bit_rate_args = ("-b:v", "-vb",)
        # Separate the two variables in case something else should be copied
        #   from source command
        copy_args = []
        copy_args.extend(bit_rate_args)

        args = source_ffmpeg_cmd.split(" ")
        for idx, arg in enumerate(args):
            if arg in copy_args:
                if arg in bit_rate_args:
                    bit_rate_defined = True
                output.extend([arg, args[idx + 1]])

    # Add bitrate if needed
    if bit_rate_must_be_defined and not bit_rate_defined:
        src_bit_rate = stream_data.get("bit_rate")
        if src_bit_rate:
            output.extend(["-b:v", src_bit_rate])

    output.extend(["-g", "1"])
    return output


def convert_ffprobe_fps_value(str_value):
    """Returns (str) value of fps from ffprobe frame format (120/1)"""
    if str_value == "0/0":
        print("WARNING: Source has \"r_frame_rate\" value set to \"0/0\".")
        return "Unknown"

    items = str_value.split("/")
    if len(items) == 1:
        fps = float(items[0])

    elif len(items) == 2:
        fps = float(items[0]) / float(items[1])

    # Check if fps is integer or float number
    if int(fps) == fps:
        fps = int(fps)

    return str(fps)


def convert_ffprobe_fps_to_float(value):
    """Convert string value of frame rate to float.

    Copy of 'convert_ffprobe_fps_value' which raises exceptions on invalid
    value, does not convert value to string and does not return "Unknown"
    string.

    Args:
        value (str): Value to be converted.

    Returns:
        Float: Converted frame rate in float. If divisor in value is '0' then
            '0.0' is returned.

    Raises:
        ValueError: Passed value is invalid for conversion.
    """

    if not value:
        raise ValueError("Got empty value.")

    items = value.split("/")
    if len(items) == 1:
        return float(items[0])

    if len(items) > 2:
        raise ValueError((
            "FPS expression contains multiple dividers \"{}\"."
        ).format(value))

    dividend = float(items.pop(0))
    divisor = float(items.pop(0))
    if divisor == 0.0:
        return 0.0
    return dividend / divisor


def convert_colorspace(
    input_path,
    output_path,
    config_path,
    source_colorspace,
    target_colorspace=None,
    view=None,
    display=None,
    additional_command_args=None,
    logger=None,
):
    """Convert source file from one color space to another.

    Args:
        input_path (str): Path that should be converted. It is expected that
            contains single file or image sequence of same type
            (sequence in format 'file.FRAMESTART-FRAMEEND#.ext', see oiio docs,
            eg `big.1-3#.tif`)
        output_path (str): Path to output filename.
            (must follow format of 'input_path', eg. single file or
             sequence in 'file.FRAMESTART-FRAMEEND#.ext', `output.1-3#.tif`)
        config_path (str): path to OCIO config file
        source_colorspace (str): ocio valid color space of source files
        target_colorspace (str): ocio valid target color space
                    if filled, 'view' and 'display' must be empty
        view (str): name for viewer space (ocio valid)
            both 'view' and 'display' must be filled (if 'target_colorspace')
        display (str): name for display-referred reference space (ocio valid)
            both 'view' and 'display' must be filled (if 'target_colorspace')
        additional_command_args (list): arguments for oiiotool (like binary
            depth for .dpx)
        logger (logging.Logger): Logger used for logging.
    Raises:
        ValueError: if misconfigured
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    input_info = get_oiio_info_for_input(input_path, logger=logger)

    # Collect channels to export
    input_arg, channels_arg = get_oiio_input_and_channel_args(input_info)

    # Prepare subprocess arguments
    oiio_cmd = get_oiio_tool_args(
        "oiiotool",
        # Don't add any additional attributes
        "--nosoftwareattrib",
        "--colorconfig", config_path
    )

    oiio_cmd.extend([
        input_arg, input_path,
        # Tell oiiotool which channels should be put to top stack
        #   (and output)
        "--ch", channels_arg,
        # Use first subimage
        "--subimage", "0"
    ])

    if all([target_colorspace, view, display]):
        raise ValueError("Colorspace and both screen and display"
                         " cannot be set together."
                         "Choose colorspace or screen and display")
    if not target_colorspace and not all([view, display]):
        raise ValueError("Both screen and display must be set.")

    if additional_command_args:
        oiio_cmd.extend(additional_command_args)

    if target_colorspace:
        oiio_cmd.extend(["--colorconvert",
                         source_colorspace,
                         target_colorspace])
    if view and display:
        oiio_cmd.extend(["--iscolorspace", source_colorspace])
        oiio_cmd.extend(["--ociodisplay", display, view])

    oiio_cmd.extend(["-o", output_path])

    logger.debug("Conversion command: {}".format(" ".join(oiio_cmd)))
    run_subprocess(oiio_cmd, logger=logger)


def split_cmd_args(in_args):
    """Makes sure all entered arguments are separated in individual items.

    Split each argument string with " -" to identify if string contains
    one or more arguments.
    Args:
        in_args (list): of arguments ['-n', '-d uint10']
    Returns
        (list): ['-n', '-d', 'unint10']
    """
    splitted_args = []
    for arg in in_args:
        if not arg.strip():
            continue
        splitted_args.extend(arg.split(" "))
    return splitted_args


def get_rescaled_command_arguments(
        application,
        input_path,
        target_width,
        target_height,
        target_par=None,
        bg_color=None,
        log=None
):
    """Get command arguments for rescaling input to target size.

    Args:
        application (str): Application for which command should be created.
            Currently supported are "ffmpeg" and "oiiotool".
        input_path (str): Path to input file.
        target_width (int): Width of target.
        target_height (int): Height of target.
        target_par (Optional[float]): Pixel aspect ratio of target.
        bg_color (Optional[list[int]]): List of 8bit int values for
            background color. Should be in range 0 - 255.
        log (Optional[logging.Logger]): Logger used for logging.

    Returns:
        list[str]: List of command arguments.
    """
    command_args = []
    target_par = target_par or 1.0
    input_par = 1.0

    input_height, input_width, stream_input_par = _get_image_dimensions(
        application, input_path, log)
    if stream_input_par:
        input_par = (
            float(stream_input_par.split(":")[0])
            / float(stream_input_par.split(":")[1])
        )
    # recalculating input and target width
    input_width = int(input_width * input_par)
    target_width = int(target_width * target_par)

    # calculate aspect ratios
    target_aspect = float(target_width) / target_height
    input_aspect = float(input_width) / input_height

    # calculate scale size
    scale_size = float(input_width) / target_width
    if input_aspect < target_aspect:
        scale_size = float(input_height) / target_height

    # calculate rescaled width and height
    rescaled_width = int(input_width / scale_size)
    rescaled_height = int(input_height / scale_size)

    # calculate width and height shift
    rescaled_width_shift = int((target_width - rescaled_width) / 2)
    rescaled_height_shift = int((target_height - rescaled_height) / 2)

    if application == "ffmpeg":
        # create scale command
        scale = "scale={0}:{1}".format(input_width, input_height)
        pad = "pad={0}:{1}:({2}-iw)/2:({3}-ih)/2".format(
            target_width,
            target_height,
            target_width,
            target_height
        )
        if input_width > target_width or input_height > target_height:
            scale = "scale={0}:{1}".format(rescaled_width, rescaled_height)
            pad = "pad={0}:{1}:{2}:{3}".format(
                target_width,
                target_height,
                rescaled_width_shift,
                rescaled_height_shift
            )

        if bg_color:
            color = convert_color_values(application, bg_color)
            pad += ":{0}".format(color)
        command_args.extend(["-vf", "{0},{1}".format(scale, pad)])

    elif application == "oiiotool":
        input_info = get_oiio_info_for_input(input_path, logger=log)
        # Collect channels to export
        _, channels_arg = get_oiio_input_and_channel_args(
            input_info, alpha_default=1.0)

        command_args.extend([
            # Tell oiiotool which channels should be put to top stack
            #   (and output)
            "--ch", channels_arg,
            # Use first subimage
            "--subimage", "0"
        ])

        if input_par != 1.0:
            command_args.extend(["--pixelaspect", "1"])

        width_shift = int((target_width - input_width) / 2)
        height_shift = int((target_height - input_height) / 2)

        # default resample is not scaling source image
        resample = [
            "--resize",
            "{0}x{1}".format(input_width, input_height),
            "--origin",
            "+{0}+{1}".format(width_shift, height_shift),
        ]
        # scaled source image to target size
        if input_width > target_width or input_height > target_height:
            # form resample command
            resample = [
                "--resize:filter=lanczos3",
                "{0}x{1}".format(rescaled_width, rescaled_height),
                "--origin",
                "+{0}+{1}".format(rescaled_width_shift, rescaled_height_shift),
            ]
        command_args.extend(resample)

        fullsize = [
            "--fullsize",
            "{0}x{1}".format(target_width, target_height)
        ]
        if bg_color:
            color = convert_color_values(application, bg_color)

            fullsize.extend([
                "--pattern",
                "constant:color={0}".format(color),
                "{0}x{1}".format(target_width, target_height),
                "4",  # 4 channels
                "--over"
            ])
        command_args.extend(fullsize)

    else:
        raise ValueError(
            "\"application\" input argument should "
            "be either \"ffmpeg\" or \"oiiotool\""
        )

    return command_args


def _get_image_dimensions(application, input_path, log):
    """Uses 'ffprobe' first and then 'oiiotool' if available to get dim.

    Args:
        application (str): "oiiotool"|"ffmpeg"
        input_path (str): path to image file
        log (Optional[logging.Logger]): Logger used for logging.
    Returns:
        (tuple) (int, int, dict) - (height, width, sample_aspect_ratio)
    Raises:
        RuntimeError if image dimensions couldn't be parsed out.
    """
    # ffmpeg command
    input_file_metadata = get_ffprobe_data(input_path, logger=log)
    input_width = input_height = 0
    stream = next(
        (
            s for s in input_file_metadata["streams"]
            if s.get("codec_type") == "video"
        ),
        {}
    )
    if stream:
        input_width = int(stream["width"])
        input_height = int(stream["height"])

    # fallback for weird files with width=0, height=0
    if (input_width == 0 or input_height == 0) and application == "oiiotool":
        # Load info about file from oiio tool
        input_info = get_oiio_info_for_input(input_path, logger=log)
        if input_info:
            input_width = int(input_info["width"])
            input_height = int(input_info["height"])

    if input_width == 0 or input_height == 0:
        raise RuntimeError("Couldn't read {} either "
                           "with ffprobe or oiiotool".format(input_path))

    stream_input_par = stream.get("sample_aspect_ratio")
    return input_height, input_width, stream_input_par


def convert_color_values(application, color_value):
    """Get color mapping for ffmpeg and oiiotool.
    Args:
        application (str): Application for which command should be created.
        color_value (list[int]): List of 8bit int values for RGBA.
    Returns:
        str: ffmpeg returns hex string, oiiotool is string with floats.
    """
    red, green, blue, alpha = color_value

    if application == "ffmpeg":
        return "{0:0>2X}{1:0>2X}{2:0>2X}@{3}".format(
            red, green, blue, (alpha / 255.0)
        )
    elif application == "oiiotool":
        red = float(red / 255)
        green = float(green / 255)
        blue = float(blue / 255)
        alpha = float(alpha / 255)

        return "{0:.3f},{1:.3f},{2:.3f},{3:.3f}".format(
            red, green, blue, alpha)
    else:
        raise ValueError(
            "\"application\" input argument should "
            "be either \"ffmpeg\" or \"oiiotool\""
        )


def get_oiio_input_and_channel_args(oiio_input_info, alpha_default=None):
    """Get input and channel arguments for oiiotool.
    Args:
        oiio_input_info (dict): Information about input from oiio tool.
            Should be output of function `get_oiio_info_for_input`.
        alpha_default (float, optional): Default value for alpha channel.
    Returns:
        tuple[str, str]: Tuple of input and channel arguments.
    """
    channel_names = oiio_input_info["channelnames"]
    review_channels = get_convert_rgb_channels(channel_names)

    if review_channels is None:
        raise ValueError(
            "Couldn't find channels that can be used for conversion."
        )

    red, green, blue, alpha = review_channels
    input_channels = [red, green, blue]

    channels_arg = "R={0},G={1},B={2}".format(red, green, blue)
    if alpha is not None:
        channels_arg += ",A={}".format(alpha)
        input_channels.append(alpha)
    elif alpha_default:
        channels_arg += ",A={}".format(float(alpha_default))
        input_channels.append("A")

    input_channels_str = ",".join(input_channels)

    subimages = oiio_input_info.get("subimages")
    input_arg = "-i"
    if subimages is None or subimages == 1:
        # Tell oiiotool which channels should be loaded
        # - other channels are not loaded to memory so helps to avoid memory
        #       leak issues
        # - this option is crashing if used on multipart exrs
        input_arg += ":ch={}".format(input_channels_str)

    return input_arg, channels_arg
