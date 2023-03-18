from pathlib import Path
import shutil

import unreal

from openpype.pipeline import publish


class ExtractUAsset(publish.Extractor):
    """Extract a UAsset."""

    label = "Extract UAsset"
    hosts = ["unreal"]
    families = ["uasset"]
    optional = True

    def process(self, instance):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        self.log.info("Performing extraction..")

        staging_dir = self.staging_dir(instance)
        filename = "{}.uasset".format(instance.name)

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
            'name': 'uasset',
            'ext': 'uasset',
            'files': filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(representation)
