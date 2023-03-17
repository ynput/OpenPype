# -*- coding: utf-8 -*-
import unreal

from openpype.pipeline import CreatorError
from openpype.hosts.unreal.api.pipeline import (
    get_subsequences
)
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator
)
from openpype.lib import UILabelDef


class CreateRender(UnrealAssetCreator):
    """Create instance for sequence for rendering"""

    identifier = "io.openpype.creators.unreal.render"
    label = "Render"
    family = "render"
    icon = "eye"

    def create(self, subset_name, instance_data, pre_create_data):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
        selection = [
            a.get_path_name() for a in sel_objects
            if a.get_class().get_name() == "LevelSequence"]

        if not selection:
            raise CreatorError("Please select at least one Level Sequence.")

        seq_data = None

        for sel in selection:
            selected_asset = ar.get_asset_by_object_path(sel).get_asset()
            selected_asset_path = selected_asset.get_path_name()

            # Check if the selected asset is a level sequence asset.
            if selected_asset.get_class().get_name() != "LevelSequence":
                unreal.log_warning(
                    f"Skipping {selected_asset.get_name()}. It isn't a Level "
                    "Sequence.")

            # The asset name is the third element of the path which
            # contains the map.
            # To take the asset name, we remove from the path the prefix
            # "/Game/OpenPype/" and then we split the path by "/".
            sel_path = selected_asset_path
            asset_name = sel_path.replace("/Game/OpenPype/", "").split("/")[0]

            # Get the master sequence and the master level.
            # There should be only one sequence and one level in the directory.
            ar_filter = unreal.ARFilter(
                class_names=["LevelSequence"],
                package_paths=[f"/Game/OpenPype/{asset_name}"],
                recursive_paths=False)
            sequences = ar.get_assets(ar_filter)
            master_seq = sequences[0].get_asset().get_path_name()
            master_seq_obj = sequences[0].get_asset()
            ar_filter = unreal.ARFilter(
                class_names=["World"],
                package_paths=[f"/Game/OpenPype/{asset_name}"],
                recursive_paths=False)
            levels = ar.get_assets(ar_filter)
            master_lvl = levels[0].get_asset().get_path_name()

            # If the selected asset is the master sequence, we get its data
            # and then we create the instance for the master sequence.
            # Otherwise, we cycle from the master sequence to find the selected
            # sequence and we get its data. This data will be used to create
            # the instance for the selected sequence. In particular,
            # we get the frame range of the selected sequence and its final
            # output path.
            master_seq_data = {
                "sequence": master_seq_obj,
                "output": f"{master_seq_obj.get_name()}",
                "frame_range": (
                    master_seq_obj.get_playback_start(),
                    master_seq_obj.get_playback_end())}

            if selected_asset_path == master_seq:
                seq_data = master_seq_data
            else:
                seq_data_list = [master_seq_data]

                for seq in seq_data_list:
                    subscenes = get_subsequences(seq.get('sequence'))

                    for sub_seq in subscenes:
                        sub_seq_obj = sub_seq.get_sequence()
                        curr_data = {
                            "sequence": sub_seq_obj,
                            "output": (f"{seq.get('output')}/"
                                       f"{sub_seq_obj.get_name()}"),
                            "frame_range": (
                                sub_seq.get_start_frame(),
                                sub_seq.get_end_frame() - 1)}

                        # If the selected asset is the current sub-sequence,
                        # we get its data and we break the loop.
                        # Otherwise, we add the current sub-sequence data to
                        # the list of sequences to check.
                        if sub_seq_obj.get_path_name() == selected_asset_path:
                            seq_data = curr_data
                            break

                        seq_data_list.append(curr_data)

                    # If we found the selected asset, we break the loop.
                    if seq_data is not None:
                        break

            # If we didn't find the selected asset, we don't create the
            # instance.
            if not seq_data:
                unreal.log_warning(
                    f"Skipping {selected_asset.get_name()}. It isn't a "
                    "sub-sequence of the master sequence.")
                continue

            instance_data["members"] = [selected_asset_path]
            instance_data["sequence"] = selected_asset_path
            instance_data["master_sequence"] = master_seq
            instance_data["master_level"] = master_lvl
            instance_data["output"] = seq_data.get('output')
            instance_data["frameStart"] = seq_data.get('frame_range')[0]
            instance_data["frameEnd"] = seq_data.get('frame_range')[1]

            super(CreateRender, self).create(
                subset_name,
                instance_data,
                pre_create_data)

    def get_pre_create_attr_defs(self):
        return [
            UILabelDef("Select the sequence to render.")
        ]
