import os
import nuke
from openpype.client import get_asset_by_name, get_project
from openpype.pipeline import Anatomy, legacy_io
from openpype.pipeline.template_data import get_template_data
from openpype.hosts.nuke.api.lib import (
    get_imageio_node_setting,
    set_node_knobs_from_settings)


def main():
    project_name = legacy_io.Session["AVALON_PROJECT"]
    asset_name = legacy_io.Session["AVALON_ASSET"]
    task_name = legacy_io.Session["AVALON_TASK"]
    # fetch asset docs
    asset_doc = get_asset_by_name(project_name, asset_name)

    # get task type to fill the timer tag
    # template = "{root[work]}/{project[name]}/{hierarchy}/{asset}"
    anatomy = Anatomy(project_name)
    project_doc = get_project(project_name)
    template_data = get_template_data(project_doc, asset_doc)
    template_data["root"] = anatomy.roots
    template_data["task"] = {"name": task_name}

    padding = int(
        anatomy.templates["render"]["frame_padding"]
    )
    version_int = 0
    version_int += 1
    if version_int:
        version_int += 1

    node_settings = get_imageio_node_setting(
        "Write", "CreateWriteRender", subset=None)

    ext = None
    for knob in node_settings["knobs"]:
        if knob["name"] == "file_type":
            ext = knob["value"]
    data = {
        "asset": asset_name,
        "task": task_name,
        "subset": "non_publish_render",
        "frame": "#" * padding,
        "ext": ext
    }

    write_selected_nodes = [
        s for s in nuke.selectedNodes() if s.Class() == "Write"]

    for i in range(len(write_selected_nodes)):
        data.update({"version": i})
        data.update(template_data)

    anatomy_filled = anatomy.format(data)
    folder = anatomy_filled["work"]["folder"]
    render_folder = os.path.join(folder, "render_no_publish")
    filename = anatomy_filled["render"]["file"]
    file_path = os.path.join(render_folder, filename)
    file_path = file_path.replace("\\", "/")

    knobs = node_settings["knobs"]
    for w in write_selected_nodes:
        w["file"].setValue(file_path)
        set_node_knobs_from_settings(w, knobs)
