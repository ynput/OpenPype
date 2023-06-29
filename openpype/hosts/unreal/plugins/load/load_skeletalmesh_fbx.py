# -*- coding: utf-8 -*-
"""Load Skeletal Meshes form FBX."""

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class SkeletalMeshFBXLoader(UnrealBaseLoader):
    """Load Unreal SkeletalMesh from FBX."""

    families = ["rig", "skeletalMesh"]
    label = "Import FBX Skeletal Mesh"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    @staticmethod
    def _import_fbx_task(
        filename, destination_path, destination_name, replace
    ):
        params = {
            "filename": filename,
            "destination_path": destination_path,
            "destination_name": destination_name,
            "replace_existing": replace,
            "automated": True,
            "save": True,
            "options_properties": [
                ["import_animations", "False"],
                ["import_mesh", "True"],
                ["import_materials", "False"],
                ["import_textures", "False"],
                ["skeleton", "None"],
                ["create_physics_asset", "False"],
                ["mesh_type_to_import",
                 "unreal.FBXImportType.FBXIT_SKELETAL_MESH"]
            ],
            "sub_options_properties": [
                [
                    "skeletal_mesh_import_data",
                    "import_content_type",
                    "unreal.FBXImportContentType.FBXICT_ALL"
                ],
                [
                    "skeletal_mesh_import_data",
                    "normal_import_method",
                    "unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS"
                ]
            ]
        }

        send_request("import_fbx_task", params=params)

    def load(self, context, name=None, namespace=None, options=None):
        """Load and containerise representation into Content Browser.

        This is two step process. First, import FBX to temporary path and
        then call `containerise()` on it - this moves all content to new
        directory and then it will create AssetContainer there and imprint it
        with metadata. This will mark this path as container.

        Args:
            context (dict): application context
            name (str): subset name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            options (dict): Those would be data to be imprinted. This is not
                            used now, data are imprinted by `containerise()`.
        """
        # Create directory for asset and OpenPype container
        root = f"{self.root}/Assets"
        if options and options.get("asset_dir"):
            root = options["asset_dir"]
        asset = context.get('asset').get('name')
        asset_name = f"{asset}_{name}" if asset else f"{name}"
        version = context.get('version').get('name')

        asset_dir, container_name = send_request(
            "create_unique_asset_name", params={
                "root": root,
                "asset": asset,
                "name": name,
                "version": version})

        if not send_request(
                "does_directory_exist", params={"directory_path": asset_dir}):
            send_request(
                "make_directory", params={"directory_path": asset_dir})

            self._import_fbx_task(self.fname, asset_dir, asset_name, False)

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": self.__class__.__name__,
            "representation": str(context["representation"]["_id"]),
            "parent": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"]
        }

        containerise(asset_dir, container_name, data)

        return send_request(
            "list_assets", params={
                "directory_path": asset_dir,
                "recursive": True,
                "include_folder": True})

    def update(self, container, representation):
        filename = get_representation_path(representation)
        asset_dir = container["namespace"]
        asset_name = container["asset_name"]

        self._import_fbx_task(filename, asset_dir, asset_name, True)

        super(UnrealBaseLoader, self).update(container, representation)
