import os
import re
import logging
import json
import collections
import tempfile
import subprocess

import xml.etree.ElementTree

from .execute import run_subprocess
from .vendor_bin_utils import (
    get_ffmpeg_tool_path,
    get_oiio_tools_path,
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


def get_transcode_temp_directory():
    """Creates temporary folder for transcoding.

    Its local, in case of farm it is 'local' to the farm machine.

    Should be much faster, needs to be cleaned up later.
    """
    return os.path.normpath(
        tempfile.mkdtemp(prefix="op_transcoding_")
    )


def get_oiio_info_for_input(filepath, logger=None):
    """Call oiiotool to get information about input and return stdout.

    Stdout should contain xml format string.
    """
    args = [
        get_oiio_tools_path(), "--info", "-v", "-i:infoformat=xml", filepath
    ]
    output = run_subprocess(args, logger=logger)
    output = output.replace("\r\n", "\n")

    xml_started = False
    lines = []
    for line in output.split("\n"):
        if not xml_started:
            if not line.startswith("<"):
                continue
            xml_started = True
        if xml_started:
            lines.append(line)

    if not xml_started:
        raise ValueError(
            "Failed to read input file \"{}\".\nOutput:\n{}".format(
                filepath, output
            )
        )

    xml_text = "\n".join(lines)
    return parse_oiio_xml_output(xml_text, logger=logger)


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

    if value_type == "float":
        return float(value)

    # Vectors will probably have more types
    if value_type == "vec2f":
        return [float(item) for item in value.split(",")]

    # Matrix should be always have square size of element 3x3, 4x4
    # - are returned as list of lists
    if value_type == "matrix":
        output = []
        current_index = -1
        parts = value.split(",")
        parts_len = len(parts)
        if parts_len == 1:
            divisor = 1
        elif parts_len == 4:
            divisor = 2
        elif parts_len == 9:
            divisor == 3
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

    if value_type == "vector":
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

    logger.info((
        "MISSING IMPLEMENTATION:"
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
            logger.info((
                "MISSING IMPLEMENTATION:"
                " Unknown tag \"{}\". Value \"{}\""
            ).format(tag_name, value))

        output[child.tag] = value

    return output


def get_convert_rgb_channels(channel_names):
    """Get first available RGB(A) group from channels info.

    ## Examples
    ```
    # Ideal situation
    channels_info: [
        "R", "G", "B", "A"
    }
    ```
    Result will be `("R", "G", "B", "A")`

    ```
    # Not ideal situation
    channels_info: [
        "beauty.red",
        "beuaty.green",
        "beauty.blue",
        "depth.Z"
    ]
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
    for channel_name in channel_names:
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
    input_info = get_oiio_info_for_input(src_filepath)
    if not input_info:
        return None

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

    input_info = get_oiio_info_for_input(first_input_path)

    # Change compression only if source compression is "dwaa" or "dwab"
    #   - they're not supported in ffmpeg
    compression = input_info["attribs"].get("compression")
    if compression in ("dwaa", "dwab"):
        compression = "none"

    # Prepare subprocess arguments
    oiio_cmd = [
        get_oiio_tools_path(),

        # Don't add any additional attributes
        "--nosoftwareattrib",
    ]
    # Add input compression if available
    if compression:
        oiio_cmd.extend(["--compression", compression])

    # Collect channels to export
    channel_names = input_info["channelnames"]
    review_channels = get_convert_rgb_channels(channel_names)
    if review_channels is None:
        raise ValueError(
            "Couldn't find channels that can be used for conversion."
        )

    red, green, blue, alpha = review_channels
    input_channels = [red, green, blue]
    channels_arg = "R={},G={},B={}".format(red, green, blue)
    if alpha is not None:
        channels_arg += ",A={}".format(alpha)
        input_channels.append(alpha)
    input_channels_str = ",".join(input_channels)

    oiio_cmd.extend([
        # Tell oiiotool which channels should be loaded
        # - other channels are not loaded to memory so helps to avoid memory
        #       leak issues
        "-i:ch={}".format(input_channels_str), first_input_path,
        # Tell oiiotool which channels should be put to top stack (and output)
        "--ch", channels_arg
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
        #   for ffmpeg or when containt unallowed symbols
        erase_reason = "Missing reason"
        erase_attribute = False
        if len(attr_value) > MAX_FFMPEG_STRING_LEN:
            erase_reason = "has too long value ({} chars).".format(
                len(attr_value)
            )

        if erase_attribute:
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
    """Contert source file to format supported in ffmpeg.

    Currently can convert only exrs. The input filepaths should be files
    with same type. Information about input is loaded only from first found
    file.

    Filenames of input files are kept so make sure that output directory
    is not the same directory as input files have.
    - This way it can handle gaps and can keep input filenames without handling
        frame template

    Args:
        input_paths (str): Paths that should be converted. It is expected that
            contains single file or image sequence of samy type.
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

    input_info = get_oiio_info_for_input(first_input_path)

    # Change compression only if source compression is "dwaa" or "dwab"
    #   - they're not supported in ffmpeg
    compression = input_info["attribs"].get("compression")
    if compression in ("dwaa", "dwab"):
        compression = "none"

    # Collect channels to export
    channel_names = input_info["channelnames"]
    review_channels = get_convert_rgb_channels(channel_names)
    if review_channels is None:
        raise ValueError(
            "Couldn't find channels that can be used for conversion."
        )

    red, green, blue, alpha = review_channels
    input_channels = [red, green, blue]
    channels_arg = "R={},G={},B={}".format(red, green, blue)
    if alpha is not None:
        channels_arg += ",A={}".format(alpha)
        input_channels.append(alpha)
    input_channels_str = ",".join(input_channels)

    for input_path in input_paths:
        # Prepare subprocess arguments
        oiio_cmd = [
            get_oiio_tools_path(),

            # Don't add any additional attributes
            "--nosoftwareattrib",
        ]
        # Add input compression if available
        if compression:
            oiio_cmd.extend(["--compression", compression])

        oiio_cmd.extend([
            # Tell oiiotool which channels should be loaded
            # - other channels are not loaded to memory so helps to
            #       avoid memory leak issues
            "-i:ch={}".format(input_channels_str), input_path,
            # Tell oiiotool which channels should be put to top stack
            #   (and output)
            "--ch", channels_arg
        ])

        for attr_name, attr_value in input_info["attribs"].items():
            if not isinstance(attr_value, str):
                continue

            # Remove attributes that have string value longer than allowed
            #   length for ffmpeg or when containt unallowed symbols
            erase_reason = "Missing reason"
            erase_attribute = False
            if len(attr_value) > MAX_FFMPEG_STRING_LEN:
                erase_reason = "has too long value ({} chars).".format(
                    len(attr_value)
                )

            if erase_attribute:
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
    logger.info(
        "Getting information about input \"{}\".".format(path_to_file)
    )
    args = [
        get_ffmpeg_tool_path("ffprobe"),
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
    popen = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

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
    product_name = format_tags.get("product_name") or ""
    output = []
    if "opatom" in product_name.lower():
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

    output.extend(["-intra"])
    output.extend(["-g", "1"])

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
        # Seprate the two variables in case something else should be copied
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
