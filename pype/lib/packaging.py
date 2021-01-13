#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import clique
import shutil
from pypeapp import Anatomy
import zipfile
import logging
log = logging.getLogger(__name__)



def _zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), os.path.relpath(
                os.path.join(root, file), os.path.join(path, '..')))


def _sync_files_to_package(sync_paths):
    for paths in sync_paths:
        for file in paths["files"]:
            os.makedirs(paths["to_dir"], mode=0o777, exist_ok=True)
            src_path = os.path.normpath(os.path.join(paths["from_dir"], file))
            dst_path = os.path.normpath(os.path.join(paths["to_dir"], file))
            shutil.copy(src_path, dst_path, follow_symlinks=True)
            log.debug(
                "File `{}` coppied to `{}`...".format(src_path, dst_path))


def _save_text_lines_to_file(filepath, lines):
    """
    Droping lines into filepath as file.

    Args:
        filepath (str): desired path to file
        lines (list): list with lines of string with `\n` at the end

    """
    if os.path.exists(filepath):
        os.remove(filepath)
    with open(filepath, 'a') as filepath_file:
        filepath_file.writelines(lines)
    filepath_file.close()


def _get_packaging_path(anatomy, anatomy_data):
    anatomy_filled = anatomy.format_all(anatomy_data)

    delivery = anatomy_filled.get("delivery")
    assert delivery, KeyError(
        "`{}` project override is not having available key "
        "`delivery` template".format(
            anatomy.project_name
        )
    )
    packaging_template = delivery.get("packaging")
    assert packaging_template, KeyError(
        "`{}` project's override `delivery` is missing "
        "`packaging` key template".format(
            anatomy.project_name
        )
    )
    return anatomy_filled["delivery"]["packaging"]


def _swap_root_to_package(anatomy, path, destination_root):
    success, rootless_path = anatomy.find_root_template_from_path(path)

    assert success, ValueError(
        "{}: Project's roots were not found in path: {}".format(
            anatomy.project_name, path
        )
    )
    return rootless_path.format(root=destination_root)


def _collect_files(filepath):
    files = list()
    dirpath = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    # if hashes then get collection of files
    if "#" in filepath or "%" in filepath:
        head = basename.split("%")
        if len(head) == 1:
            head = basename.split("#")

        collections, reminders = clique.assemble(
            [f for f in os.listdir(dirpath)
             if head[0] in f])
        collection = collections.pop()

        # add collection to files for coppying
        files = list(collection)
    else:
        files.append(basename)
    return files




def make_workload_package_for_tasks(
    project_doc, asset_docs_by_id, task_names_by_asset_id
):
    # Create anatomy object
    anatomy = Anatomy(project_doc["name"])
    log.warning(anatomy.root_environments())
    anatomy_data = {
        "project": {"name": project_name},
        "task": avalon_session["AVALON_TASK"],
        "asset": avalon_session["AVALON_ASSET"],
        "root": anatomy.roots,
        "ext": "zip"
    }
    log.warning(anatomy_data)


def make_workload_package(anatomy, fill_data, path_nk):
    packaging_data = copy.deepcopy(fill_data)
    # Set extension to zip
    packaging_data["ext"] = "zip"
    log.warning(packaging_data)

    # get packaging zip path
    zip_package_path = _get_packaging_path(anatomy, packaging_data)
    dir_package_path = os.path.splitext(zip_package_path)[0]
    os.makedirs(dir_package_path, mode=0o777, exist_ok=True)
    log.debug(dir_package_path)

    # potentially used alternative file if any change had been made
    new_workfile_suffix = "OutsideResourcesIncuded"
    extension = os.path.splitext(path_nk)[1]
    nk_file_altered = ''.join([
        path_nk.replace(extension, ''),
        "_", new_workfile_suffix, extension])
    save_altered_nkfile = False

    resources_path = os.path.join(
        os.path.dirname(path_nk), "resources"
    )

    # nuke path for zip package
    package_path_nk = _swap_root_to_package(anatomy, path_nk, dir_package_path)
    log.debug(package_path_nk)

    pattern = re.compile("^(?:\\s+file\\s)(?P<path>.*)", re.VERBOSE)
    sync_paths = list()
    done_paths = list()
    with open(path_nk, "r") as nk_file:
        nk_file_lines = list(nk_file.readlines())

    nk_file_lines_new = nk_file_lines.copy()
    for line_index, line_string in enumerate(nk_file_lines):
        for result in pattern.finditer(line_string):
            if "path" not in result.groupdict().keys():
                continue

            from_path = result.groupdict()["path"]
            # try env replace
            try:
                env_path = anatomy.replace_root_with_env_key(
                    from_path, "\\[getenv {}]")
            except ValueError:
                # excepth test if path exists | except script fail
                dirpath = os.path.dirname(from_path)
                basename = os.path.basename(from_path)

                if not os.path.exists(dirpath):
                    IOError(
                        "Used path in script does not exist: {}".format(
                            from_path
                        )
                    )
                move_files = _collect_files(from_path)

                # if resources folder not existing > create one
                os.makedirs(resources_path, mode=0o777, exist_ok=True)

                # copy all appropriate data to `workfile/resources`
                for file in move_files:
                    copy_from = os.path.join(dirpath, file)
                    copy_to = os.path.join(resources_path, file)
                    shutil.copy(copy_from, copy_to)

                # create new path to resources as new original
                new_from_path = os.path.join(
                    resources_path, basename
                ).replace("\\", "/")

                # change path in original `nk_file_lines`
                nk_file_lines[line_index] = nk_file_lines[
                    line_index].replace(from_path, new_from_path)

                # trigger after saving as new subversion
                save_altered_nkfile = True

                env_path = anatomy.replace_root_with_env_key(
                    new_from_path, "\\[getenv {}]")
                from_path = new_from_path

            to_path = _swap_root_to_package(
                anatomy, from_path, dir_package_path)

            # replace path in .nk file wich will be delivered
            # with package
            nk_file_lines_new[line_index] = nk_file_lines[
                line_index].replace(
                    from_path, "\"{}\"".format(env_path))

            # skip path if it had been already used
            if from_path in done_paths:
                continue

            # save paths for later processing
            sync_paths.append({
                "from_dir": os.path.dirname(from_path),
                "to_dir": os.path.dirname(to_path),
                "files": _collect_files(from_path)
            })
            done_paths.append(from_path)

    # copy all files from sync_paths
    _sync_files_to_package(sync_paths)

    # save nk file for alteret original
    if save_altered_nkfile:
        _save_text_lines_to_file(nk_file_altered, nk_file_lines)

    # save nk file to package
    _save_text_lines_to_file(package_path_nk, nk_file_lines_new)

    zipf = zipfile.ZipFile(zip_package_path, 'w', zipfile.ZIP_DEFLATED)
    _zipdir(dir_package_path, zipf)
    zipf.close()

    log.info(f"Zip file was collected to: `{zip_package_path}`")
