"""Utility functions for file sequences.
"""
from calendar import c
import os
import re
from isort import file
from openpype.lib import Logger
from openpype.pipeline import frames
from openpype.pipeline import colorspace as clrs


def collect_filepaths_from_sequential_path(
    frame_start,
    frame_end,
    path,
    only_existing=False,
):
    """Generate expected files from path

    Args:
        frame_start (int): Start frame of the sequence
        frame_end (int): End frame of the sequence
        path (str): Path to generate expected files from
        only_existing (Optional[bool]): Ensure that files exists.

    Returns:
        Any[list[str], str]: List of absolute paths to files
            (frames of a sequence) or path if single file
    """

    dirpath = os.path.dirname(path)
    filename = os.path.basename(path)

    formattable_string = convert_filename_to_formattable_string(
        filename)

    if not formattable_string:
        return path

    expected_files = []
    for frame in range(int(frame_start), (int(frame_end) + 1)):
        frame_file_path = os.path.join(
            dirpath, formattable_string.format(frame)
        )
        # normalize path
        frame_file_path = os.path.normpath(frame_file_path)

        # make sure file exists if ensure_exists is enabled
        if only_existing and not os.path.exists(frame_file_path):
            continue

        # add to expected files
        expected_files.append(
            # add normalized path
            frame_file_path
        )

    return expected_files


def generate_expected_filepaths(
    frame_start,
    frame_end,
    path,
):
    """Generate expected files from path

    Args:
        frame_start (int): Start frame of the sequence
        frame_end (int): End frame of the sequence
        path (str): Path to generate expected files from

    Returns:
        Any[list[str], str]: List of expected absolute paths to files
            (frames of a sequence) or path if single file
    """
    return collect_filepaths_from_sequential_path(
        frame_start,
        frame_end,
        path,
        only_existing=False,
    )


def collect_files_from_sequential_path(
    frame_start,
    frame_end,
    file_path,
    only_existing=False,
):
    """Collect files from sequential path

    Args:
        frame_start (int): Start frame of the sequence
        frame_end (int): End frame of the sequence
        file_path (str): Absolute path with any sequential pattern (##, %02d)
        only_existing (Optional[bool]): Ensure that files exists.

    Returns:
        list[str]: List of collected file names
            (frames of a sequence) or path if single file
    """

    collected_abs_filepaths = collect_filepaths_from_sequential_path(
        frame_start,
        frame_end,
        file_path,
        only_existing,
    )

    if isinstance(collected_abs_filepaths, list):
        return [os.path.basename(f_) for f_ in collected_abs_filepaths]

    # return single file in list
    return [os.path.basename(collected_abs_filepaths)]


def convert_filename_to_formattable_string(filename):
    """Convert filename to formattable string

    Args:
        filename (str): Filename to convert

    Returns:
        Any[str, None]: Formattable string or None if not possible
                        to convert
    """
    new_filename = None

    if "#" in filename:
        # use regex to convert #### to {:0>4}
        def replace(match):
            return "{{:0>{}}}".format(len(match.group()))
        new_filename = re.sub("#+", replace, filename)

    elif "%" in filename:
        # use regex to convert %04d to {:0>4}
        def replace(match):
            return "{{:0>{}}}".format(match.group()[1:])
        new_filename = re.sub("%\\d+d", replace, filename)

    return new_filename


def get_farm_publishing_representation(
    instance,
    file_path,
    frame_start,
    frame_end,
    colorspace=None,
    log=None,
    only_existing=False,
):
    """Get representation with expected files.

    Args:
        instance (pyblish.Instance): instance
        file_path (str): file path
        frame_start (int): first frame
        frame_end (int): last frame
        colorspace (Optional[str]): colorspace
        log (Optional[Logger]): logger
        only_existing (Optional[bool]): Ensure that files exists.


    Returns:
        dict[str, Any]: representation
    """
    log = log or Logger().get_logger(__name__)
    file_ext = os.path.splitext(file_path)[-1].lstrip(".")
    output_dir = os.path.dirname(file_path)
    # get families from instance and add family from data
    families = set(
        instance.data.get("families", []) + [instance.data["family"]]
    )
    context_data = instance.context.data

    # prepare base representation data
    representation = {
        "name": file_ext,
        "ext": file_ext,
        "stagingDir": output_dir,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "tags": ["publish_on_farm"],
    }

    # collect files from sequential path or single file in list
    collected_file_frames = \
        collect_files_from_sequential_path(
            frame_start, frame_end, file_path, only_existing)

    # set slate frame
    if (
        "slate" in families
        and _add_slate_frame_to_collected_frames(
            collected_file_frames, frame_start, frame_end)
    ):
        log.info("Slate frame added to collected frames.")
        representation["frameStart"] = frame_start - 1

    if len(collected_file_frames) == 1:
        representation["files"] = collected_file_frames.pop()
    else:
        representation["files"] = collected_file_frames

    # inject colorspace data
    clrs.set_colorspace_data_to_representation(
        representation,
        context_data,
        colorspace,
        log=log
    )

    return representation


def _add_slate_frame_to_collected_frames(
    collected_file_frames,
    frame_start,
    frame_end
):
    """Add slate frame to collected frames.

    Args:
        collected_file_frames (list[str]): collected file frames
        frame_start (int): first frame
        frame_end (int): last frame

    Returns:
        Bool: True if slate frame was added
    """
    frame_start_str = frames.get_frame_start_str(
        frame_start, frame_end)
    frame_length = int(frame_end - frame_start + 1)

    # add slate frame only if it is not already in collected frames
    if frame_length == len(collected_file_frames):
        frame_slate_str = frames.get_frame_start_str(
            frame_start - 1,
            frame_end
        )

        slate_frame = collected_file_frames[0].replace(
            frame_start_str, frame_slate_str)
        collected_file_frames.insert(0, slate_frame)

        return True
