import os

import hiero

from avalon import api


def file_extensions():
    return [".hrox"]


def has_unsaved_changes():
    # There are no methods for querying unsaved changes to a project, so
    # enforcing to always save.
    return True


def save_file(filepath):
    project = hiero.core.projects()[-1]
    if project:
        project.saveAs(filepath)
    else:
        project = hiero.core.newProject()
        project.saveAs(filepath)


def open_file(filepath):
    hiero.core.openProject(filepath)
    return True


def current_file():
    current_file = hiero.core.projects()[-1].path()
    normalised = os.path.normpath(current_file)

    # Unsaved current file
    if normalised == "":
        return None

    return normalised


def work_root():
    return os.path.normpath(api.Session["AVALON_WORKDIR"]).replace("\\", "/")
