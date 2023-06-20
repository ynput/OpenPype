""" OpenPype custom script for setting up write nodes for non-publish """
import os
import nuke
import nukescripts
from openpype.pipeline import Anatomy
from openpype.hosts.nuke.api.lib import (
    set_node_knobs_from_settings,
    get_nuke_imageio_settings
)


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


class WriteNodeKnobSettingPanel(nukescripts.PythonPanel):
    """ Write Node's Knobs Settings Panel """
    def __init__(self):
        nukescripts.PythonPanel.__init__(self, "Set Presets(Write Node)")

        knobs_value, _ = self.get_node_knobs_setting()
        # create knobs

        self.selected_preset_name = nuke.Enumeration_Knob(
            'preset_selector', 'presets', knobs_value)
        # add knobs to panel
        self.addKnob(self.selected_preset_name)

    def process(self):
        """ Process the panel values. """
        write_selected_nodes = [
            s for s in nuke.selectedNodes() if s.Class() == "Write"]

        node_knobs = self.selected_preset_name.value()
        ext = None
        knobs = knobs_setting["knobs"]
        knobs_value, node_knobs_settings = (
            self.get_node_knobs_setting(node_knobs)
        )

        if node_knobs and knobs_value:
            if not node_knobs_settings:
                nuke.message("No knobs value found in subset group..\nDefault setting will be used..")  # noqa
            else:
                knobs = node_knobs_settings

        ext_knob_list = [knob for knob in knobs if knob["name"] == "file_type"]
        if not ext_knob_list:
            nuke.message("ERROR: No file type found in the subset's knobs.\nPlease add one to complete setting up the node")   # noqa
            return
        else:
            for knob in ext_knob_list:
                ext = knob["value"]

        anatomy = Anatomy()

        frame_padding = int(
            anatomy.templates["render"].get(
                "frame_padding"
            )
        )
        for write_node in write_selected_nodes:
            # data for mapping the path
            data = {
                "work": os.getenv("AVALON_WORKDIR"),
                "subset": write_node["name"].value(),
                "frame": "#" * frame_padding,
                "ext": ext
            }
            file_path = temp_rendering_path_template.format(**data)
            file_path = file_path.replace("\\", "/")
            write_node["file"].setValue(file_path)
            set_node_knobs_from_settings(write_node, knobs)

    def get_node_knobs_setting(self, value=None):
        knobs_value = []
        knobs_nodes = []
        settings = [
            node
            for node in get_nuke_imageio_settings()["nodes"]["overrideNodes"]
        ]
        if not settings:
            return

        for i, _ in enumerate(settings):
            if value in settings[i]["subsets"]:
                knobs_nodes = settings[i]["knobs"]

        for setting in settings:
            if setting["nukeNodeClass"] == "Write" and setting["subsets"]:
                for knob in setting["subsets"]:
                    knobs_value.append(knob)

        return knobs_value, knobs_nodes


def main():
    p_ = WriteNodeKnobSettingPanel()
    if p_.showModalDialog():
        print(p_.process())
