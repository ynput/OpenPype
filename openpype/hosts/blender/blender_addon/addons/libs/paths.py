import re
import os
import logging
from pathlib import Path

from openpype.pipeline.anatomy import Anatomy


def get_next_version_folder(filepath, create_version_folder=False):
    return _get_next_version(filepath, create_version_folder, format_to_version_folder=True)


def get_next_version_number(filepath, create_version_folder=False):
    return _get_next_version(filepath, create_version_folder, format_to_version_folder=False)


def get_version_folder_fullpath(filepath):
    latest_version_folder = _get_latest_version_folder(filepath, absolute_path=True, create_version_folder=False)
    if not latest_version_folder:
        return None

    return latest_version_folder


def get_workdir():
    anatomy_object = Anatomy()
    roots = getattr(anatomy_object, "roots", None)
    if not roots:
        raise Exception("Can't retrieve roots attribute for given anatomy object.")

    workdir = roots.get('work', None)
    if not workdir:
        raise Exception("Anatomy object has not work property. Can't retrive workdir for given entity.")

    return str(Path(str(workdir)).resolve())


def _get_latest_version_folder(filepath, absolute_path=False, create_version_folder=False):
    directory_path = _get_version_directory(filepath)
    if not directory_path:
        raise Exception("Version delimiter not found in given filepath: " + "({})".format(filepath))

    if create_version_folder:
        directory_path.mkdir(parents=True, exist_ok=True)

    elif not directory_path.is_dir():
        return None

    versions_folders = _list_all_versions_folders(directory_path)
    if not versions_folders:
        return None

    if absolute_path:
        return directory_path.joinpath(str(max(versions_folders))).resolve()

    return max(versions_folders)


def _get_version_directory(filepath):
    capture_version = r'(.*?)(v\d{3})|(.+[\\\/])'
    captured_groups = re.search(capture_version, filepath).groups()
    try:
        return Path(next(filter(lambda path: path is not None, captured_groups)))
    except StopIteration:
        return None


def _get_next_version(filepath, create_version_folder, format_to_version_folder):
    latest_version_folder = _get_latest_version_folder(filepath, create_version_folder)
    if not latest_version_folder:
        next_version_number = 1
    else:
        next_version_number = _extract_version_digits(latest_version_folder) + 1

    if format_to_version_folder:
        return _format_to_version_folder(next_version_number)
    else:
        return next_version_number


def _list_all_versions_folders(directory_path):
    for root, folders_names, _ in os.walk(directory_path):
        return [
            folder_name for folder_name in folders_names
            if Path(root).joinpath(folder_name).is_dir() and
            _is_version_folder(folder_name)
        ]


def _is_version_folder(folder_name):
    only_version_regex = r'(v\d{3})+$'
    results = re.search(only_version_regex, folder_name)
    return results.groups()[-1] if results else None


def _extract_version_digits(version_folder):
    return int(version_folder[-3:])


def _format_to_version_folder(version_number):
    return f'v{version_number:03d}'
