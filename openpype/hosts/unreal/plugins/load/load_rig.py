# -*- coding: utf-8 -*-
"""Load Skeletal Meshes form FBX."""
import os

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as up


class SkeletalMeshFBXLoader(plugin.Loader):
    """Load Unreal SkeletalMesh from FBX."""

    families = ["rig", "skeletalMesh"]
    label = "Import FBX Skeletal Mesh"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def _import_fbx_task(
            self, filename, destination_path, destination_name, replace):
        task_properties = [
            ("filename", up.format_string(filename)),
            ("destination_path", up.format_string(destination_path)),
            ("destination_name", up.format_string(destination_name)),
            ("replace_existing", str(replace)),
            ("automated", "True"),
            ("save", "True")
        ]

        options_properties = [
            ("import_as_skeletal", "True"),
            ("import_animations", "False"),
            ("import_mesh", "True"),
            ("import_materials", "False"),
            ("import_textures", "False"),
            ("skeleton", "None"),
            ("create_physics_asset", "False"),
            ("mesh_type_to_import",
                "unreal.FBXImportType.FBXIT_SKELETAL_MESH")
        ]

        options_extra_properties = [
            (
                "skeletal_mesh_import_data",
                "import_content_type",
                "unreal.FBXImportContentType.FBXICT_ALL"
            ),
            (
                "skeletal_mesh_import_data",
                "normal_import_method",
                "unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS"
            )
        ]

        up.send_request(
            "import_fbx_task",
            params=[
                str(task_properties),
                str(options_properties),
                str(options_extra_properties)
            ])

    def load(self, context, name, namespace, options):
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

        Returns:
            list(str): list of container content

        """
        # Create directory for asset and OpenPype container
        root = "/Game/OpenPype/Assets"
        if options and options.get("asset_dir"):
            root = options["asset_dir"]
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)
        version = context.get('version').get('name')

        asset_dir, container_name = up.send_request_literal(
            "create_unique_asset_name", params=[root, asset, name, version])

        container_name += suffix

        if not up.send_request_literal(
                "does_directory_exist", params=[asset_dir]):
            up.send_request("make_directory", params=[asset_dir])

            self._import_fbx_task(self.fname, asset_dir, asset_name, False)

            # Create Asset Container
            up.send_request(
                "create_container", params=[container_name, asset_dir])

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": str(context["representation"]["_id"]),
            "parent": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"]
        }
        up.send_request(
            "imprint", params=[f"{asset_dir}/{container_name}", str(data)])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "True"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

        return asset_content

    def update(self, container, representation):
        filename = get_representation_path(representation)
        asset_dir = container["namespace"]
        asset_name = container["asset_name"]
        container_name = container['objectName']

        self._import_fbx_task(filename, asset_dir, asset_name, True)

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"])
        }
        up.send_request(
            "imprint", params=[f"{asset_dir}/{container_name}", str(data)])

        asset_content = up.send_request_literal(
            "list_assets", params=[asset_dir, "True", "True"])

        up.send_request(
            "save_listed_assets", params=[str(asset_content)])

    def remove(self, container):
        path = container["namespace"]

        up.send_request(
            "remove_asset", params=[path])
