"""Host API required Work Files tool"""
import os

from openpype.pipeline import HOST_WORKFILE_EXTENSIONS
from .launch_logic import get_stub


def file_extensions():
    return HOST_WORKFILE_EXTENSIONS["aftereffects"]


def has_unsaved_changes():
    if _active_document():
        return not get_stub().is_saved()

    return False


def save_file(filepath):
    get_stub().saveAs(filepath, True)


def open_file(filepath):
    get_stub().open(filepath)

    return True


def current_file():
    try:
        full_name = get_stub().get_active_document_full_name()
        if full_name and full_name != "null":
            return os.path.normpath(full_name).replace("\\", "/")
    except ValueError:
        print("Nothing opened")
        pass

    return None


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")


def _active_document():
    # TODO merge with current_file - even in extension
    document_name = None
    try:
        document_name = get_stub().get_active_document_name()
    except ValueError:
        print("Nothing opened")
        pass

    return document_name