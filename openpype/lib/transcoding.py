import os
import re
import logging
import collections
import tempfile

import xml.etree.ElementTree

from .execute import run_subprocess
from .vendor_bin_utils import (
    get_oiio_tools_path,
    is_oiio_supported
)

# Max length of string that is supported by ffmpeg
MAX_FFMPEG_STRING_LEN = 8196
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
        if (
            isinstance(attr_value, str)
            and len(attr_value) > MAX_FFMPEG_STRING_LEN
        ):
            return True
    return False


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
    oiio_cmd = [get_oiio_tools_path()]
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

    ignore_attr_changes_added = False
    for attr_name, attr_value in input_info["attribs"].items():
        if not isinstance(attr_value, str):
            continue

        # Remove attributes that have string value longer than allowed length
        #   for ffmpeg
        if len(attr_value) > MAX_FFMPEG_STRING_LEN:
            if not ignore_attr_changes_added:
                # Attrite changes won't be added to attributes itself
                ignore_attr_changes_added = True
                oiio_cmd.append("--sansattrib")
            # Set attribute to empty string
            logger.info((
                "Removed attribute \"{}\" from metadata"
                " because has too long value ({} chars)."
            ).format(attr_name, len(attr_value)))
            oiio_cmd.extend(["--eraseattrib", attr_name])

    # Add last argument - path to output
    base_file_name = os.path.basename(first_input_path)
    output_path = os.path.join(output_dir, base_file_name)
    oiio_cmd.extend([
        "-o", output_path
    ])

    logger.debug("Conversion command: {}".format(" ".join(oiio_cmd)))
    run_subprocess(oiio_cmd, logger=logger)
