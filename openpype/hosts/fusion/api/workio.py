"""Host API required Work Files tool"""
import os

from .lib import get_fusion_module, get_current_comp


def file_extensions():
    return [".comp"]


def has_unsaved_changes():
    comp = get_current_comp()
    return comp.GetAttrs()["COMPB_Modified"]


def save_file(filepath):
    comp = get_current_comp()
    comp.Save(filepath)


def open_file(filepath):
    fusion = get_fusion_module()
    return fusion.LoadComp(filepath)


def current_file():
    comp = get_current_comp()
    current_filepath = comp.GetAttrs()["COMPS_FileName"]
    return current_filepath or None


def work_root(session):
    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
