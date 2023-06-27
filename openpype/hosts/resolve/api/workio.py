"""Host API required Work Files tool"""

import os
from openpype.lib import Logger
from .lib import (
    get_project_manager,
    get_current_project
)


log = Logger.get_logger(__name__)

exported_project_ext = ".drp"


def file_extensions():
    return [exported_project_ext]


def has_unsaved_changes():
    get_project_manager().SaveProject()
    return False


def save_file(filepath):
    pm = get_project_manager()
    file = os.path.basename(filepath)
    fname, _ = os.path.splitext(file)
    project = get_current_project()
    name = project.GetName()

    response = False
    if name == "Untitled Project":
        response = pm.CreateProject(fname)
        log.info("New project created: {}".format(response))
        pm.SaveProject()
    elif name != fname:
        response = project.SetName(fname)
        log.info("Project renamed: {}".format(response))

    if response:
        # only export if project was saved or renamed
        exported = pm.ExportProject(fname, filepath)
        log.info("Project exported: {}".format(exported))


def open_file(filepath):
    """
    Loading project
    """

    from . import bmdvr

    pm = get_project_manager()
    page = bmdvr.GetCurrentPage()
    if page is not None:
        # Save current project only if Resolve has an active page, otherwise
        # we consider Resolve being in a pre-launch state (no open UI yet)
        project = pm.GetCurrentProject()
        print(f"Saving current project: {project}")
        pm.SaveProject()

    file = os.path.basename(filepath)
    fname, _ = os.path.splitext(file)

    try:
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
    fname = name + exported_project_ext
    current_file = os.path.join(current_dir, fname)
    if current_file:
        return os.path.normpath(current_file)


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
