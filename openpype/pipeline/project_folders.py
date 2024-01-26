import os
import re
import json

import six

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
                if not root_path or not os.path.exists(str(root_path)):
                    log.debug(
                        "Root {} path path {} not exist on computer!".format(
                            root, root_path
                        )
                    )
                    continue

                root_items = [
                    "{{root[{}]}}".format(root),
                    "{project[name]}"
                ]
                root_items.extend(clean_items[1:])
                output.append(os.path.normpath(os.path.sep.join(root_items)))
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
