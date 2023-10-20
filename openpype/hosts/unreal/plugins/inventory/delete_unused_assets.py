import unreal

from openpype.hosts.unreal.api.pipeline import delete_asset_if_unused
from openpype.pipeline import InventoryAction



class DeleteUnusedAssets(InventoryAction):
    """Delete all the assets that are not used in any level.
    """

    label = "Delete Unused Assets"
    icon = "trash"
    color = "red"
    order = 1

    def process(self, containers):
        allowed_families = ["model", "rig"]

        for container in containers:
            container_dir = container.get("namespace")
            if container.get("family") not in allowed_families:
                unreal.log_warning(
                    f"Container {container_dir} is not supported.")
                continue

            asset_content = unreal.EditorAssetLibrary.list_assets(
                container_dir, recursive=True, include_folder=False
            )

            delete_asset_if_unused(container, asset_content)
