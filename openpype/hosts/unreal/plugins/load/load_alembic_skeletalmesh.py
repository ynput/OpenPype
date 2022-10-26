# -*- coding: utf-8 -*-
"""Load Skeletal Mesh alembics."""
import os

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as up


class SkeletalMeshAlembicLoader(plugin.Loader):
    """Load Unreal SkeletalMesh from Alembic"""

    families = ["pointcache"]
    label = "Import Alembic Skeletal Mesh"
    representations = ["abc"]
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
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """

        # Create directory for asset and openpype container
        root = "/Game/OpenPype/Assets"
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)
        version = context.get('version').get('name')

        default_conversion = False
        if options.get("default_conversion"):
            default_conversion = options.get("default_conversion")

        asset_dir, container_name = up.send_request_literal(
            "create_unique_asset_name", params=[root, asset, name, version])

        container_name += suffix

        if not up.send_request_literal(
                "does_directory_exist", params=[asset_dir]):
            up.send_request("make_directory", params=[asset_dir])

            task_properties = [
                ("filename", up.format_string(self.fname)),
                ("destination_path", up.format_string(asset_dir)),
                ("destination_name", up.format_string(asset_name)),
                ("replace_existing", "False"),
                ("automated", "True"),
                ("save", "True")
            ]

            options_properties = [
                ("import_type", "unreal.AlembicImportType.SKELETAL")
            ]

            options_extra_properties = []

            if not default_conversion:
                options_extra_properties.extend([
                    ("conversion_settings", "preset", "unreal.AbcConversionPreset.CUSTOM"),
                    ("conversion_settings", "flip_u", "False"),
                    ("conversion_settings", "flip_v", "False"),
                    ("conversion_settings", "rotation", "[0.0, 0.0, 0.0]"),
                    ("conversion_settings", "scale", "[1.0, 1.0, 1.0]")
                ])

            up.send_request(
                "import_abc_task",
                params=[
                    str(task_properties),
                    str(options_properties),
                    str(options_extra_properties)
                ])

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

    # def update(self, container, representation):
    #     name = container["asset_name"]
    #     source_path = get_representation_path(representation)
    #     destination_path = container["namespace"]

    #     task = self.get_task(source_path, destination_path, name, True)

    #     # do import fbx and replace existing data
    #     unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    #     container_path = "{}/{}".format(container["namespace"],
    #                                     container["objectName"])
    #     # update metadata
    #     up.imprint(
    #         container_path,
    #         {
    #             "representation": str(representation["_id"]),
    #             "parent": str(representation["parent"])
    #         })

    #     asset_content = unreal.EditorAssetLibrary.list_assets(
    #         destination_path, recursive=True, include_folder=True
    #     )

    #     for a in asset_content:
    #         unreal.EditorAssetLibrary.save_asset(a)

    # def remove(self, container):
    #     path = container["namespace"]
    #     parent_path = os.path.dirname(path)

    #     unreal.EditorAssetLibrary.delete_directory(path)

    #     asset_content = unreal.EditorAssetLibrary.list_assets(
    #         parent_path, recursive=False
    #     )

    #     if len(asset_content) == 0:
    #         unreal.EditorAssetLibrary.delete_directory(parent_path)
