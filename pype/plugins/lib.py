import re
import os
import pype.api
import logging
import tempfile


def get_unique_layer_name(layers, asset_name, subset_name):
    """
        Gets all layer names and if 'name' is present in them, increases
        suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list): of namedtuples, expects 'name' field present
        asset_name (string):  in format asset_subset (Hero)
        subset_name (string): (LOD)

    Returns:
        (string): name_00X (without version)
    """
    name = "{}_{}".format(asset_name, subset_name)
    names = {}
    for layer in layers:
        layer_name = re.sub(r'_\d{3}$', '', layer.name)
        if layer_name in names.keys():
            names[layer_name] = names[layer_name] + 1
        else:
            names[layer_name] = 1
    occurrences = names.get(name, 0)

    return "{}_{:0>3d}".format(name, occurrences + 1)


def oiio_supported():
    """
        Checks if oiiotool is configured for this platform.

        'should_decompress' will throw exception if configured,
        but not present or working.
    """
    return os.getenv("PYPE_OIIO_PATH", "") != ""


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
    oiio_cmd.append(os.getenv("PYPE_OIIO_PATH"))

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
    pype.api.subprocess(
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
    """
        Tests that 'file_url' is compressed with DWAA.

        Uses 'oiio_supported' to check that OIIO tool is available for this
        platform

        Args:
            file_url (str): path to rendered file (in sequence it would be
                first file, if that compressed it is expected that whole seq
                will be too)
        Returns:
            (bool): 'file_url' is DWAA compressed and should be decompressed
    """
    if oiio_supported():
        output = pype.api.subprocess([os.getenv("PYPE_OIIO_PATH"),
                                      "--info", "-v", file_url])
        return "compression: \"dwaa\"" in output

    return False
