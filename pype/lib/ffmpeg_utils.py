import os
import json
import subprocess
import logging
from .environment import get_paths_from_environ

log = logging.getLogger(__name__)


def ffprobe_streams(path_to_file):
    """Load streams from entered filepath via ffprobe."""
    log.info(
        "Getting information about input \"{}\".".format(path_to_file)
    )
    args = [
        get_ffmpeg_tool_path("ffprobe"),
        "-v quiet",
        "-print_format json",
        "-show_format",
        "-show_streams",
        "\"{}\"".format(path_to_file)
    ]
    command = " ".join(args)
    log.debug("FFprobe command: \"{}\"".format(command))
    popen = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)

    popen_output = popen.communicate()[0]
    log.debug("FFprobe output: {}".format(popen_output))
    return json.loads(popen_output)["streams"]


def get_ffmpeg_tool_path(tool="ffmpeg"):
    """Find path to ffmpeg tool in FFMPEG_PATH paths.

    Function looks for tool in paths set in FFMPEG_PATH environment. If tool
    exists then returns it's full path.

    Returns tool name itself when tool path was not found. (FFmpeg path may be
    set in PATH environment variable)
    """

    dir_paths = get_paths_from_environ("FFMPEG_PATH")
    for dir_path in dir_paths:
        for file_name in os.listdir(dir_path):
            base, ext = os.path.splitext(file_name)
            if base.lower() == tool.lower():
                return os.path.join(dir_path, tool)
    return tool
