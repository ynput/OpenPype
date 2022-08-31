import os
import re

from openpype.lib import Logger

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
