import re
import os
from pathlib import Path


def _get_version_directory(filepath):
    parts = filepath.split('{version}')
    if len(parts) == 1:
        return None
    return Path(parts[0])


def get_next_version_folder(filepath):
    directory_path = _get_version_directory(filepath)
    if not directory_path:
        raise Exception("Delimiter '{version}' not found in given filepath: " + "({})".format(filepath))

    # Ensure the folder exists on disk
    directory_path.mkdir(parents=True, exist_ok=True)

    versions_folders = _list_all_versions_folders(directory_path)

    next_version_number = 1
    if versions_folders:
        latest_version_folder = max(versions_folders)
        next_version_number = _extract_version_digits(latest_version_folder) + 1

    return _format_to_version_folder(next_version_number)


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
