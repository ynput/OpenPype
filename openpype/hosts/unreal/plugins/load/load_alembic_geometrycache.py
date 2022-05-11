# -*- coding: utf-8 -*-
"""Loader for published alembics."""
import os

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline

import unreal  # noqa


class PointCacheAlembicLoader(plugin.Loader):
    """Load Point Cache from Alembic"""

    families = ["model", "pointcache"]
    label = "Import Alembic Point Cache"
    representations = ["abc"]
    icon = "cube"
    color = "orange"

    def get_task(
        self, filename, asset_dir, asset_name, replace, frame_start, frame_end
    ):
        task = unreal.AssetImportTask()
        options = unreal.AbcImportSettings()
        gc_settings = unreal.AbcGeometryCacheSettings()
        conversion_settings = unreal.AbcConversionSettings()
        sampling_settings = unreal.AbcSamplingSettings()

        task.set_editor_property('filename', filename)
        task.set_editor_property('destination_path', asset_dir)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('replace_existing', replace)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)

        # set import options here
        # Unreal 4.24 ignores the settings. It works with Unreal 4.26
        options.set_editor_property(
            'import_type', unreal.AlembicImportType.GEOMETRY_CACHE)

        gc_settings.set_editor_property('flatten_tracks', False)

        conversion_settings.set_editor_property('flip_u', False)
        conversion_settings.set_editor_property('flip_v', True)
        conversion_settings.set_editor_property(
            'scale', unreal.Vector(x=100.0, y=100.0, z=100.0))
        conversion_settings.set_editor_property(
            'rotation', unreal.Vector(x=-90.0, y=0.0, z=180.0))

        sampling_settings.set_editor_property('frame_start', frame_start)
        sampling_settings.set_editor_property('frame_end', frame_end)

        options.geometry_cache_settings = gc_settings
        options.conversion_settings = conversion_settings
        options.sampling_settings = sampling_settings
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
        # Create directory for asset and OpenPype container
        root = "/Game/OpenPype/Assets"
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            "{}/{}/{}".format(root, asset, name), suffix="")

        container_name += suffix

        unreal.EditorAssetLibrary.make_directory(asset_dir)

        frame_start = context.get('asset').get('data').get('frameStart')
        frame_end = context.get('asset').get('data').get('frameEnd')

        # If frame start and end are the same, we increase the end frame by
        # one, otherwise Unreal will not import it
        if frame_start == frame_end:
            frame_end += 1

        task = self.get_task(
            self.fname, asset_dir, asset_name, False, frame_start, frame_end)

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

        task = self.get_task(source_path, destination_path, name, True)

        # do import fbx and replace existing data
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

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
