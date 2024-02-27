import re
import os
from pathlib import Path


def _get_version_directory(filepath):
    parts = filepath.split('{version}')
    if len(parts) == 1:
        return None
    return Path(parts[0])


def get_latest_version_folder(filepath, enforce_parent_dir=False):
    directory_path = _get_version_directory(filepath)
    if not directory_path:
        raise Exception("Delimiter '{version}' not found in given filepath: " + "({})".format(filepath))

    # Ensure the folder exists on disk
    if enforce_parent_dir:
        directory_path.mkdir(parents=True, exist_ok=True)
    elif not directory_path.exists():
        return None

    versions_folders = _list_all_versions_folders(directory_path)

    if not versions_folders:
        return None

    return max(versions_folders)


def get_next_version_folder(filepath):
    latest_version_folder = get_latest_version_folder(filepath, enforce_parent_dir=True)
    if not latest_version_folder:
        next_version_number = 1
    else:
        next_version_number = _extract_version_digits(latest_version_folder) + 1

    return _format_to_version_folder(next_version_number)


def get_version_folder(filepath):
    directory_path = _get_version_directory(filepath)
    latest_version_folder = get_latest_version_folder(filepath)
    if not latest_version_folder:
        return None

    version_path = os.path.join(directory_path, latest_version_folder)

    return version_path


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
    return results.groups()[-1]


def _extract_version_digits(version_folder):
    return int(version_folder[-3:])


def _format_to_version_folder(version_number):
    return f'v{version_number:03d}'
