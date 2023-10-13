# -*- coding: utf-8 -*-
"""Loader for Yeti Cache."""
import os
import json

from openpype.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline
import unreal  # noqa


class YetiLoader(plugin.Loader):
    """Load Yeti Cache"""

    families = ["yeticacheUE"]
    label = "Import Yeti"
    representations = ["abc"]
    icon = "pagelines"
    color = "orange"

    @staticmethod
    def get_task(filename, asset_dir, asset_name, replace):
        task = unreal.AssetImportTask()
        options = unreal.AbcImportSettings()

        task.set_editor_property('filename', filename)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('replace_existing', replace)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        task.options = options

        return task

    @staticmethod
    def is_groom_module_active():
        """
        Check if Groom plugin is active.

        This is a workaround, because the Unreal python API don't have
        any method to check if plugin is active.
        """
        prj_file = unreal.Paths.get_project_file_path()

        with open(prj_file, "r") as fp:
            data = json.load(fp)

        plugins = data.get("Plugins")

        if not plugins:
            return False

        plugin_names = [p.get("Name") for p in plugins]

        return "HairStrands" in plugin_names

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
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content

        """
        # Check if Groom plugin is active
        if not self.is_groom_module_active():
            raise RuntimeError("Groom plugin is not activated.")

        # Create directory for asset and Ayon container
        root = "/Game/Ayon/Assets"
        asset = context.get('asset').get('name')
        suffix = "_CON"
        asset_name = f"{asset}_{name}" if asset else f"{name}"

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            f"{root}/{asset}/{name}", suffix="")

        unique_number = 1
        while unreal.EditorAssetLibrary.does_directory_exist(
            f"{asset_dir}_{unique_number:02}"
        ):
            unique_number += 1

        asset_dir = f"{asset_dir}_{unique_number:02}"
        container_name = f"{container_name}_{unique_number:02}{suffix}"

        if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
            unreal.EditorAssetLibrary.make_directory(asset_dir)

            path = self.filepath_from_context(context)
            task = self.get_task(path, asset_dir, asset_name, False)

            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])  # noqa: E501

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
        unreal_pipeline.imprint(f"{asset_dir}/{container_name}", data)

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
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        container_path = f'{container["namespace"]}/{container["objectName"]}'
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
