# -*- coding: utf-8 -*-
from pathlib import Path

import unreal

from openpype.hosts.unreal.api.pipeline import (
    UNREAL_VERSION,
    create_folder,
    get_subsequences,
)
from openpype.hosts.unreal.api.plugin import (
    UnrealAssetCreator
)
from openpype.lib import (
    UILabelDef,
    UISeparatorDef,
    BoolDef,
    NumberDef
)


class CreateRender(UnrealAssetCreator):
    """Create instance for sequence for rendering"""

    identifier = "io.ayon.creators.unreal.render"
    label = "Render"
    family = "render"
    icon = "eye"

    def create_instance(
            self, instance_data, subset_name, pre_create_data,
            selected_asset_path, master_seq, master_lvl, seq_data
    ):
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

    def create_with_new_sequence(
            self, subset_name, instance_data, pre_create_data
    ):
        # If the option to create a new level sequence is selected,
        # create a new level sequence and a master level.

        root = f"/Game/Ayon/Sequences"

        # Create a new folder for the sequence in root
        sequence_dir_name = create_folder(root, subset_name)
        sequence_dir = f"{root}/{sequence_dir_name}"

        unreal.log_warning(f"sequence_dir: {sequence_dir}")

        # Create the level sequence
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        seq = asset_tools.create_asset(
            asset_name=subset_name,
            package_path=sequence_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew())

        seq.set_playback_start(pre_create_data.get("start_frame"))
        seq.set_playback_end(pre_create_data.get("end_frame"))

        pre_create_data["members"] = [seq.get_path_name()]

        unreal.EditorAssetLibrary.save_asset(seq.get_path_name())

        # Create the master level
        if UNREAL_VERSION.major >= 5:
            curr_level = unreal.LevelEditorSubsystem().get_current_level()
        else:
            world = unreal.EditorLevelLibrary.get_editor_world()
            levels = unreal.EditorLevelUtils.get_levels(world)
            curr_level = levels[0] if len(levels) else None
            if not curr_level:
                raise RuntimeError("No level loaded.")
        curr_level_path = curr_level.get_outer().get_path_name()

        # If the level path does not start with "/Game/", the current
        # level is a temporary, unsaved level.
        if curr_level_path.startswith("/Game/"):
            if UNREAL_VERSION.major >= 5:
                unreal.LevelEditorSubsystem().save_current_level()
            else:
                unreal.EditorLevelLibrary.save_current_level()

        ml_path = f"{sequence_dir}/{subset_name}_MasterLevel"

        if UNREAL_VERSION.major >= 5:
            unreal.LevelEditorSubsystem().new_level(ml_path)
        else:
            unreal.EditorLevelLibrary.new_level(ml_path)

        seq_data = {
            "sequence": seq,
            "output": f"{seq.get_name()}",
            "frame_range": (
                seq.get_playback_start(),
                seq.get_playback_end())}

        self.create_instance(
            instance_data, subset_name, pre_create_data,
            seq.get_path_name(), seq.get_path_name(), ml_path, seq_data)

    def create_from_existing_sequence(
            self, subset_name, instance_data, pre_create_data
    ):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
        selection = [
            a.get_path_name() for a in sel_objects
            if a.get_class().get_name() == "LevelSequence"]

        if len(selection) == 0:
            raise RuntimeError("Please select at least one Level Sequence.")

        seq_data = None

        for sel in selection:
            selected_asset = ar.get_asset_by_object_path(sel).get_asset()
            selected_asset_path = selected_asset.get_path_name()

            # Check if the selected asset is a level sequence asset.
            if selected_asset.get_class().get_name() != "LevelSequence":
                unreal.log_warning(
                    f"Skipping {selected_asset.get_name()}. It isn't a Level "
                    "Sequence.")

            if pre_create_data.get("use_hierarchy"):
                # The asset name is the the third element of the path which
                # contains the map.
                # To take the asset name, we remove from the path the prefix
                # "/Game/OpenPype/" and then we split the path by "/".
                sel_path = selected_asset_path
                asset_name = sel_path.replace(
                    "/Game/Ayon/", "").split("/")[0]

                search_path = f"/Game/Ayon/{asset_name}"
            else:
                search_path = Path(selected_asset_path).parent.as_posix()

            # Get the master sequence and the master level.
            # There should be only one sequence and one level in the directory.
            try:
                ar_filter = unreal.ARFilter(
                    class_names=["LevelSequence"],
                    package_paths=[search_path],
                    recursive_paths=False)
                sequences = ar.get_assets(ar_filter)
                master_seq = sequences[0].get_asset().get_path_name()
                master_seq_obj = sequences[0].get_asset()
                ar_filter = unreal.ARFilter(
                    class_names=["World"],
                    package_paths=[search_path],
                    recursive_paths=False)
                levels = ar.get_assets(ar_filter)
                master_lvl = levels[0].get_asset().get_path_name()
            except IndexError:
                raise RuntimeError(
                    f"Could not find the hierarchy for the selected sequence.")

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

            if (selected_asset_path == master_seq or
                    pre_create_data.get("use_hierarchy")):
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

            self.create_instance(
                instance_data, subset_name, pre_create_data,
                selected_asset_path, master_seq, master_lvl, seq_data)

    def create(self, subset_name, instance_data, pre_create_data):
        if pre_create_data.get("create_seq"):
            self.create_with_new_sequence(
                subset_name, instance_data, pre_create_data)
        else:
            self.create_from_existing_sequence(
                subset_name, instance_data, pre_create_data)

    def get_pre_create_attr_defs(self):
        return [
            UILabelDef(
                "Select a Level Sequence to render or create a new one."
            ),
            BoolDef(
                "create_seq",
                label="Create a new Level Sequence",
                default=False
            ),
            UILabelDef(
                "WARNING: If you create a new Level Sequence, the current\n"
                "level will be saved and a new Master Level will be created."
            ),
            NumberDef(
                "start_frame",
                label="Start Frame",
                default=0,
                minimum=-999999,
                maximum=999999
            ),
            NumberDef(
                "end_frame",
                label="Start Frame",
                default=150,
                minimum=-999999,
                maximum=999999
            ),
            UISeparatorDef(),
            UILabelDef(
                "The following settings are valid only if you are not\n"
                "creating a new sequence."
            ),
            BoolDef(
                "use_hierarchy",
                label="Use Hierarchy",
                default=False
            ),
        ]
