"""Host API required Work Files tool"""
import os
import nuke
import shutil
from .utils import is_headless


def file_extensions():
    return [".nk"]


def has_unsaved_changes():
    return nuke.root().modified()


def save_file(filepath):
    path = filepath.replace("\\", "/")
    nuke.scriptSaveAs(path, overwrite=1)
    nuke.Root()["name"].setValue(path)
    nuke.Root()["project_directory"].setValue(os.path.dirname(path))
    nuke.Root().setModified(False)


def open_file(filepath):

    def read_script(nuke_script):
        nuke.scriptClear()
        nuke.scriptReadFile(nuke_script)
        nuke.Root()["name"].setValue(nuke_script)
        nuke.Root()["project_directory"].setValue(os.path.dirname(nuke_script))
        nuke.Root().setModified(False)

    filepath = filepath.replace("\\", "/")

    # To remain in the same window, we have to clear the script and read
    # in the contents of the workfile.
    # Nuke Preferences can be read after the script is read.
    read_script(filepath)

    if not is_headless():
        autosave = nuke.toNode("preferences")["AutoSaveName"].evaluate()
        autosave_prmpt = "Autosave detected.\n" \
                         "Would you like to load the autosave file?"  # noqa
        if os.path.isfile(autosave) and nuke.ask(autosave_prmpt):
            try:
                # Overwrite the filepath with autosave
                shutil.copy(autosave, filepath)
                # Now read the (auto-saved) script again
                read_script(filepath)
            except shutil.Error as err:
                nuke.message(
                    "Detected autosave file could not be used.\n{}"

                    .format(err))

    return True


def current_file():
    current_file = nuke.root().name()

    # Unsaved current file
    if current_file == 'Root':
        return None

    return os.path.normpath(current_file).replace("\\", "/")


def work_root(session):

    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        path = os.path.join(work_dir, scene_dir)
    else:
        path = work_dir

    return os.path.normpath(path).replace("\\", "/")
