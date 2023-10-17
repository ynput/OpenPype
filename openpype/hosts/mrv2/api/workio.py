"""Host API required Work Files tool"""
import os
import logging
from mrv2 import cmd


log = logging.getLogger(__name__)


def file_extensions():
    return [".mrv2s"]


def has_unsaved_changes():
    # MRV2 tracks no save state for the session so we always return True
    return True


def save_file(filepath):
    return cmd.saveSessionAs(filepath)


def open_file(filepath):
    if hasattr(cmd, "openSession"):
        fn = cmd.openSession
    else:
        # Prior to mrv 0.8 there was a typo in the exposed python function
        # See: https://github.com/ggarra13/mrv2/issues/123
        fn = cmd.oepnSession
    return fn(filepath)


def current_file():
    # Backwards compatibility before MRV2 0.8
    # See: https://github.com/ggarra13/mrv2/issues/124
    if not hasattr(cmd, "currentSession"):
        log.warning("mrv2 version lower than 0.8 does not support "
                    "'cmd.currentSession()'. Please update to a newer"
                    "version of mrv2.")
        return

    return cmd.currentSession()


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
