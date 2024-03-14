import re
import os
from pathlib import Path


def _get_next_version(filepath, format_to_version_folder=True, create_version_folder=False):
    directory_path = _get_version_directory(filepath)
    print('directory path')
    print(directory_path)
    if create_version_folder:
        directory_path.mkdir(parents=True, exist_ok=True)
    else:
        if not directory_path.is_dir(): return 1

    versions_folders = _list_all_versions_folders(directory_path)
    if versions_folders:
        latest_version_folder = max(versions_folders)
        next_version_number = _extract_version_digits(latest_version_folder) +1

    else:
        next_version_number = 1

    if format_to_version_folder:
        return _format_to_version_folder(next_version_number)
    else:
        return next_version_number


def get_next_version_folder(filepath):
    return _get_next_version(filepath, format_to_version_folder=True, create_version_folder=False)


def get_next_version_number(filepath):
    return _get_next_version(filepath, format_to_version_folder=False, create_version_folder=False)


def create_and_get_next_version_folder(filepath):
    return _get_next_version(filepath, format_to_version_folder=True, create_version_folder=True)


def create_and_get_next_version_number(filepath):
    return _get_next_version(filepath, format_to_version_folder=False, create_version_folder=True)


def _get_version_directory(filepath):
    capture_version = r'(.+)(v\d{3})|(.+[\\\/])'
    captured_groups = re.search(capture_version, filepath).groups()
    return Path(next(filter(lambda path: path is not None, captured_groups)))


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
