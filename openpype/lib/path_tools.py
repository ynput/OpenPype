import os
import re
import abc
import json
import logging
import six
import platform

import clique

from openpype.client import get_project
from openpype.settings import get_project_settings

from .profiles_filtering import filter_profiles

log = logging.getLogger(__name__)


def format_file_size(file_size, suffix=None):
    """Returns formatted string with size in appropriate unit.

    Args:
        file_size (int): Size of file in bytes.
        suffix (str): Suffix for formatted size. Default is 'B' (as bytes).

    Returns:
        str: Formatted size using proper unit and passed suffix (e.g. 7 MiB).
    """

    if suffix is None:
        suffix = "B"

    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(file_size) < 1024.0:
            return "%3.1f%s%s" % (file_size, unit, suffix)
        file_size /= 1024.0
    return "%.1f%s%s" % (file_size, "Yi", suffix)


def create_hard_link(src_path, dst_path):
    """Create hardlink of file.

    Args:
        src_path(str): Full path to a file which is used as source for
            hardlink.
        dst_path(str): Full path to a file where a link of source will be
            added.
    """
    # Use `os.link` if is available
    #   - should be for all platforms with newer python versions
    if hasattr(os, "link"):
        os.link(src_path, dst_path)
        return

    # Windows implementation of hardlinks
    #   - used in Python 2
    if platform.system().lower() == "windows":
        import ctypes
        from ctypes.wintypes import BOOL
        CreateHardLink = ctypes.windll.kernel32.CreateHardLinkW
        CreateHardLink.argtypes = [
            ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_void_p
        ]
        CreateHardLink.restype = BOOL

        res = CreateHardLink(dst_path, src_path, None)
        if res == 0:
            raise ctypes.WinError()
        return
    # Raises not implemented error if gets here
    raise NotImplementedError(
        "Implementation of hardlink for current environment is missing."
    )


def collect_frames(files):
    """Returns dict of source path and its frame, if from sequence

    Uses clique as most precise solution, used when anatomy template that
    created files is not known.

    Assumption is that frames are separated by '.', negative frames are not
    allowed.

    Args:
        files(list) or (set with single value): list of source paths

    Returns:
        (dict): {'/asset/subset_v001.0001.png': '0001', ....}
    """

    patterns = [clique.PATTERNS["frames"]]
    collections, remainder = clique.assemble(
        files, minimum_items=1, patterns=patterns)

    sources_and_frames = {}
    if collections:
        for collection in collections:
            src_head = collection.head
            src_tail = collection.tail

            for index in collection.indexes:
                src_frame = collection.format("{padding}") % index
                src_file_name = "{}{}{}".format(
                    src_head, src_frame, src_tail)
                sources_and_frames[src_file_name] = src_frame
    else:
        sources_and_frames[remainder.pop()] = None

    return sources_and_frames


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
    new_filename = "{}{}".format(new_basename, ext)
    new_filename = os.path.join(dirname, new_filename)
    new_filename = os.path.normpath(new_filename)

    if new_filename == filepath:
        raise RuntimeError("Created path is the same as current file,"
                           "this is a bug")

    # We check for version clashes against the current file for any file
    # that matches completely in name up to the {version} label found. Thus
    # if source file was test_v001_test.txt we want to also check clashes
    # against test_v002.txt but do want to preserve the part after the version
    # label for our new filename
    clash_basename = new_basename
    if not clash_basename.endswith(new_label):
        index = (clash_basename.find(new_label))
        index += len(new_label)
        clash_basename = clash_basename[:index]

    for file in os.listdir(dirname):
        if file.endswith(ext) and file.startswith(clash_basename):
            log.info("Skipping existing version %s" % new_label)
            return version_up(new_filename)

    log.info("New version %s" % new_label)
    return new_filename


def get_version_from_path(file):
    """Find version number in file path string.

    Args:
        file (str): file path

    Returns:
        str: version number in string ('001')
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
        path_dir (str): directory path
        filter (list): list of strings used as file name filter

    Returns:
        str: file name with last version

    Example:
        last_version_file = get_last_version_from_path(
            "/project/shots/shot01/work", ["shot01", "compositing", "nk"])
    """

    assert os.path.isdir(path_dir), "`path_dir` argument needs to be directory"
    assert isinstance(filter, list) and (
        len(filter) != 0), "`filter` argument needs to be list and not empty"

    filtred_files = list()

    # form regex for filtering
    pattern = r".*".join(filter)

    for file in os.listdir(path_dir):
        if not re.findall(pattern, file):
            continue
        filtred_files.append(file)

    if filtred_files:
        sorted(filtred_files)
        return filtred_files[-1]

    return None


def concatenate_splitted_paths(split_paths, anatomy):
    pattern_array = re.compile(r"\[.*\]")
    output = []
    for path_items in split_paths:
        clean_items = []
        if isinstance(path_items, str):
            path_items = [path_items]

        for path_item in path_items:
            if not re.match(r"{.+}", path_item):
                path_item = re.sub(pattern_array, "", path_item)
            clean_items.append(path_item)

        # backward compatibility
        if "__project_root__" in path_items:
            for root, root_path in anatomy.roots.items():
                if not os.path.exists(str(root_path)):
                    log.debug("Root {} path path {} not exist on \
                        computer!".format(root, root_path))
                    continue
                clean_items = ["{{root[{}]}}".format(root),
                               r"{project[name]}"] + clean_items[1:]
                output.append(os.path.normpath(os.path.sep.join(clean_items)))
            continue

        output.append(os.path.normpath(os.path.sep.join(clean_items)))

    return output


def get_format_data(anatomy):
    project_doc = get_project(anatomy.project_name, fields=["data.code"])
    project_code = project_doc["data"]["code"]

    return {
        "root": anatomy.roots,
        "project": {
            "name": anatomy.project_name,
            "code": project_code
        },
    }


def fill_paths(path_list, anatomy):
    format_data = get_format_data(anatomy)
    filled_paths = []

    for path in path_list:
        new_path = path.format(**format_data)
        filled_paths.append(new_path)

    return filled_paths


def create_project_folders(basic_paths, project_name):
    from openpype.pipeline import Anatomy
    anatomy = Anatomy(project_name)

    concat_paths = concatenate_splitted_paths(basic_paths, anatomy)
    filled_paths = fill_paths(concat_paths, anatomy)

    # Create folders
    for path in filled_paths:
        if os.path.exists(path):
            log.debug("Folder already exists: {}".format(path))
        else:
            log.debug("Creating folder: {}".format(path))
            os.makedirs(path)


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


def create_workdir_extra_folders(
    workdir, host_name, task_type, task_name, project_name,
    project_settings=None
):
    """Create extra folders in work directory based on context.

    Args:
        workdir (str): Path to workdir where workfiles is stored.
        host_name (str): Name of host implementation.
        task_type (str): Type of task for which extra folders should be
            created.
        task_name (str): Name of task for which extra folders should be
            created.
        project_name (str): Name of project on which task is.
        project_settings (dict): Prepared project settings. Are loaded if not
            passed.
    """
    # Load project settings if not set
    if not project_settings:
        project_settings = get_project_settings(project_name)

    # Load extra folders profiles
    extra_folders_profiles = (
        project_settings["global"]["tools"]["Workfiles"]["extra_folders"]
    )
    # Skip if are empty
    if not extra_folders_profiles:
        return

    # Prepare profiles filters
    filter_data = {
        "task_types": task_type,
        "task_names": task_name,
        "hosts": host_name
    }
    profile = filter_profiles(extra_folders_profiles, filter_data)
    if profile is None:
        return

    for subfolder in profile["folders"]:
        # Make sure backslashes are converted to forwards slashes
        #   and does not start with slash
        subfolder = subfolder.replace("\\", "/").lstrip("/")
        # Skip empty strings
        if not subfolder:
            continue

        fullpath = os.path.join(workdir, subfolder)
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)
