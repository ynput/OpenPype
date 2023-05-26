"""Host API required Work Files tool"""

import os
from openpype.lib import Logger
from .lib import (
    get_project_manager,
    get_current_project,
    set_project_manager_to_folder_name
)


log = Logger.get_logger(__name__)

exported_projet_ext = ".drp"


def file_extensions():
    return [exported_projet_ext]


def has_unsaved_changes():
    get_project_manager().SaveProject()
    return False


def save_file(filepath):
    pm = get_project_manager()
    file = os.path.basename(filepath)
    fname, _ = os.path.splitext(file)
    dname, _ = fname.split("_v")
    project = get_current_project()
    name = project.GetName()

    if fname != name:
        # nest project version iteration in own folder
        if not set_project_manager_to_folder_name(dname):
            raise

        log.info(f"Creating new project {fname}...")
        pm.CreateProject(fname)
        pm.ExportProject(name, filepath)


def open_file(filepath):
    """
    Loading project
    """
    pm = get_project_manager()
    file = os.path.basename(filepath)
    fname, _ = os.path.splitext(file)
    dname, _ = fname.split("_v")

    # deal with current project
    project = pm.GetCurrentProject()
    if project.GetName() != "Untitled Project":
        log.info(f"Saving project: `{project.GetName()}`")
        pm.SaveProject()

    try:
        log.info(f"Test `dname`: {dname}")
        if not set_project_manager_to_folder_name(dname):
            raise
        # load project from input path
        project = pm.LoadProject(fname)
        log.info(f"Project {project.GetName()} opened...")

    except AttributeError:
        log.warning((f"Project with name `{fname}` does not exist! It will "
                     f"be imported from {filepath} and then loaded..."))
        if pm.ImportProject(filepath):
            # load project from input path
            project = pm.LoadProject(fname)
            log.info(f"Project imported/loaded {project.GetName()}...")
            return True
        return False
    return True


def current_file():
    pm = get_project_manager()
    current_dir = os.getenv("AVALON_WORKDIR")
    project = pm.GetCurrentProject()
    name = project.GetName()
    fname = name + exported_projet_ext
    current_file = os.path.join(current_dir, fname)

    # check if file exists
    if not current_file:
        return None

    return os.path.normpath(current_file)


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
