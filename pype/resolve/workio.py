"""Host API required Work Files tool"""

import os
import sys
from pypeapp import Logger
from .utils import get_resolve_module

log = Logger().get_logger(__name__, "nukestudio")

exported_projet_ext = ".drp"

self = sys.modules[__name__]
self.pm = None


def get_project_manager():
    if not self.pm:
        resolve = get_resolve_module()
        self.pm = resolve.GetProjectManager()
    return self.pm


def file_extensions():
    return [exported_projet_ext]


def has_unsaved_changes():
    get_project_manager().SaveProject()
    return False


def save_file(filepath):
    pm = get_project_manager()
    file = os.path.basename(filepath)
    fname, _ = os.path.splitext(file)
    project = pm.GetCurrentProject()
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

    # deal with current project
    project = pm.GetCurrentProject()
    pm.SaveProject()
    pm.CloseProject(project)

    try:
        # load project from input path
        project = pm.LoadProject(fname)
        log.info(f"Project {project.GetName()} opened...")
        return True
    except NameError as E:
        log.error(f"Project with name `{fname}` does not exist!\n\nError: {E}")
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
