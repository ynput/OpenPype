import json
import logging
import os
import re


from .anatomy import Anatomy
from openpype.settings import get_project_settings

log = logging.getLogger(__name__)


def _rreplace(s, a, b, n=1):
    """Replace a with b in string s from right side n times."""
    return b.join(s.rsplit(a, n))


def version_up(filepath):
    """Version up filepath to a new non-existing version.

    Parses for a version identifier like `_v001` or `.v001`
    When no version present _v001 is appended as suffix.

    Args:
        filepath (str): full url

    Returns:
        (str): filepath with increased version number

    """
    dirname = os.path.dirname(filepath)
    basename, ext = os.path.splitext(os.path.basename(filepath))

    regex = r"[._]v\d+"
    matches = re.findall(regex, str(basename), re.IGNORECASE)
    if not matches:
        log.info("Creating version...")
        new_label = "_v{version:03d}".format(version=1)
        new_basename = "{}{}".format(basename, new_label)
    else:
        label = matches[-1]
        version = re.search(r"\d+", label).group()
        padding = len(version)

        new_version = int(version) + 1
        new_version = '{version:0{padding}d}'.format(version=new_version,
                                                     padding=padding)
        new_label = label.replace(version, new_version, 1)
        new_basename = _rreplace(basename, label, new_label)

    if not new_basename.endswith(new_label):
        index = (new_basename.find(new_label))
        index += len(new_label)
        new_basename = new_basename[:index]

    new_filename = "{}{}".format(new_basename, ext)
    new_filename = os.path.join(dirname, new_filename)
    new_filename = os.path.normpath(new_filename)

    if new_filename == filepath:
        raise RuntimeError("Created path is the same as current file,"
                           "this is a bug")

    for file in os.listdir(dirname):
        if file.endswith(ext) and file.startswith(new_basename):
            log.info("Skipping existing version %s" % new_label)
            return version_up(new_filename)

    log.info("New version %s" % new_label)
    return new_filename


def get_version_from_path(file):
    """Find version number in file path string.

    Args:
        file (string): file path

    Returns:
        v: version number in string ('001')

    """
    pattern = re.compile(r"[\._]v([0-9]+)", re.IGNORECASE)
    try:
        return pattern.findall(file)[-1]
    except IndexError:
        log.error(
            "templates:get_version_from_workfile:"
            "`{}` missing version string."
            "Example `v004`".format(file)
        )


def get_last_version_from_path(path_dir, filter):
    """Find last version of given directory content.

    Args:
        path_dir (string): directory path
        filter (list): list of strings used as file name filter

    Returns:
        string: file name with last version

    Example:
        last_version_file = get_last_version_from_path(
            "/project/shots/shot01/work", ["shot01", "compositing", "nk"])
    """
    assert os.path.isdir(path_dir), "`path_dir` argument needs to be directory"
    assert isinstance(filter, list) and (
        len(filter) != 0), "`filter` argument needs to be list and not empty"

    filtred_files = list()

    # form regex for filtering
    patern = r".*".join(filter)

    for file in os.listdir(path_dir):
        if not re.findall(patern, file):
            continue
        filtred_files.append(file)

    if filtred_files:
        sorted(filtred_files)
        return filtred_files[-1]

    return None


def compute_paths(basic_paths_items, project_root):
    pattern_array = re.compile(r"\[.*\]")
    project_root_key = "__project_root__"
    output = []
    for path_items in basic_paths_items:
        clean_items = []
        for path_item in path_items:
            matches = re.findall(pattern_array, path_item)
            if len(matches) > 0:
                path_item = path_item.replace(matches[0], "")
            if path_item == project_root_key:
                path_item = project_root
            clean_items.append(path_item)
        output.append(os.path.normpath(os.path.sep.join(clean_items)))
    return output


def create_project_folders(basic_paths, project_name):
    anatomy = Anatomy(project_name)
    roots_paths = []
    if isinstance(anatomy.roots, dict):
        for root in anatomy.roots.values():
            roots_paths.append(root.value)
    else:
        roots_paths.append(anatomy.roots.value)

    for root_path in roots_paths:
        project_root = os.path.join(root_path, project_name)
        full_paths = compute_paths(basic_paths, project_root)
        # Create folders
        for path in full_paths:
            full_path = path.format(project_root=project_root)
            if os.path.exists(full_path):
                log.debug(
                    "Folder already exists: {}".format(full_path)
                )
            else:
                log.debug("Creating folder: {}".format(full_path))
                os.makedirs(full_path)


def _list_path_items(folder_structure):
    output = []
    for key, value in folder_structure.items():
        if not value:
            output.append(key)
        else:
            paths = _list_path_items(value)
            for path in paths:
                if not isinstance(path, (list, tuple)):
                    path = [path]

                item = [key]
                item.extend(path)
                output.append(item)

    return output


def get_project_basic_paths(project_name):
    project_settings = get_project_settings(project_name)
    folder_structure = (
        project_settings["global"]["project_folder_structure"]
    )
    if not folder_structure:
        return []

    if isinstance(folder_structure, str):
        folder_structure = json.loads(folder_structure)
    return _list_path_items(folder_structure)
