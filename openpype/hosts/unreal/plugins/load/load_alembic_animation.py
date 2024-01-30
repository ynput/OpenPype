# -*- coding: utf-8 -*-
"""Load Alembic Animation."""
import os

from openpype.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline
import unreal  # noqa


class AnimationAlembicLoader(plugin.Loader):
    """Load Unreal SkeletalMesh from Alembic"""

    families = ["animation"]
    label = "Import Alembic Animation"
    representations = ["abc"]
    icon = "cube"
    color = "orange"

    def get_task(self, filename, asset_dir, asset_name, replace):
        task = unreal.AssetImportTask()
        options = unreal.AbcImportSettings()
        sm_settings = unreal.AbcStaticMeshSettings()
        conversion_settings = unreal.AbcConversionSettings(
            preset=unreal.AbcConversionPreset.CUSTOM,
            flip_u=False, flip_v=False,
            rotation=[0.0, 0.0, 0.0],
            scale=[1.0, 1.0, -1.0])

        task.set_editor_property('filename', filename)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('replace_existing', replace)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        options.set_editor_property(
            'import_type', unreal.AlembicImportType.SKELETAL)

        options.static_mesh_settings = sm_settings
        options.conversion_settings = conversion_settings
        task.options = options

        return task

    def load(self, context, name, namespace, data):
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
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """

        # Create directory for asset and ayon container
        root = unreal_pipeline.AYON_ASSET_DIR
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)
        version = context.get('version')
        # Check if version is hero version and use different name
        if not version.get("name") and version.get('type') == "hero_version":
            name_version = f"{name}_hero"
        else:
            name_version = f"{name}_v{version.get('name'):03d}"

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{root}/{asset}/{name_version}", suffix="")

        container_name += suffix

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            unreal.EditorAssetLibrary.make_directory(asset_dir)

            path = self.filepath_from_context(context)
            task = self.get_task(path, asset_dir, asset_name, False)

            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            asset_tools.import_asset_tasks([task])

            # Create Asset Container
            unreal_pipeline.create_container(
                container=container_name, path=asset_dir)

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
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
            f"{asset_dir}/{container_name}", data)

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

        task = self.get_task(source_path, destination_path, name, True)

        # do import fbx and replace existing data
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        asset_tools.import_asset_tasks([task])

        container_path = f"{container['namespace']}/{container['objectName']}"

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
