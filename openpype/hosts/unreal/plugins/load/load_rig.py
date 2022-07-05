# -*- coding: utf-8 -*-
"""Load Skeletal Meshes form FBX."""
import os

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline
import unreal  # noqa


class SkeletalMeshFBXLoader(plugin.Loader):
    """Load Unreal SkeletalMesh from FBX."""

    families = ["rig", "skeletalMesh"]
    label = "Import FBX Skeletal Mesh"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

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

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{root}/{asset}/{name}_v{version:03d}", suffix="")

        container_name += suffix

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            unreal.EditorAssetLibrary.make_directory(asset_dir)

            task = unreal.AssetImportTask()

            task.set_editor_property('filename', self.fname)
            task.set_editor_property('destination_path', asset_dir)
            task.set_editor_property('destination_name', asset_name)
            task.set_editor_property('replace_existing', False)
            task.set_editor_property('automated', True)
            task.set_editor_property('save', False)

            # set import options here
            options = unreal.FbxImportUI()
            options.set_editor_property('import_as_skeletal', True)
            options.set_editor_property('import_animations', False)
            options.set_editor_property('import_mesh', True)
            options.set_editor_property('import_materials', False)
            options.set_editor_property('import_textures', False)
            options.set_editor_property('skeleton', None)
            options.set_editor_property('create_physics_asset', False)

            options.set_editor_property(
                'mesh_type_to_import',
                unreal.FBXImportType.FBXIT_SKELETAL_MESH)

            options.skeletal_mesh_import_data.set_editor_property(
                'import_content_type',
                unreal.FBXImportContentType.FBXICT_ALL)
            # set to import normals, otherwise Unreal will compute them
            # and it will take a long time, depending on the size of the mesh
            options.skeletal_mesh_import_data.set_editor_property(
                'normal_import_method',
                unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)

            task.options = options
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])  # noqa: E501

            # Create Asset Container
            unreal_pipeline.create_container(
                container=container_name, path=asset_dir)

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        name = container["asset_name"]
        source_path = get_representation_path(representation)
        destination_path = container["namespace"]

        task = unreal.AssetImportTask()

        task.set_editor_property('filename', source_path)
        task.set_editor_property('destination_path', destination_path)
        task.set_editor_property('destination_name', name)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        # set import options here
        options = unreal.FbxImportUI()
        options.set_editor_property('import_as_skeletal', True)
        options.set_editor_property('import_animations', False)
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_materials', True)
        options.set_editor_property('import_textures', True)
        options.set_editor_property('skeleton', None)
        options.set_editor_property('create_physics_asset', False)

        options.set_editor_property('mesh_type_to_import',
                                    unreal.FBXImportType.FBXIT_SKELETAL_MESH)

        options.skeletal_mesh_import_data.set_editor_property(
            'import_content_type',
            unreal.FBXImportContentType.FBXICT_ALL
        )
        # set to import normals, otherwise Unreal will compute them
        # and it will take a long time, depending on the size of the mesh
        options.skeletal_mesh_import_data.set_editor_property(
            'normal_import_method',
            unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        )

        task.options = options
        # do import fbx and replace existing data
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])  # noqa: E501
        container_path = "{}/{}".format(container["namespace"],
                                        container["objectName"])
        # update metadata
        unreal_pipeline.imprint(
            container_path,
            {
                "representation": str(representation["_id"]),
                "parent": str(representation["parent"])
            })

        asset_content = unreal.EditorAssetLibrary.list_assets(
            destination_path, recursive=True, include_folder=True
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

    def remove(self, container):
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        unreal.EditorAssetLibrary.delete_directory(path)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            parent_path, recursive=False
        )

        if len(asset_content) == 0:
            unreal.EditorAssetLibrary.delete_directory(parent_path)
