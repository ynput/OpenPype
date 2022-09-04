# -*- coding: utf-8 -*-
"""Tile Assembler Plugin using Open Image IO tool.

Todo:
    Currently we support only EXRs with their data window set.
"""
import os
import subprocess
import shutil

from System.IO import Path
from Deadline.Plugins import (
    DeadlinePlugin,
    PluginType,
)
from Deadline.Scripting import (
    FileUtils,
    RepositoryUtils,
    SystemUtils
)


def GetDeadlinePlugin():  # noqa: N802
    """Helper."""
    return OpenPypeTileAssembler()


def CleanupDeadlinePlugin(deadlinePlugin):  # noqa: N802, N803
    """Helper."""
    deadlinePlugin.cleanup()


class OpenPypeTileAssembler(DeadlinePlugin):
    """Deadline plugin for assembling tiles using OIIO."""

    def __init__(self):
        self.InitializeProcessCallback += self._init_process
        self.StartJobCallback += self._start_job
        self.RenderTasksCallback += self._render_tasks

    def cleanup(self):
        """Clean up the plugin."""
        del self.InitializeProcessCallback
        del self.StartJobCallback
        del self.RenderTasksCallback
        del self.EndJobCallback

    def _init_process(self):
        """Called by Deadline to initialize the process."""
        # Set the plugin specific settings.
        self.SingleFramesOnly = True
        self.PluginType = PluginType.Advanced

        self._renderer = self.GetPluginInfoEntryWithDefault(
            "Renderer", "undefined"
        )

    def _start_job(self):
        """Called by Deadline when the job starts."""
        self.LogInfo("OpenPype Tile Assembler starting...")

    def _render_tasks(self):
        """Called by Deadline for each task the Worker renders."""
        # Do something to interact with the running process.
        self.LogInfo("In renderer is \"{}\"".format(self._renderer))

        try:
            data = self._load_config_data()
        except Exception as exc:
            self.FailRender("Cannot parse config file: {}".format(exc))

        output_file = data["ImageFileName"]
        output_file = RepositoryUtils.CheckPathMapping(output_file)
        output_file = self._convert_path(output_file)

        width = int(data["ImageWidth"])
        height = int(data["ImageHeight"])
        tiles_cropped_str = data.get("TilesCropped") or ""
        tiles_cropped = None
        if tiles_cropped_str.lower() == "false":
            tiles_cropped = False
        elif tiles_cropped_str.lower() == "true":
            tiles_cropped = True

        tiles_info = []
        for tile_idx in range(int(data["TileCount"])):
            tiles_info.append({
                "filepath": data["Tile{}".format(tile_idx)],
                "pos_x": int(data["Tile{}X".format(tile_idx)]),
                "pos_y": int(data["Tile{}Y".format(tile_idx)]),
                "height": int(data["Tile{}Height".format(tile_idx)]),
                "width": int(data["Tile{}Width".format(tile_idx)])
            })

        if not tiles_info:
            self.FailRender("Tiles cound are set to '0' tiles!")

        self._assembly_tiles(
            tiles_info, output_file, height, width, tiles_cropped
        )

    def _assembly_tiles(
        self, tiles_info, output_file, height, width, tiles_cropped
    ):
        executable = self._render_executable()
        startup_dir = os.path.dirname(executable)

        self.LogInfo("Rendering to \"{}\"".format(output_file))
        output_file_extless, ext = os.path.splitext(output_file)
        tmp_output_file = output_file_extless + "_" + ext
        last_idx = len(tiles_info)
        first_tile = tiles_info[0]
        first_filepath = first_tile["filepath"]
        self.LogInfo("Creating initial file \"{}\"".format(output_file))
        if not tiles_cropped:
            shutil.copy(first_filepath, output_file)
        else:
            tile_width = first_tile["width"]
            tile_height = first_tile["height"]
            pos_x = first_tile["pos_x"]
            pos_y = first_tile["pos_y"]
            args = [
                "--nosoftwareattrib",
                first_filepath,
                "--cut", "{}x{}+{}+{}".format(
                    width, height, pos_x, pos_y
                ),
                "-o", output_file
            ]
            arguments = subprocess.list2cmdline(args)
            returncode = self.RunProcess(
                executable, arguments, startup_dir, -1
            )
            if returncode != 0:
                self.FailRender("Failed to create initial file \"{}\"".format(
                    output_file
                ))

        for tile_idx, tile_info in enumerate(tiles_info):
            self.SetProgress(tile_idx / last_idx)
            filepath = tile_info["filepath"]
            tile_width = tile_info["width"]
            tile_height = tile_info["height"]
            pos_x = tile_info["pos_x"]
            pos_y = tile_info["pos_y"]

            args = [
                "--nosoftwareattrib",
                output_file,
                filepath
            ]
            if tiles_cropped:
                args.extend(["--origin", "+0+0"])
            else:
                args.extend(["--cut", "{},{},{},{}".format(
                    pos_x,
                    pos_y,
                    (pos_x + tile_width) - 1,
                    (pos_y + tile_height) - 1
                )])

            args.extend([
                "--swap",
                "--paste", "+{}+{}".format(pos_x, pos_y),
                "-o", tmp_output_file
            ])
            arguments = subprocess.list2cmdline(args)
            self.LogInfo("Creating tile {}/{}".format(tile_idx + 1, last_idx))
            returncode = self.RunProcess(
                executable, arguments, startup_dir, -1
            )
            if returncode != 0:
                if os.path.exists(tmp_output_file):
                    os.remove(tmp_output_file)
                self.FailRender(
                    "Failed to run {} {}".format(executable, arguments)
                )
            os.remove(output_file)
            os.rename(tmp_output_file, output_file)

    def _load_config_data(self):
        scene_filename = self.GetDataFilename()
        temp_scene_directory = self.CreateTempDirectory(
            "thread" + str(self.GetThreadNumber())
        )
        temp_scene_filename = Path.GetFileName(scene_filename)
        config_file = Path.Combine(
            temp_scene_directory, temp_scene_filename
        )

        if SystemUtils.IsRunningOnWindows():
            RepositoryUtils.CheckPathMappingInFileAndReplaceSeparator(
                scene_filename, config_file, "/", "\\"
            )
        else:
            RepositoryUtils.CheckPathMappingInFileAndReplaceSeparator(
                scene_filename, config_file, "\\", "/"
            )
            os.chmod(config_file, os.stat(config_file).st_mode)

        if not config_file:
            self.FailJob("Config file for Tile assembly is not set!")
            return

        if not os.path.exists(config_file):
            self.FailJob("Config file for Tile assembly is not accessible!")
            return

        data = {}
        with open(config_file, "rU") as stream:
            for line in stream:
                # Parsing key-value pair and removing white-space
                # around the entries
                info = [
                    part.strip()
                    for part in line.split("=", 1)
                ]
                if len(info) == 2:
                    data[str(info[0])] = info[1]
        return data

    def _render_executable(self):
        """Get render executable name.

        Get paths from plugin configuration, find executable and return it.

        Returns:
            (str): Render executable.

        """
        oiiotool_exe_list = self.GetConfigEntry(
            "OIIOTool_RenderExecutable"
        )
        oiiotool_exe = FileUtils.SearchFileList(oiiotool_exe_list)

        if oiiotool_exe == "":
            self.FailRender((
                "No file found in the semicolon separated list \"{}\"."
                " The path to the render executable can be configured from the"
                " Plugin Configuration in the Deadline Monitor."
            ).format(oiiotool_exe_list))

        return oiiotool_exe

    def _convert_path(self, filepath):
        """Handle slashes in file paths."""
        if SystemUtils.IsRunningOnWindows():
            filepath = filepath.replace("/", "\\")
            if filepath.startswith("\\") and not filepath.startswith("\\\\"):
                filepath = "\\" + filepath
        else:
            filepath = filepath.replace("\\", "/")
        return filepath
