"""Host API required Work Files tool"""
import os
import hiero


def file_extensions():
    return [".hrox"]


def has_unsaved_changes():
    return hiero.core.projects()[-1]


def save(filepath):
    project = hiero.core.projects()[-1]

    if project:
        project.saveAs(filepath)
    else:
        project = hiero.core.newProject()
        project.saveAs(filepath)


def open(filepath):
    try:
        hiero.core.openProject(filepath)
        return True
    except Exception as e:
        try:
            from PySide.QtGui import *
            from PySide.QtCore import *
        except:
            from PySide2.QtGui import *
            from PySide2.QtWidgets import *
            from PySide2.QtCore import *

        prompt = "Cannot open the selected file: `{}`".format(e)
        hiero.core.log.error(prompt)
        dialog = QMessageBox.critical(
            hiero.ui.mainWindow(), "Error", unicode(prompt))


def current_file():
    import os
    import hiero

    current_file = hiero.core.projects()[-1].path()
    normalised = os.path.normpath(current_file)

    # Unsaved current file
    if normalised is '':
        return "NOT SAVED"

    return normalised



def work_root():
    from avalon import api

    return os.path.normpath(api.Session["AVALON_WORKDIR"]).replace("\\", "/")
