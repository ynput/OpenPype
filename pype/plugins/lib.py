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
        Checks if oiiotool is installed for this platform
    """
    # TODO check if OIIO is actually working
    return os.getenv("PYPE_OIIO_PATH", "") != ""


def decompress(target_dir, file_urls, log=None):
    """
        Decompresses DWAA 'file_urls' .exrs to 'target_dir'.

        Creates uncompressed files in 'target_dir', they need to be cleaned

        Args:
            target_dir (str): extended from stagingDir
            file_urls (list): full urls to source files
            log (Logger): pype logger
    """
    oiio_cmd = []
    oiio_cmd.append(os.getenv("PYPE_OIIO_PATH"))

    oiio_cmd.append("--compression none")

    for file in file_urls:
        base_file_name = os.path.basename(file)
        oiio_cmd.append(file)

        oiio_cmd.append("-o")
        oiio_cmd.append(os.path.join(target_dir, base_file_name))

        subprocess_exr = " ".join(oiio_cmd)

        if not log:
            log = logging.getLogger(__name__)

        pype.api.subprocess(
            subprocess_exr, shell=True, logger=log
        )


def get_decompress_dir():
    return os.path.normpath(
        tempfile.mkdtemp(prefix="pyblish_tmp_")
    )


def should_decompress(self, file_url):
    if oiio_supported():
        oiio_supported
        output = pype.api.subprocess([os.getenv("PYPE_OIIO_PATH"),
                                      "--info", "-v", file_url])
        return "compression: \"dwaa\"" in output

    return False
