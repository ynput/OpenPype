import unreal
from unreal import EditorAssetLibrary as eal
from unreal import EditorLevelLibrary as ell

from openpype.hosts.unreal.api.plugin import Creator
from avalon.unreal import (
    instantiate,
)


class CreateCamera(Creator):
    """Layout output for character rigs"""

    name = "layoutMain"
    label = "Camera"
    family = "camera"
    icon = "cubes"

    root = "/Game/Avalon/Instances"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateCamera, self).__init__(*args, **kwargs)

    def process(self):
        data = self.data

        name = data["subset"]

        # selection = []
        # # if (self.options or {}).get("useSelection"):
        # #     sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
        # #     selection = [a.get_path_name() for a in sel_objects]

        # data["level"] = ell.get_editor_world().get_path_name()

        data["level"] = ell.get_editor_world().get_path_name()

        # if (self.options or {}).get("useSelection"):
        #     # Set as members the selected actors
        #     for actor in ell.get_selected_level_actors():
        #         data["members"].append("{}.{}".format(
        #             actor.get_outer().get_name(), actor.get_name()))

        if not eal.does_directory_exist(self.root):
            eal.make_directory(self.root)

        factory = unreal.LevelSequenceFactoryNew()
        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset = tools.create_asset(name, f"{self.root}/{name}", None, factory)

        asset_name = f"{self.root}/{name}/{name}.{name}"

        data["members"] = [asset_name]

        instantiate(f"{self.root}", name, data, None, self.suffix)
