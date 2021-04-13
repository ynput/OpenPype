import os
import logging
import json
import subprocess

from . import get_paths_from_environ

log = logging.getLogger("FFmpeg utils")


def get_ffmpeg_tool_path(tool="ffmpeg"):
    """Find path to ffmpeg tool in OPENPYPE_FFMPEG_PATH paths.

    Function looks for tool in paths set in OPENPYPE_FFMPEG_PATH environment.
    If tool exists then returns it's full path.

    Args:
        tool (string): tool name

    Returns:
        (str): tool name itself when tool path was not found. (FFmpeg path
        may be set in PATH environment variable)
    """
    dir_paths = get_paths_from_environ("OPENPYPE_FFMPEG_PATH")
    for dir_path in dir_paths:
        for file_name in os.listdir(dir_path):
            base, _ext = os.path.splitext(file_name)
            if base.lower() == tool.lower():
                return os.path.join(dir_path, tool)
    return tool


def ffprobe_streams(path_to_file, logger=None):
    """Load streams from entered filepath via ffprobe.

    Args:
        path_to_file (str): absolute path
        logger (logging.getLogger): injected logger, if empty new is created

    """
    if not logger:
        logger = log
    logger.info(
        "Getting information about input \"{}\".".format(path_to_file)
    )
    args = [
        "\"{}\"".format(get_ffmpeg_tool_path("ffprobe")),
        "-v quiet",
        "-print_format json",
        "-show_format",
        "-show_streams",
        "\"{}\"".format(path_to_file)
    ]
    command = " ".join(args)
    logger.debug("FFprobe command: \"{}\"".format(command))
    popen = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    popen_stdout, popen_stderr = popen.communicate()
    if popen_stdout:
        logger.debug("ffprobe stdout: {}".format(popen_stdout))

    if popen_stderr:
        logger.debug("ffprobe stderr: {}".format(popen_stderr))
    return json.loads(popen_stdout)["streams"]
