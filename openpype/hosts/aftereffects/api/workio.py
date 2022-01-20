"""Host API required Work Files tool"""
import os

from .launch_logic import get_stub
from avalon import api


def _active_document():
    document_name = get_stub().get_active_document_name()
    if not document_name:
        return None

    return document_name


def file_extensions():
    return api.HOST_WORKFILE_EXTENSIONS["aftereffects"]


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
    except Exception:
        pass

    return None


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
