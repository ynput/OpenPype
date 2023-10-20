"""Host API required Work Files tool"""
import os
import logging
from mrv2 import session


log = logging.getLogger(__name__)


def file_extensions():
    return [".mrv2s"]


def has_unsaved_changes():
    # MRV2 tracks no save state for the session so we always return True
    return True


def save_file(filepath):
    success = session.save(filepath)
    if success:
        session.setCurrent(filepath)
    return success


def open_file(filepath):
    return session.load(filepath)


def current_file():
    return session.current()


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
