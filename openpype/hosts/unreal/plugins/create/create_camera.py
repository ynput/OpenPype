import unreal
from unreal import EditorAssetLibrary as eal
from unreal import EditorLevelLibrary as ell

from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api.pipeline import instantiate


class CreateCamera(plugin.Creator):
    """Layout output for character rigs"""

    name = "layoutMain"
    label = "Camera"
    family = "camera"
    icon = "cubes"

    root = "/Game/OpenPype/Instances"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateCamera, self).__init__(*args, **kwargs)

    def process(self):
        data = self.data

        name = data["subset"]

        data["level"] = ell.get_editor_world().get_path_name()

        if not eal.does_directory_exist(self.root):
            eal.make_directory(self.root)

        factory = unreal.LevelSequenceFactoryNew()
        tools = unreal.AssetToolsHelpers().get_asset_tools()
        tools.create_asset(name, f"{self.root}/{name}", None, factory)

        asset_name = f"{self.root}/{name}/{name}.{name}"

        data["members"] = [asset_name]

        instantiate(f"{self.root}", name, data, None, self.suffix)
