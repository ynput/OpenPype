import os
import re
from openpype.lib import Logger
from openpype.pipeline import frames
from openpype.pipeline import colorspace as clrs


def generate_expected_files(
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
        only_existing Optional[bool]: Ensure that files exists.

    Returns:
        Any[list[str], str]: List of expected files (file frames)
            or path if single file
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


def get_representation_with_expected_files(
    families,
    context_data,
    file_ext,
    output_dir,
    first_frame,
    last_frame,
    collected_file_frames,
    colorspace=None,
    log=None
):
    """Get representation with expected files.

    Args:
        families (list[str]): families
        context_data (dict[str, Any]): publishing context data
        file_ext (str): file extension
        output_dir (str): output directory
        first_frame (int): first frame
        last_frame (int): last frame
        collected_file_frames (list[str]): collected file frames

    Returns:
        dict[str, Any]: representation
    """
    log = log or Logger().get_logger(__name__)

    representation = {
        "name": file_ext,
        "ext": file_ext,
        "stagingDir": output_dir,
        "tags": []
    }

    frame_start_str = frames.get_frame_start_str(
        first_frame, last_frame)

    representation['frameStart'] = frame_start_str

    # set slate frame
    # QUESTION: should not we also include the slate
    #           frame within representation frameStart?
    if "slate" in families:
        collected_file_frames = \
            add_slate_frame_to_collected_frames(
                collected_file_frames,
                first_frame,
                last_frame
            )

    if len(collected_file_frames) == 1:
        representation['files'] = collected_file_frames.pop()
    else:
        representation['files'] = collected_file_frames

    # inject colorspace data
    clrs.set_colorspace_data_to_representation(
        representation,
        context_data,
        colorspace,
        log=log
    )

    return representation


def add_slate_frame_to_collected_frames(
    collected_file_frames,
    first_frame,
    last_frame
):
    """Add slate frame to collected frames.

    Args:
        collected_file_frames (list[str]): collected file frames
        first_frame (int): first frame
        last_frame (int): last frame

    Returns:
        list[str]: collected file frames
    """
    frame_start_str = frames.get_frame_start_str(
        first_frame, last_frame)
    frame_length = int(last_frame - first_frame + 1)

    # add slate frame only if it is not already in collected frames
    if frame_length == len(collected_file_frames):
        frame_slate_str = frames.get_frame_start_str(
            first_frame - 1,
            last_frame
        )

        slate_frame = collected_file_frames[0].replace(
            frame_start_str, frame_slate_str)
        collected_file_frames.insert(0, slate_frame)

    return collected_file_frames
