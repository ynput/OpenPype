"""Host API required Work Files tool"""
import os

from mrv2 import cmd


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
    # It seems that MRV2 has no equivalent to the 'current session'?
    # See: https://github.com/ggarra13/mrv2/issues/124
    return None


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
