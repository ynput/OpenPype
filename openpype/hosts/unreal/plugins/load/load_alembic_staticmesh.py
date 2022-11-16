# -*- coding: utf-8 -*-
"""Loader for Static Mesh alembics."""
import os

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as up


class StaticMeshAlembicLoader(plugin.Loader):
    """Load Unreal StaticMesh from Alembic"""

    families = ["model"]
    label = "Import Alembic Static Mesh"
    representations = ["abc"]
    icon = "cube"
    color = "orange"

    def _import_fbx_task(
        self, filename, destination_path, destination_name, replace,
        default_conversion
    ):
        task_properties = [
            ("filename", up.format_string(filename)),
            ("destination_path", up.format_string(destination_path)),
            ("destination_name", up.format_string(destination_name)),
            ("replace_existing", str(replace)),
            ("automated", "True"),
            ("save", "True")
        ]

        options_properties = [
            ("import_type", "unreal.AlembicImportType.STATIC_MESH")
        ]

        options_extra_properties = [
            ("static_mesh_settings", "merge_meshes", "True")
        ]

        if not default_conversion:
            options_extra_properties.extend([
                ("conversion_settings", "preset",
                    "unreal.AbcConversionPreset.CUSTOM"),
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
        # Create directory for asset and OpenPype container
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

            self._import_fbx_task(
                self.fname, asset_dir, asset_name, False, default_conversion)

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
            "family": context["representation"]["context"]["family"],
            "default_conversion": default_conversion
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
        default_conversion = container["default_conversion"]

        self._import_fbx_task(
            filename, asset_dir, asset_name, True, default_conversion)

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
