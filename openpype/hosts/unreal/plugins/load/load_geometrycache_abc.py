# -*- coding: utf-8 -*-
"""Loader for published alembics."""

from openpype.pipeline import (
    get_representation_path,
    AYON_CONTAINER_ID
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class PointCacheAlembicLoader(UnrealBaseLoader):
    """Load Point Cache from Alembic"""

    families = ["model", "pointcache"]
    label = "Import Alembic Point Cache"
    representations = ["abc"]
    icon = "cube"
    color = "orange"

    @staticmethod
    def _import_abc_task(
        filename, destination_path, destination_name, replace,
        frame_start, frame_end, default_conversion
    ):
        conversion = (
            None
            if default_conversion
            else {
                "flip_u": False,
                "flip_v": True,
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
            }
        )

        params = {
            "filename": filename,
            "destination_path": destination_path,
            "destination_name": destination_name,
            "replace_existing": replace,
            "automated": True,
            "save": True,
            "options_properties": [
                ["import_type", "unreal.AlembicImportType.GEOMETRY_CACHE"]
            ],
            "sub_options_properties": [
                ["geometry_cache_settings", "flatten_tracks", "False"],
                ["sampling_settings", "frame_start", str(frame_start)],
                ["sampling_settings", "frame_end", str(frame_end)]
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
        # Create directory for asset and OpenPype container
        root = f"{self.root}/Assets"
        asset = context.get('asset').get('name')
        asset_name = f"{asset}_{name}" if asset else f"{name}"
        version = context.get('version').get('name')

        default_conversion = options.get("default_conversion") or False

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

            frame_start = context.get('asset').get('data').get('frameStart')
            frame_end = context.get('asset').get('data').get('frameEnd')

            # If frame start and end are the same, we increase the end frame by
            # one, otherwise Unreal will not import it
            if frame_start == frame_end:
                frame_end += 1

            self._import_abc_task(
                self.fname, asset_dir, asset_name, False,
                frame_start, frame_end, default_conversion)

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
            "family": context["representation"]["context"]["family"],
            "frame_start": context["asset"]["data"]["frameStart"],
            "frame_end": context["asset"]["data"]["frameEnd"],
            "default_conversion": default_conversion
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

        frame_start = container["frameStart"]
        frame_end = container["frameStart"]
        default_conversion = container["default_conversion"]

        self._import_abc_task(
            filename, asset_dir, asset_name, True,
            frame_start, frame_end, default_conversion)

        super(UnrealBaseLoader, self).update(container, representation)
