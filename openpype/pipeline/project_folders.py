import os
import re
import json

import six

from pathlib import Path

from openpype.settings import get_project_settings
from openpype.lib import Logger

from .anatomy import Anatomy
from .template_data import get_project_template_data


def concatenate_splitted_paths(split_paths, anatomy):
    log = Logger.get_logger("concatenate_splitted_paths")
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


def fill_paths(path_list, anatomy):
    format_data = get_project_template_data(project_name=anatomy.project_name)
    format_data["root"] = anatomy.roots
    filled_paths = []

    for path in path_list:
        new_path = path.format(**format_data)
        filled_paths.append(new_path)

    return filled_paths


def create_project_folders(project_name, basic_paths=None):
    log = Logger.get_logger("create_project_folders")
    anatomy = Anatomy(project_name)
    if basic_paths is None:
        basic_paths = get_project_basic_paths(project_name)

    if not basic_paths:
        return

    concat_paths = concatenate_splitted_paths(basic_paths, anatomy)
    filled_paths = fill_paths(concat_paths, anatomy)

    # Create folders
    case_sensitivity_issues = []
    for path_str in filled_paths:
        path = Path(path_str)

        if path.is_dir():
            log.debug("Folder already exists: {}".format(path_str))
        else:
            log.debug("Creating folder: {}".format(path_str))
            # Check case-insensitive for the whole path
            # Needed for case-sensitive OSs (Unix based)
            path_parent = Path(path.absolute().parts[0])
            path_parts = path.absolute().parts[1:]
            # We need to check for every part of the path because
            # os.makedirs can create multiple levels of directory at a time
            for path_part in path_parts:
                path_current = path_parent.joinpath(path_part)
                # Check if the current path already exists, so no need to check for doppelgängers
                if path_current.exists():
                    path_parent = path_current
                    continue
                for dir_child_path_str in os.listdir(path_parent):
                    if dir_child_path_str.lower() == path_part.lower():
                        case_sensitivity_issues.append((path_current, str(path_parent.joinpath(dir_child_path_str))))
                # Set the current looked dir as the new parent
                os.makedirs(path_current)
                path_parent = path_current


    return case_sensitivity_issues


def _list_path_items(folder_structure):
    output = []
    for key, value in folder_structure.items():
        if not value:
            output.append(key)
            continue

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

    if isinstance(folder_structure, six.string_types):
        folder_structure = json.loads(folder_structure)
    return _list_path_items(folder_structure)
