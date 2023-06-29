# -*- coding: utf-8 -*-
"""Load UAsset."""
from pathlib import Path
import shutil

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class UAssetLoader(UnrealBaseLoader):
    """Load UAsset."""

    families = ["uasset"]
    label = "Load UAsset"
    representations = ["uasset"]
    icon = "cube"
    color = "orange"

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

        # Create directory for asset and OpenPype container
        root = f"{self.root}/Assets"
        asset = context.get('asset').get('name')
        asset_name = f"{asset}_{name}" if asset else f"{name}"

        asset_dir, container_name = send_request(
            "create_unique_asset_name", params={
                "root": root,
                "asset": asset,
                "name": name})

        send_request(
            "make_directory", params={"directory_path": asset_dir})

        project_content_dir = send_request("project_content_dir")
        destination_path = asset_dir.replace(
            "/Game", Path(project_content_dir).as_posix(), 1)

        shutil.copy(self.fname, f"{destination_path}/{asset_name}.uasset")

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

        project_content_dir = send_request("project_content_dir")
        destination_path = asset_dir.replace(
            "/Game", Path(project_content_dir).as_posix(), 1)

        shutil.copy(filename, f"{destination_path}/{asset_name}.uasset")

        super(UnrealBaseLoader, self).update(container, representation)
