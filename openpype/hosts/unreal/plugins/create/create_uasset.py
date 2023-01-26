"""Create UAsset."""
from pathlib import Path

import unreal

from openpype.hosts.unreal.api import pipeline
from openpype.pipeline import LegacyCreator


class CreateUAsset(LegacyCreator):
    """UAsset."""

    name = "UAsset"
    label = "UAsset"
    family = "uasset"
    icon = "cube"

    root = "/Game/OpenPype"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateUAsset, self).__init__(*args, **kwargs)

    def process(self):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        subset = self.data["subset"]
        path = f"{self.root}/PublishInstances/"

        unreal.EditorAssetLibrary.make_directory(path)

        selection = []
        if (self.options or {}).get("useSelection"):
            sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
            selection = [a.get_path_name() for a in sel_objects]

            if len(selection) != 1:
                raise RuntimeError("Please select only one object.")

            obj = selection[0]

            asset = ar.get_asset_by_object_path(obj).get_asset()
            sys_path = unreal.SystemLibrary.get_system_path(asset)

            if not sys_path:
                raise RuntimeError(
                    f"{Path(obj).name} is not on the disk. Likely it needs to"
                    "be saved first.")

            if Path(sys_path).suffix != ".uasset":
                raise RuntimeError(f"{Path(sys_path).name} is not a UAsset.")

        unreal.log("selection: {}".format(selection))
        container_name = f"{subset}{self.suffix}"
        pipeline.create_publish_instance(
            instance=container_name, path=path)

        data = self.data.copy()
        data["members"] = selection

        pipeline.imprint(f"{path}/{container_name}", data)
