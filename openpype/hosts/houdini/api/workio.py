"""Host API required Work Files tool"""
import os

import hou
from avalon import api


def file_extensions():
    return api.HOST_WORKFILE_EXTENSIONS["houdini"]


def has_unsaved_changes():
    return hou.hipFile.hasUnsavedChanges()


def save_file(filepath):

    # Force forwards slashes to avoid segfault
    filepath = filepath.replace("\\", "/")

    hou.hipFile.save(file_name=filepath,
                     save_to_recent_files=True)

    return filepath


def open_file(filepath):

    # Force forwards slashes to avoid segfault
    filepath = filepath.replace("\\", "/")

    hou.hipFile.load(filepath,
                     suppress_save_prompt=True,
                     ignore_load_warnings=False)

    return filepath


def current_file():

    current_filepath = hou.hipFile.path()
    if (os.path.basename(current_filepath) == "untitled.hip" and
            not os.path.exists(current_filepath)):
        # By default a new scene in houdini is saved in the current
        # working directory as "untitled.hip" so we need to capture
        # that and consider it 'not saved' when it's in that state.
        return None

    return current_filepath


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
