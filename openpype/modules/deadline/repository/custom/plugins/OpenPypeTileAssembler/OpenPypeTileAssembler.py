# -*- coding: utf-8 -*-
"""Tile Assembler Plugin using Open Image IO tool.

Todo:
    Currently we support only EXRs with their data window set.
"""
import os
import re
import subprocess
import xml.etree.ElementTree

from System.IO import Path

from Deadline.Plugins import DeadlinePlugin
from Deadline.Scripting import (
    FileUtils, RepositoryUtils, SystemUtils)


version_major = 1
version_minor = 0
version_patch = 0
version_string = "{}.{}.{}".format(version_major, version_minor, version_patch)
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


def convert_value_by_type_name(value_type, value):
    """Convert value to proper type based on type name.

    In some cases value types have custom python class.
    """

    # Simple types
    if value_type == "string":
        return value

    if value_type == "int":
        return int(value)

    if value_type == "float":
        return float(value)

    # Vectors will probably have more types
    if value_type in ("vec2f", "float2"):
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
            divisor = 3
        elif parts_len == 16:
            divisor = 4
        else:
            print("Unknown matrix resolution {}. Value: \"{}\"".format(
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
        parts = value.split("/")
        top = float(parts[0])
        bottom = 1.0
        if len(parts) != 1:
            bottom = float(parts[1])
        return float(top) / float(bottom)

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
                convert_value_by_type_name(array_type, item)
            )
        return output

    print((
        "Dev note (missing implementation):"
        " Unknown attrib type \"{}\". Value: {}"
    ).format(value_type, value))
    return value


def parse_oiio_xml_output(xml_string):
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

    tree = xml.etree.ElementTree.fromstring(xml_string)
    attribs = {}
    output["attribs"] = attribs
    for child in tree:
        tag_name = child.tag
        if tag_name == "attrib":
            attrib_def = child.attrib
            value = convert_value_by_type_name(
                attrib_def["type"], child.text
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
            print((
                "Dev note (missing implementation):"
                " Unknown tag \"{}\". Value \"{}\""
            ).format(tag_name, value))

        output[child.tag] = value

    return output


def info_about_input(oiiotool_path, filepath):
    args = [
        oiiotool_path,
        "--info",
        "-v",
        "-i:infoformat=xml",
        filepath
    ]
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    _stdout, _stderr = popen.communicate()
    output = ""
    if _stdout:
        output += _stdout.decode("utf-8", errors="backslashreplace")

    if _stderr:
        output += _stderr.decode("utf-8", errors="backslashreplace")

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
    return parse_oiio_xml_output(xml_text)


def GetDeadlinePlugin():  # noqa: N802
    """Helper."""
    return OpenPypeTileAssembler()


def CleanupDeadlinePlugin(deadlinePlugin):  # noqa: N802, N803
    """Helper."""
    deadlinePlugin.cleanup()


class OpenPypeTileAssembler(DeadlinePlugin):
    """Deadline plugin for assembling tiles using OIIO."""

    def __init__(self):
        """Init."""
        self.InitializeProcessCallback += self.initialize_process
        self.RenderExecutableCallback += self.render_executable
        self.RenderArgumentCallback += self.render_argument
        self.PreRenderTasksCallback += self.pre_render_tasks
        self.PostRenderTasksCallback += self.post_render_tasks

    def cleanup(self):
        """Cleanup function."""
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
        del self.PreRenderTasksCallback
        del self.PostRenderTasksCallback

    def initialize_process(self):
        """Initialization."""
        self.LogInfo("Plugin version: {}".format(version_string))
        self.SingleFramesOnly = True
        self.StdoutHandling = True
        self.renderer = self.GetPluginInfoEntryWithDefault(
            "Renderer", "undefined")
        self.AddStdoutHandlerCallback(
            ".*Error.*").HandleCallback += self.handle_stdout_error

    def render_executable(self):
        """Get render executable name.

        Get paths from plugin configuration, find executable and return it.

        Returns:
            (str): Render executable.

        """
        oiiotool_exe_list = self.GetConfigEntry("OIIOTool_RenderExecutable")
        oiiotool_exe = FileUtils.SearchFileList(oiiotool_exe_list)

        if oiiotool_exe == "":
            self.FailRender(("No file found in the semicolon separated "
                             "list \"{}\". The path to the render executable "
                             "can be configured from the Plugin Configuration "
                             "in the Deadline Monitor.").format(
                                oiiotool_exe_list))

        return oiiotool_exe

    def render_argument(self):
        """Generate command line arguments for render executable.

        Returns:
            (str): arguments to add to render executable.

        """
        # Read tile config file. This file is in compatible format with
        # Draft Tile Assembler
        data = {}
        with open(self.config_file, "rU") as f:
            for text in f:
                # Parsing key-value pair and removing white-space
                # around the entries
                info = [x.strip() for x in text.split("=", 1)]

                if len(info) > 1:
                    try:
                        data[str(info[0])] = info[1]
                    except Exception as e:
                        # should never be called
                        self.FailRender(
                            "Cannot parse config file: {}".format(e))

        # Get output file. We support only EXRs now.
        output_file = data["ImageFileName"]
        output_file = RepositoryUtils.CheckPathMapping(output_file)
        output_file = self.process_path(output_file)

        tile_info = []
        for tile in range(int(data["TileCount"])):
            tile_info.append({
                "filepath": data["Tile{}".format(tile)],
                "pos_x": int(data["Tile{}X".format(tile)]),
                "pos_y": int(data["Tile{}Y".format(tile)]),
                "height": int(data["Tile{}Height".format(tile)]),
                "width": int(data["Tile{}Width".format(tile)])
            })

        arguments = self.tile_oiio_args(
            int(data["ImageWidth"]), int(data["ImageHeight"]),
            tile_info, output_file)
        self.LogInfo(
            "Using arguments: {}".format(" ".join(arguments)))
        self.tiles = tile_info
        return " ".join(arguments)

    def process_path(self, filepath):
        """Handle slashes in file paths."""
        if SystemUtils.IsRunningOnWindows():
            filepath = filepath.replace("/", "\\")
            if filepath.startswith("\\") and not filepath.startswith("\\\\"):
                filepath = "\\" + filepath
        else:
            filepath = filepath.replace("\\", "/")
        return filepath

    def pre_render_tasks(self):
        """Load config file and do remapping."""
        self.LogInfo("OpenPype Tile Assembler starting...")
        config_file = self.GetPluginInfoEntry("ConfigFile")

        temp_scene_directory = self.CreateTempDirectory(
            "thread" + str(self.GetThreadNumber()))
        temp_scene_filename = Path.GetFileName(config_file)
        self.config_file = Path.Combine(
            temp_scene_directory, temp_scene_filename)

        if SystemUtils.IsRunningOnWindows():
            RepositoryUtils.CheckPathMappingInFileAndReplaceSeparator(
                config_file, self.config_file, "/", "\\")
        else:
            RepositoryUtils.CheckPathMappingInFileAndReplaceSeparator(
                config_file, self.config_file, "\\", "/")
            os.chmod(self.config_file, os.stat(self.config_file).st_mode)

    def post_render_tasks(self):
        """Cleanup tiles if required."""
        if self.GetBooleanPluginInfoEntryWithDefault("CleanupTiles", False):
            self.LogInfo("Cleaning up Tiles...")
            for tile in self.tiles:
                try:
                    self.LogInfo("Deleting: {}".format(tile["filepath"]))
                    os.remove(tile["filepath"])
                    # By this time we would have errored out
                    # if error on missing was enabled
                except KeyError:
                    pass
                except OSError:
                    self.LogInfo("Failed to delete: {}".format(
                        tile["filepath"]))
                    pass

        self.LogInfo("OpenPype Tile Assembler Job finished.")

    def handle_stdout_error(self):
        """Handle errors in stdout."""
        self.FailRender(self.GetRegexMatch(0))

    def tile_oiio_args(
            self, output_width, output_height, tile_info, output_path):
        """Generate oiio tool arguments for tile assembly.

        Args:
            output_width (int): Width of output image.
            output_height (int): Height of output image.
            tiles_info (list): List of tile items, each item must be
                dictionary with `filepath`, `pos_x` and `pos_y` keys
                representing path to file and x, y coordinates on output
                image where top-left point of tile item should start.
            output_path (str): Path to file where should be output stored.

        Returns:
            (list): oiio tools arguments.

        """
        args = []

        # Create new image with output resolution, and with same type and
        # channels as input
        oiiotool_path = self.render_executable()
        first_tile_path = tile_info[0]["filepath"]
        first_tile_info = info_about_input(oiiotool_path, first_tile_path)
        create_arg_template = "--create{} {}x{} {}"

        image_type = ""
        image_format = first_tile_info.get("format")
        if image_format:
            image_type = ":type={}".format(image_format)

        create_arg = create_arg_template.format(
            image_type, output_width,
            output_height, first_tile_info["nchannels"]
        )
        args.append(create_arg)

        for tile in tile_info:
            path = tile["filepath"]
            pos_x = tile["pos_x"]
            tile_height = info_about_input(oiiotool_path, path)["height"]
            if self.renderer == "vray":
                pos_y = tile["pos_y"]
            else:
                pos_y = output_height - tile["pos_y"] - tile_height

            # Add input path and make sure inputs origin is 0, 0
            args.append(path)
            args.append("--origin +0+0")
            # Swap to have input as foreground
            args.append("--swap")
            # Paste foreground to background
            args.append("--paste {x:+d}{y:+d}".format(x=pos_x, y=pos_y))

        args.append("-o")
        args.append(output_path)

        return args
