import os
import hiero
from avalon import api
from pype.api import Logger


log = Logger().get_logger(__name__, "nukestudio")


def file_extensions():
    return api.HOST_WORKFILE_EXTENSIONS["nukestudio"]


def has_unsaved_changes():
    # There are no methods for querying unsaved changes to a project, so
    # enforcing to always save.
    # but we could at least check if a current open script has a path
    project = hiero.core.projects()[-1]
    if project.path():
        return True
    else:
        return False


def save_file(filepath):
    file = os.path.basename(filepath)
    project = hiero.core.projects()[-1]

    if project:
        log.info("Saving project: `{}` as '{}'".format(project.name(), file))
        project.saveAs(filepath)
    else:
        log.info("Creating new project...")
        project = hiero.core.newProject()
        project.saveAs(filepath)


def open_file(filepath):
    """Manually fire the kBeforeProjectLoad event in order to work around a bug in Hiero.
    The Foundry has logged this bug as:
      Bug 40413 - Python API - kBeforeProjectLoad event type is not triggered
      when calling hiero.core.openProject() (only triggered through UI)
    It exists in all versions of Hiero through (at least) v1.9v1b12.

    Once this bug is fixed, a version check will need to be added here in order to
    prevent accidentally firing this event twice. The following commented-out code
    is just an example, and will need to be updated when the bug is fixed to catch the
    correct versions."""
    # if (hiero.core.env['VersionMajor'] < 1 or
    #     hiero.core.env['VersionMajor'] == 1 and hiero.core.env['VersionMinor'] < 10:
    hiero.core.events.sendEvent("kBeforeProjectLoad", None)

    project = hiero.core.projects()[-1]

    # open project file
    hiero.core.openProject(filepath.replace(os.path.sep, "/"))

    # close previous project
    project.close()



    return True


def current_file():
    current_file = hiero.core.projects()[-1].path()
    normalised = os.path.normpath(current_file)

    # Unsaved current file
    if normalised == "":
        return None

    return normalised


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
