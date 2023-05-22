from pathlib import Path
import shutil

import unreal

from openpype.pipeline import publish


class ExtractUMap(publish.Extractor):
    """Extract a UMap."""

    label = "Extract Level"
    hosts = ["unreal"]
    families = ["uasset"]
    optional = True

    def process(self, instance):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        self.log.info("Performing extraction..")

        staging_dir = self.staging_dir(instance)
        filename = f"{instance.name}.umap"

        members = instance.data.get("members", [])

        if not members:
            raise RuntimeError("No members found in instance.")

        # UAsset publishing supports only one member
        obj = members[0]

        asset = ar.get_asset_by_object_path(obj).get_asset()
        sys_path = unreal.SystemLibrary.get_system_path(asset)
        filename = Path(sys_path).name

        shutil.copy(sys_path, staging_dir)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'umap',
            'ext': 'umap',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)
