"""Host API required Work Files tool"""
import os
import nuke


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


def open_file(filepath, allow_autosave=True):
    filepath = filepath.replace("\\", "/")

    # To remain in the same window, we have to clear the script and read
    # in the contents of the workfile.
    nuke.scriptClear()
    if allow_autosave:
        autosave = "{}.autosave".format(filepath)
        autosave_prmpt = "Autosave detected.\nWould you like to load the autosave file?"       # noqa
        if os.path.isfile(autosave) and nuke.ask(autosave_prmpt):
            filepath = autosave

    nuke.scriptReadFile(filepath)
    nuke.Root()["name"].setValue(filepath)
    nuke.Root()["project_directory"].setValue(os.path.dirname(filepath))
    nuke.Root().setModified(False)
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
