""" OpenPype custom script for setting up write nodes for non-publish """
import os
import nuke
import nukescripts
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
        nukescripts.PythonPanel.__init__(self, "Set Knobs Value(Write Node)")

        knobs_value = self.get_node_knobs_override()
        # create knobs

        self.typeKnob = nuke.Enumeration_Knob(
            'override_subsets', 'override subsets', knobs_value)
        # add knobs to panel
        self.addKnob(self.typeKnob)

    def process(self):
        """ Process the panel values. """
        write_selected_nodes = [
            s for s in nuke.selectedNodes() if s.Class() == "Write"]

        node_knobs = self.typeKnob.value()
        ext = None
        knobs = None
        if node_knobs:
            knobs = self.get_node_knobs_setting(node_knobs)
            if not knobs:
                nuke.message("No knobs value found in subset group..\nDefault setting will be used..")  # noqa
                knobs = knobs_setting["knobs"]
        else:
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

    def get_node_knobs_setting(self, value):
        settings = [
            node for node in get_nuke_imageio_settings()["nodes"]["overrideNodes"]
        ]
        if not settings:
            return
        for i, setting in enumerate(settings):
            if value in settings[i]["subsets"]:
                return settings[i]["knobs"]

    def get_node_knobs_override(self):
        knobs_value = []
        settings = [
            node for node in get_nuke_imageio_settings()["nodes"]["overrideNodes"]
        ]
        if not settings:
            return

        for setting in settings:
            if setting["nukeNodeClass"] == "Write" and setting["subsets"]:
                for knob in setting["subsets"]:
                    knobs_value.append(knob)
        return knobs_value

def main():
    p_ = WriteNodeKnobSettingPanel()
    if p_.showModalDialog():
        print(p_.process())
