import os
import logging
import json
import platform
import subprocess

log = logging.getLogger("FFmpeg utils")


def get_vendor_bin_path(bin_app):
    """Path to OpenPype vendorized binaries.

    Vendorized executables are expected in specific hierarchy inside build or
    in code source.

    "{OPENPYPE_ROOT}/vendor/bin/{name of vendorized app}/{platform}"

    Args:
        bin_app (str): Name of vendorized application.

    Returns:
        str: Path to vendorized binaries folder.
    """
    return os.path.join(
        os.environ["OPENPYPE_ROOT"],
        "vendor",
        "bin",
        bin_app,
        platform.system().lower()
    )


def get_ffmpeg_tool_path(tool="ffmpeg"):
    """Path to vendorized FFmpeg executable.

    Args:
        tool (string): Tool name (ffmpeg, ffprobe, ...).
            Default is "ffmpeg".

    Returns:
        str: Full path to ffmpeg executable.
    """
    ffmpeg_dir = get_vendor_bin_path("ffmpeg")
    if platform.system().lower() == "windows":
        ffmpeg_dir = os.path.join(ffmpeg_dir, "bin")
    return os.path.join(ffmpeg_dir, tool)


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
