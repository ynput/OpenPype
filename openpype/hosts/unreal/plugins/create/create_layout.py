# -*- coding: utf-8 -*-
from unreal import EditorLevelLibrary

from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api.pipeline import instantiate


class CreateLayout(plugin.Creator):
    """Layout output for character rigs."""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    root = "/Game"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateLayout, self).__init__(*args, **kwargs)

    def process(self):
        data = self.data

        name = data["subset"]

        selection = []
        # if (self.options or {}).get("useSelection"):
        #     sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
        #     selection = [a.get_path_name() for a in sel_objects]

        data["level"] = EditorLevelLibrary.get_editor_world().get_path_name()

        data["members"] = []

        if (self.options or {}).get("useSelection"):
            # Set as members the selected actors
            for actor in EditorLevelLibrary.get_selected_level_actors():
                data["members"].append("{}.{}".format(
                    actor.get_outer().get_name(), actor.get_name()))

        instantiate(self.root, name, data, selection, self.suffix)
