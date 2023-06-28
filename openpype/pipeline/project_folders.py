import os
import re
import json

import six

from openpype.settings import get_project_settings
from openpype.lib import Logger
import shutil
from .anatomy import Anatomy
from .template_data import get_project_template_data
import win32file
import sys
import subprocess
def concatenate_splitted_paths(split_paths, anatomy):
    log = Logger.get_logger("concatenate_splitted_paths")
    pattern_array = re.compile(r"\[.*\]")
    pattern_symlink = re.compile(r"symlink\.[^.,\],\s,]*")
    output = []
    for path_items in split_paths:
        clean_items = []
        links = []
        if isinstance(path_items, str):
            path_items = [path_items]

        for path_item in path_items:
            if not re.match(r"{.+}", path_item):
                link = re.findall(pattern_symlink,path_item)
                #Hornet > create symlink
                if len(link) > 0:
                    make_link(path_item,path_items,anatomy)
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

def make_link(link_item,path_items, anatomy):
    DRIVES = {
        'edit': '//fse.hellohornet.lan/edit/',
        'producers': '//fs.hellohornet.lan/producers/',
        'resources': '//fs.hellohornet.lan/resources/'
    }
    drive_letter_pattern = r"[A-Z]:[\\/]"
    unc_pattern = r"(\\\\[\w\s.$_-]+[\\/](?:[\w\s.$_-]+[\\/])+[\w\s.$_-]+)"
    pattern_symlink = re.compile(r"symlink\.[^.,\],\s,]*")

    log = Logger.get_logger("concatenate_splitted_paths")
    clean_items = path_items
    if "__project_root__" in path_items:
            for root, root_path in anatomy.roots.items():
                if not os.path.exists(str(root_path)):
                    log.debug("Root {} path path {} not exist on \
                        computer!".format(root, root_path))
                    continue
                clean_items = ["{{root[{}]}}".format(root),
                               r"{project[name]}"] + clean_items[1:]

    stack = fill_paths(clean_items,anatomy)
    link_alias = link_item.split('[')[0]
    link_loc = stack[:stack.index(link_item)]
    link_drive = link_item.split('.')[1].strip('[]')
    link_file = ('/'.join(link_loc)).replace('\\','/')
    link_path = '/'.join(link_loc)
    link_target = re.sub(drive_letter_pattern, DRIVES[link_drive],link_path)
    link_target = re.sub(unc_pattern, DRIVES[link_drive],link_target).replace('\\','/')
    log.debug('linking to drive ' + link_drive)
    log.debug('link at ' + link_file)
    log.debug('link target: ' + link_target)
    log.debug('----')
    try:
        if sys.platform == 'darwin':
            print(f'osascript -e \'tell application "Finder" to make alias file to POSIX file "{link_target}" at POSIX file "{link_at}"\'')
            subprocess.Popen( f'osascript -e \'tell application "Finder" to make alias file to POSIX file "{link_target}" at POSIX file "{link_at}"\'',shell=True)
        elif sys.platform == 'win32':
            win32file.CreateSymbolicLink(link_file,link_target,1)
    except Exception as e:
        log.debug(e)


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
            log.debug("folder already exists: {}".format(path))
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
