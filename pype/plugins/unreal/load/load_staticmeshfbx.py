from avalon import api
from avalon import unreal as avalon_unreal
import unreal
import time


class StaticMeshFBXLoader(api.Loader):
    """Load Unreal StaticMesh from FBX"""

    families = ["unrealStaticMesh"]
    label = "Import FBX Static Mesh"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def load(self, context, name, namespace, data):

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        temp_dir, temp_name = tools.create_unique_asset_name(
                "/Game/{}".format(name), "_TMP"
        )

        # asset_path = "/Game/{}".format(namespace)
        unreal.EditorAssetLibrary.make_directory(temp_dir)

        task = unreal.AssetImportTask()

        task.filename = self.fname
        task.destination_path = temp_dir
        task.destination_name = name
        task.replace_existing = False
        task.automated = True
        task.save = True

        # set import options here
        task.options = unreal.FbxImportUI()
        task.options.import_animations = False

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])  # noqa: E501

        imported_assets = unreal.EditorAssetLibrary.list_assets(
            temp_dir, recursive=True, include_folder=True
        )
        new_dir = avalon_unreal.containerise(
            name, namespace, imported_assets, context, self.__class__.__name__)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            new_dir, recursive=True, include_folder=True
        )

        unreal.EditorAssetLibrary.delete_directory(temp_dir)

        return asset_content
