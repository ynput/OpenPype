import os
import re
import logging
import tempfile

from .execute import run_subprocess
from .vendor_bin_utils import (
    get_oiio_tools_path,
    is_oiio_supported
)


def decompress(target_dir, file_url,
               input_frame_start=None, input_frame_end=None, log=None):
    """
        Decompresses DWAA 'file_url' .exr to 'target_dir'.

        Creates uncompressed files in 'target_dir', they need to be cleaned.

        File url could be for single file or for a sequence, in that case
        %0Xd will be as a placeholder for frame number AND input_frame* will
        be filled.
        In that case single oiio command with '--frames' will be triggered for
        all frames, this should be faster then looping and running sequentially

        Args:
            target_dir (str): extended from stagingDir
            file_url (str): full urls to source file (with or without %0Xd)
            input_frame_start (int) (optional): first frame
            input_frame_end (int) (optional): last frame
            log (Logger) (optional): pype logger
    """
    is_sequence = input_frame_start is not None and \
        input_frame_end is not None and \
        (int(input_frame_end) > int(input_frame_start))

    oiio_cmd = []
    oiio_cmd.append(get_oiio_tools_path())

    oiio_cmd.append("--compression none")

    base_file_name = os.path.basename(file_url)
    oiio_cmd.append(file_url)

    if is_sequence:
        oiio_cmd.append("--frames {}-{}".format(input_frame_start,
                                                input_frame_end))

    oiio_cmd.append("-o")
    oiio_cmd.append(os.path.join(target_dir, base_file_name))

    subprocess_exr = " ".join(oiio_cmd)

    if not log:
        log = logging.getLogger(__name__)

    log.debug("Decompressing {}".format(subprocess_exr))
    run_subprocess(
        subprocess_exr, shell=True, logger=log
    )


def get_decompress_dir():
    """
        Creates temporary folder for decompressing.
        Its local, in case of farm it is 'local' to the farm machine.

        Should be much faster, needs to be cleaned up later.
    """
    return os.path.normpath(
        tempfile.mkdtemp(prefix="pyblish_tmp_")
    )


def should_decompress(file_url):
    """Tests that 'file_url' is compressed with DWAA.

    Uses 'is_oiio_supported' to check that OIIO tool is available for this
    platform.

    Shouldn't throw exception as oiiotool is guarded by check function.
    Currently implemented this way as there is no support for Mac and Linux
    In the future, it should be more strict and throws exception on
    misconfiguration.

    Args:
        file_url (str): path to rendered file (in sequence it would be
            first file, if that compressed it is expected that whole seq
            will be too)

    Returns:
        bool: 'file_url' is DWAA compressed and should be decompressed
            and we can decompress (oiiotool supported)
    """
    if is_oiio_supported():
        try:
            output = run_subprocess([
                get_oiio_tools_path(),
                "--info", "-v", file_url])
            return (
                "compression: \"dwaa\"" in output
                or "compression: \"dwab\"" in output
            )

        except RuntimeError:
            _name, ext = os.path.splitext(file_url)
            # TODO: should't the list of allowed extensions be
            #     taken from an OIIO variable of supported formats
            if ext not in [".mxf"]:
                # Reraise exception
                raise

    return False


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
