import os
import nuke
from openpype.hosts.nuke.api.lib import set_node_knobs_from_settings


frame_padding = 5
temp_rendering_path_template = (
    "{work}/renders/nuke/{subset}/{subset}.{frame}.{ext}")

knobs_setting = {
    "knobs": [
        {
            "type": "text",
            "name": "file_type",
            "value": "exr"
        },
        {
            "type": "text",
            "name": "datatype",
            "value": "16 bit half"
        },
        {
            "type": "text",
            "name": "compression",
            "value": "Zip (1 scanline)"
        },
        {
            "type": "bool",
            "name": "autocrop",
            "value": True
        },
        {
            "type": "color_gui",
            "name": "tile_color",
            "value": [
                186,
                35,
                35,
                255
            ]
        },
        {
            "type": "text",
            "name": "channels",
            "value": "rgb"
        },
        {
            "type": "bool",
            "name": "create_directories",
            "value": True
        }
    ]
}


def main():
    write_selected_nodes = [
        s for s in nuke.selectedNodes() if s.Class() == "Write"]

    ext = None
    knobs = knobs_setting["knobs"]
    for knob in knobs:
        if knob["name"] == "file_type":
            ext = knob["value"]
    for w in write_selected_nodes:
        # data for mapping the path
        data = {
            "work": os.getenv("AVALON_WORKDIR"),
            "subset": w["name"].value(),
            "frame": "#" * frame_padding,
            "ext": ext
        }
        file_path = temp_rendering_path_template.format(**data)
        file_path = file_path.replace("\\", "/")
        w["file"].setValue(file_path)
        set_node_knobs_from_settings(w, knobs)
