# -*- coding: utf-8 -*-
"""Load UAsset."""
from pathlib import Path
import shutil

from openpype.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
    AYON_ASSET_DIR,
)


class UAssetLoader(UnrealBaseLoader):
    """Load UAsset."""

    families = ["uasset"]
    label = "Load UAsset"
    representations = ["uasset"]
    icon = "cube"
    color = "orange"

    extension = "uasset"

    def load(self, context, name=None, namespace=None, options=None):
        """Load and containerise representation into Content Browser.

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

        # Create directory for asset and Ayon container
        root = AYON_ASSET_DIR
        asset = context.get('asset').get('name')
        suffix = "_CON"
        asset_name = f"{asset}_{name}" if asset else f"{name}"

        asset_dir, container_name = send_request(
            "create_unique_asset_name", params={
                "root": root,
                "asset": asset,
                "name": name})

        unique_number = 1
        while send_request(
                "does_directory_exist",
                params={"directory_path": f"{asset_dir}_{unique_number:02}"}):
            unique_number += 1

        asset_dir = f"{asset_dir}_{unique_number:02}"
        container_name = f"{container_name}_{unique_number:02}{suffix}"

        send_request(
            "make_directory", params={"directory_path": asset_dir})

        project_content_dir = send_request("project_content_dir")
        destination_path = asset_dir.replace(
            "/Game", Path(project_content_dir).as_posix(), 1)

        path = self.filepath_from_context(context)
        shutil.copy(
            path,
            f"{destination_path}/{name}_{unique_number:02}.{self.extension}")

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": self.__class__.__name__,
            "representation_id": str(context["representation"]["_id"]),
            "version_id": str(context["representation"]["parent"]),
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
        name = representation["context"]["subset"]

        unique_number = container["container_name"].split("_")[-2]

        project_content_dir = send_request("project_content_dir")
        destination_path = asset_dir.replace(
            "/Game", Path(project_content_dir).as_posix(), 1)

        send_request(
            "delete_assets_in_dir_but_container",
            params={"asset_dir": asset_dir})

        update_filepath = get_representation_path(representation)

        shutil.copy(
            update_filepath,
            f"{destination_path}/{name}_{unique_number}.{self.extension}")

        super(UAssetLoader, self).update(container, representation)


class UMapLoader(UAssetLoader):
    """Load Level."""

    families = ["uasset"]
    label = "Load Level"
    representations = ["umap"]

    extension = "umap"
