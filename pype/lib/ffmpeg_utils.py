import logging
import json
import subprocess

from . import get_ffmpeg_tool_path

log = logging.getLogger("FFmpeg utils")


def ffprobe_streams(path_to_file, logger=None):
    """Load streams from entered filepath via ffprobe."""
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
