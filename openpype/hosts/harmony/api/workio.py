"""Host API required Work Files tool"""
import os
import shutil

from openpype.pipeline import HOST_WORKFILE_EXTENSIONS

from .lib import (
    ProcessContext,
    get_local_harmony_path,
    zip_and_move,
    launch_zip_file
)

# used to lock saving until previous save is done.
save_disabled = False


def file_extensions():
    return HOST_WORKFILE_EXTENSIONS["harmony"]


def has_unsaved_changes():
    if ProcessContext.server:
        return ProcessContext.server.send(
            {"function": "scene.isDirty"})["result"]

    return False


def save_file(filepath):
    global save_disabled
    if save_disabled:
        return ProcessContext.server.send(
            {
                "function": "show_message",
                "args": "Saving in progress, please wait until it finishes."
            })["result"]

    save_disabled = True
    temp_path = get_local_harmony_path(filepath)

    if ProcessContext.server:
        if os.path.exists(temp_path):
            try:
                shutil.rmtree(temp_path)
            except Exception as e:
                raise Exception(f"cannot delete {temp_path}") from e

        ProcessContext.server.send(
            {"function": "scene.saveAs", "args": [temp_path]}
        )["result"]

        zip_and_move(temp_path, filepath)

        ProcessContext.workfile_path = filepath

        scene_path = os.path.join(
            temp_path, os.path.basename(temp_path) + ".xstage"
        )
        ProcessContext.server.send(
            {"function": "AvalonHarmony.addPathToWatcher", "args": scene_path}
        )
    else:
        os.environ["HARMONY_NEW_WORKFILE_PATH"] = filepath.replace("\\", "/")

    save_disabled = False


def open_file(filepath):
    launch_zip_file(filepath)


def current_file():
    """Returning None to make Workfiles app look at first file extension."""
    return None


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
