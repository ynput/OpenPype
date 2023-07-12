# -*- coding: utf-8 -*-
"""Load Alembic Animation."""

from openpype.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class AnimationAlembicLoader(UnrealBaseLoader):
    """Load Unreal SkeletalMesh from Alembic"""

    families = ["animation"]
    label = "Import Alembic Animation"
    representations = ["abc"]
    icon = "cube"
    color = "orange"

    @staticmethod
    def _import_abc_task(
        filename, destination_path, destination_name, replace
    ):
        conversion = {
            "flip_u": False,
            "flip_v": False,
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, -1.0],
        }

        params = {
            "filename": filename,
            "destination_path": destination_path,
            "destination_name": destination_name,
            "replace_existing": replace,
            "automated": True,
            "save": True,
            "options_properties": [
                ['import_type', 'unreal.AlembicImportType.SKELETAL']
            ],
            "conversion_settings": conversion
        }

        send_request("import_abc_task", params=params)

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

        # Create directory for asset and openpype container
        root = f"{self.root}/Assets"
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

            self._import_abc_task(
                self.fname, asset_dir, asset_name, False)

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
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

        self._import_abc_task(filename, asset_dir, asset_name, True)

        super(UnrealBaseLoader, self).update(container, representation)
