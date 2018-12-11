import glob
import os
import logging

_registered_paths = []
log = logging.getLogger("Presets")


def discover(paths=None):
    """Get the full list of files found in the registered folders

    Args:
        paths (list, Optional): directories which host preset files or None.
            When None (default) it will list from the registered preset paths.

    Returns:
        list: valid .json preset file paths.

    """

    presets = []
    for path in paths or preset_paths():
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            continue

        # check for json files
        glob_query = os.path.abspath(os.path.join(path, "*.json"))
        filenames = glob.glob(glob_query)
        for filename in filenames:
            # skip private files
            if filename.startswith("_"):
                continue

            # check for file size
            if not check_file_size(filename):
                log.warning("Filesize is smaller than 1 byte for file '%s'",
                            filename)
                continue

            if filename not in presets:
                presets.append(filename)

    return presets


def check_file_size(filepath):
    """Check if filesize of the given file is bigger than 1.0 byte

    Args:
        filepath (str): full filepath of the file to check

    Returns:
        bool: Whether bigger than 1 byte.

    """

    file_stats = os.stat(filepath)
    if file_stats.st_size < 1:
        return False
    return True


def preset_paths():
    """Return existing registered preset paths

    Returns:
        list: List of full paths.

    """

    paths = list()
    for path in _registered_paths:
        # filter duplicates
        if path in paths:
            continue

        if not os.path.exists(path):
            continue

        paths.append(path)

    return paths


def register_preset_path(path):
    """Add filepath to registered presets

    :param path: the directory of the preset file(s)
    :type path: str

    :return:
    """
    if path in _registered_paths:
        return log.warning("Path already registered: %s", path)

    _registered_paths.append(path)

    return path


# Register default user folder
user_folder = os.path.expanduser("~")
capture_gui_presets = os.path.join(user_folder, "CaptureGUI", "presets")
register_preset_path(capture_gui_presets)
