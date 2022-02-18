"""Host API required Work Files tool"""
import sys
import os
from avalon import api
from .pipeline import get_current_comp


def file_extensions():
    return api.HOST_WORKFILE_EXTENSIONS["fusion"]


def has_unsaved_changes():
    comp = get_current_comp()
    return comp.GetAttrs()["COMPB_Modified"]


def save_file(filepath):
    comp = get_current_comp()
    comp.Save(filepath)


def open_file(filepath):
    # Hack to get fusion, see
    #   openpype.hosts.fusion.api.pipeline.get_current_comp()
    fusion = getattr(sys.modules["__main__"], "fusion", None)

    return fusion.LoadComp(filepath)


def current_file():
    comp = get_current_comp()
    current_filepath = comp.GetAttrs()["COMPS_FileName"]
    if not current_filepath:
        return None

    return current_filepath


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
