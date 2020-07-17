"""Host API required Work Files tool"""

import os
from pypeapp import Logger
from . import (
    get_project_manager,
    get_current_project,
    set_project_manager_to_folder_name
)


log = Logger().get_logger(__name__, "resolve")

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
    project = get_current_project()
    name = project.GetName()

    if "Untitled Project" not in name:
        log.info("Saving project: `{}` as '{}'".format(name, file))
        pm.ExportProject(name, filepath)
    else:
        log.info("Creating new project...")
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
    log.info(f"Test `pm`: {pm}")
    pm.SaveProject()

    try:
        log.info(f"Test `dname`: {dname}")
        if not set_project_manager_to_folder_name(dname):
            raise
        # load project from input path
        project = pm.LoadProject(fname)
        log.info(f"Project {project.GetName()} opened...")
        return True
    except AttributeError:
        log.warning((f"Project with name `{fname}` does not exist! It will "
                     f"be imported from {filepath} and then loaded..."))
        if pm.ImportProject(filepath):
            # load project from input path
            project = pm.LoadProject(fname)
            log.info(f"Project imported/loaded {project.GetName()}...")
            return True
        else:
            return False


def current_file():
    pm = get_project_manager()
    current_dir = os.getenv("AVALON_WORKDIR")
    project = pm.GetCurrentProject()
    name = project.GetName()
    fname = name + exported_projet_ext
    current_file = os.path.join(current_dir, fname)
    normalised = os.path.normpath(current_file)

    # Unsaved current file
    if normalised == "":
        return None

    return normalised


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
