from pathlib import Path
import shutil

import unreal

from openpype.pipeline import publish


class ExtractUAsset(publish.Extractor):
    """Extract a UAsset."""

    label = "Extract UAsset"
    hosts = ["unreal"]
    families = ["uasset", "umap"]
    optional = True

    def process(self, instance):
        extension = (
            "umap" if "umap" in instance.data.get("families") else "uasset")
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        self.log.debug("Performing extraction..")
        staging_dir = self.staging_dir(instance)

        members = instance.data.get("members", [])

        if not members:
            raise RuntimeError("No members found in instance.")

        # UAsset publishing supports only one member
        obj = members[0]

        asset = ar.get_asset_by_object_path(obj).get_asset()
        sys_path = unreal.SystemLibrary.get_system_path(asset)
        filename = Path(sys_path).name

        shutil.copy(sys_path, staging_dir)

        self.log.info(f"instance.data: {instance.data}")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            "name": extension,
            "ext": extension,
            "files": filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)
