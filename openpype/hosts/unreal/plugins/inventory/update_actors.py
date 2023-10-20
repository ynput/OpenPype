import unreal

from openpype.hosts.unreal.api.pipeline import (
    ls,
    replace_static_mesh_actors,
    replace_skeletal_mesh_actors,
    replace_geometry_cache_actors,
)
from openpype.pipeline import InventoryAction


def update_assets(containers, selected):
    allowed_families = ["model", "rig"]

    # Get all the containers in the Unreal Project
    all_containers = ls()

    for container in containers:
        container_dir = container.get("namespace")
        if container.get("family") not in allowed_families:
            unreal.log_warning(
                f"Container {container_dir} is not supported.")
            continue

        # Get all containers with same asset_name but different objectName.
        # These are the containers that need to be updated in the level.
        sa_containers = [
            i
            for i in all_containers
            if (
                i.get("asset_name") == container.get("asset_name") and
                i.get("objectName") != container.get("objectName")
            )
        ]

        asset_content = unreal.EditorAssetLibrary.list_assets(
            container_dir, recursive=True, include_folder=False
        )

        # Update all actors in level
        for sa_cont in sa_containers:
            sa_dir = sa_cont.get("namespace")
            old_content = unreal.EditorAssetLibrary.list_assets(
                sa_dir, recursive=True, include_folder=False
            )

            if container.get("family") == "rig":
                replace_skeletal_mesh_actors(
                    old_content, asset_content, selected)
                replace_static_mesh_actors(
                    old_content, asset_content, selected)
            elif container.get("family") == "model":
                if container.get("loader") == "PointCacheAlembicLoader":
                    replace_geometry_cache_actors(
                        old_content, asset_content, selected)
                else:
                    replace_static_mesh_actors(
                        old_content, asset_content, selected)

            unreal.EditorLevelLibrary.save_current_level()


class UpdateAllActors(InventoryAction):
    """Update all the Actors in the current level to the version of the asset
    selected in the scene manager.
    """

    label = "Replace all Actors in level to this version"
    icon = "arrow-up"

    def process(self, containers):
        update_assets(containers, False)


class UpdateSelectedActors(InventoryAction):
    """Update only the selected Actors in the current level to the version
    of the asset selected in the scene manager.
    """

    label = "Replace selected Actors in level to this version"
    icon = "arrow-up"

    def process(self, containers):
        update_assets(containers, True)
