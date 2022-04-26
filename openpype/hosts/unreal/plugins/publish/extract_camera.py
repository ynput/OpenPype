# -*- coding: utf-8 -*-
"""Extract camera from Unreal."""
import os

import unreal
from unreal import EditorAssetLibrary as eal
from unreal import EditorLevelLibrary as ell

import openpype.api


class ExtractCamera(openpype.api.Extractor):
    """Extract a camera."""

    label = "Extract Camera"
    hosts = ["unreal"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        staging_dir = self.staging_dir(instance)
        fbx_filename = "{}.fbx".format(instance.name)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Check if the loaded level is the same of the instance
        current_level = ell.get_editor_world().get_path_name()
        assert current_level == instance.data.get("level"), \
            "Wrong level loaded"

        for member in instance[:]:
            data = eal.find_asset_data(member)
            if data.asset_class == "LevelSequence":
                ar = unreal.AssetRegistryHelpers.get_asset_registry()
                sequence = ar.get_asset_by_object_path(member).get_asset()
                unreal.SequencerTools.export_fbx(
                    ell.get_editor_world(),
                    sequence,
                    sequence.get_bindings(),
                    unreal.FbxExportOption(),
                    os.path.join(staging_dir, fbx_filename)
                )
                break

        if "representations" not in instance.data:
            instance.data["representations"] = []

        fbx_representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': fbx_filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(fbx_representation)
