"""Host API required Work Files tool"""

import os
from openpype.api import Logger
# from .. import (
#     get_project_manager,
#     get_current_project
# )


log = Logger.get_logger(__name__)

exported_projet_ext = ".otoc"


def file_extensions():
    return [exported_projet_ext]


def has_unsaved_changes():
    pass


def save_file(filepath):
    pass


def open_file(filepath):
    pass


def current_file():
    pass


def work_root(session):
    return os.path.normpath(session["AVALON_WORKDIR"]).replace("\\", "/")
