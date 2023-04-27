# -*- coding: utf-8 -*-
"""Extract camera from Unreal."""
import os

import unreal

from openpype.pipeline import publish
from openpype.hosts.unreal.api.pipeline import UNREAL_VERSION


class ExtractCamera(publish.Extractor):
    """Extract a camera."""

    label = "Extract Camera"
    hosts = ["unreal"]
    families = ["camera"]
    optional = True

    def process(self, instance):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        # Define extract output file path
        staging_dir = self.staging_dir(instance)
        fbx_filename = "{}.fbx".format(instance.name)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Check if the loaded level is the same of the instance
        if UNREAL_VERSION.major == 5:
            world = unreal.UnrealEditorSubsystem().get_editor_world()
        else:
            world = unreal.EditorLevelLibrary.get_editor_world()
        current_level = world.get_path_name()
        assert current_level == instance.data.get("level"), \
            "Wrong level loaded"

        for member in instance.data.get('members'):
            data = ar.get_asset_by_object_path(member)
            if UNREAL_VERSION.major == 5:
                is_level_sequence = (
                    data.asset_class_path.asset_name == "LevelSequence")
            else:
                is_level_sequence = (data.asset_class == "LevelSequence")

            if is_level_sequence:
                sequence = data.get_asset()
                if UNREAL_VERSION.major == 5 and UNREAL_VERSION.minor >= 1:
                    params = unreal.SequencerExportFBXParams(
                        world=world,
                        root_sequence=sequence,
                        sequence=sequence,
                        bindings=sequence.get_bindings(),
                        master_tracks=sequence.get_master_tracks(),
                        fbx_file_name=os.path.join(staging_dir, fbx_filename)
                    )
                    unreal.SequencerTools.export_level_sequence_fbx(params)
                elif UNREAL_VERSION.major == 4 and UNREAL_VERSION.minor == 26:
                    unreal.SequencerTools.export_fbx(
                        world,
                        sequence,
                        sequence.get_bindings(),
                        unreal.FbxExportOption(),
                        os.path.join(staging_dir, fbx_filename)
                    )
                else:
                    # Unreal 5.0 or 4.27
                    unreal.SequencerTools.export_level_sequence_fbx(
                        world,
                        sequence,
                        sequence.get_bindings(),
                        unreal.FbxExportOption(),
                        os.path.join(staging_dir, fbx_filename)
                    )

                if not os.path.isfile(os.path.join(staging_dir, fbx_filename)):
                    raise RuntimeError("Failed to extract camera")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        fbx_representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': fbx_filename,
            "stagingDir": staging_dir,
        }
        instance.data["representations"].append(fbx_representation)
