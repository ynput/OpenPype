import logging

from husd.outputprocessor import OutputProcessor

from openpype.lib import usdlib


class AyonURIOutputProcessor(OutputProcessor):
    """Process Ayon URIs into their full path equivalents."""

    def __init__(self):
        """ There is only one object of each output processor class that is
            ever created in a Houdini session. Therefore be very careful
            about what data gets put in this object.
        """
        self._save_cache = dict()
        self._ref_cache = dict()
        self._publish_context = None
        self.log = logging.getLogger(__name__)

    @staticmethod
    def name():
        return "ayon_uri_processor"

    @staticmethod
    def displayName():
        return "Ayon URI Output Processor"

    def processReferencePath(self,
                             asset_path,
                             referencing_layer_path,
                             asset_is_layer):
        """
        Args:
            asset_path (str): The path to the asset, as specified in Houdini.
               If this asset is being written to disk, this will be the final
               output of the `processSavePath()` calls on all output
               processors.
            referencing_layer_path (str): The absolute file path of the file
               containing the reference to the asset. You can use this to make
               the path pointer relative.
            asset_is_layer (bool): A boolean value indicating whether this
                asset is a USD layer file. If this is `False`, the asset is
                something else (for example, a texture or volume file).

        Returns:
            The refactored reference path.

        """

        cache = self._ref_cache

        # Retrieve from cache if this query occurred before (optimization)
        if asset_path in cache:
            return cache[asset_path]

        uri_data = usdlib.parse_ayon_uri(asset_path)
        if not uri_data:
            cache[asset_path] = asset_path
            return asset_path

        # Try and find it as an existing publish
        query = {
            "project_name": uri_data["project"],
            "asset_name": uri_data["asset"],
            "subset_name": uri_data["product"],
            "version_name": uri_data["version"],
            "representation_name": uri_data["representation"],
        }
        path = usdlib.get_representation_path_by_names(
            **query
        )
        if path:
            self.log.debug(
                "Ayon URI Resolver - ref: %s -> %s", asset_path, path
            )
            cache[asset_path] = path
            return path

        elif self._publish_context:
            # Query doesn't resolve to an existing version - likely
            # points to a version defined in the current publish session
            # as such we should resolve it using the current publish
            # context if that was set prior to this publish
            raise NotImplementedError("TODO")

        self.log.warning(f"Unable to resolve AYON URI: {asset_path}")
        cache[asset_path] = asset_path
        return asset_path

    def processSavePath(self,
                        asset_path,
                        referencing_layer_path,
                        asset_is_layer):
        """
        Args:
            asset_path (str): The path to the asset, as specified in Houdini.
               If this asset is being written to disk, this will be the final
               output of the `processSavePath()` calls on all output
               processors.
            referencing_layer_path (str): The absolute file path of the file
               containing the reference to the asset. You can use this to make
               the path pointer relative.
            asset_is_layer (bool): A boolean value indicating whether this
                asset is a USD layer file. If this is `False`, the asset is
                something else (for example, a texture or volume file).

        Returns:
            The refactored save path.

        """
        cache = self._save_cache

        # Retrieve from cache if this query occurred before (optimization)
        if asset_path in cache:
            return cache[asset_path]

        uri_data = usdlib.parse_ayon_uri(asset_path)
        if not uri_data:
            cache[asset_path] = asset_path
            return asset_path

        relative_template = "{asset}_{product}_{version}_{representation}.usd"
        # Set save output path to a relative path so other
        # processors can potentially manage it easily?
        path = relative_template.format(**uri_data)

        self.log.debug("Ayon URI Resolver - save: %s -> %s", asset_path, path)
        cache[asset_path] = path
        return path


def usdOutputProcessor():
    return AyonURIOutputProcessor
