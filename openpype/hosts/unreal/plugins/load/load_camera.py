# -*- coding: utf-8 -*-
"""Load camera from FBX."""
from pathlib import Path

import unreal
from unreal import (
    EditorAssetLibrary,
    EditorLevelLibrary,
    EditorLevelUtils,
    LevelSequenceEditorBlueprintLibrary as LevelSequenceLib,
)
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AYON_CONTAINER_ID,
    get_current_project_name,
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api.pipeline import (
    generate_sequence,
    set_sequence_hierarchy,
    create_container,
    imprint,
)


class CameraLoader(plugin.Loader):
    """Load Unreal StaticMesh from FBX"""

    families = ["camera"]
    label = "Load Camera"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def _import_camera(
        self, world, sequence, bindings, import_fbx_settings, import_filename
    ):
        ue_version = unreal.SystemLibrary.get_engine_version().split('.')
        ue_major = int(ue_version[0])
        ue_minor = int(ue_version[1])

        if ue_major == 4 and ue_minor <= 26:
            unreal.SequencerTools.import_fbx(
                world,
                sequence,
                bindings,
                import_fbx_settings,
                import_filename
            )
        elif (ue_major == 4 and ue_minor >= 27) or ue_major == 5:
            unreal.SequencerTools.import_level_sequence_fbx(
                world,
                sequence,
                bindings,
                import_fbx_settings,
                import_filename
            )
        else:
            raise NotImplementedError(
                f"Unreal version {ue_major} not supported")

    def load(self, context, name, namespace, data):
        """
        Load and containerise representation into Content Browser.

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
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """

        # Create directory for asset and Ayon container
        hierarchy = context.get('asset').get('data').get('parents')
        root = "/Game/Ayon"
        hierarchy_dir = root
        hierarchy_dir_list = []
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
            hierarchy_dir_list.append(hierarchy_dir)
        asset = context.get('asset').get('name')
        suffix = "_CON"
        asset_name = f"{asset}_{name}" if asset else f"{name}"

        tools = unreal.AssetToolsHelpers().get_asset_tools()

        # Create a unique name for the camera directory
        unique_number = 1
        if EditorAssetLibrary.does_directory_exist(f"{hierarchy_dir}/{asset}"):
            asset_content = EditorAssetLibrary.list_assets(
                f"{root}/{asset}", recursive=False, include_folder=True
            )

            # Get highest number to make a unique name
            folders = [a for a in asset_content
                       if a[-1] == "/" and f"{name}_" in a]
            # Get number from folder name. Splits the string by "_" and
            # removes the last element (which is a "/").
            f_numbers = [int(f.split("_")[-1][:-1]) for f in folders]
            f_numbers.sort()
            unique_number = f_numbers[-1] + 1 if f_numbers else 1

        asset_dir, container_name = tools.create_unique_asset_name(
            f"{hierarchy_dir}/{asset}/{name}_{unique_number:02d}", suffix="")

        container_name += suffix

        EditorAssetLibrary.make_directory(asset_dir)

        # Create map for the shot, and create hierarchy of map. If the maps
        # already exist, we will use them.
        h_dir = hierarchy_dir_list[0]
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"
        if not EditorAssetLibrary.does_asset_exist(master_level):
            EditorLevelLibrary.new_level(f"{h_dir}/{h_asset}_map")

        level = f"{asset_dir}/{asset}_map_camera.{asset}_map_camera"
        if not EditorAssetLibrary.does_asset_exist(level):
            EditorLevelLibrary.new_level(f"{asset_dir}/{asset}_map_camera")

            EditorLevelLibrary.load_level(master_level)
            EditorLevelUtils.add_level_to_world(
                EditorLevelLibrary.get_editor_world(),
                level,
                unreal.LevelStreamingDynamic
            )
        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(level)

        # Get all the sequences in the hierarchy. It will create them, if
        # they don't exist.
        frame_ranges = []
        sequences = []
        for (h_dir, h) in zip(hierarchy_dir_list, hierarchy):
            root_content = EditorAssetLibrary.list_assets(
                h_dir, recursive=False, include_folder=False)

            existing_sequences = [
                EditorAssetLibrary.find_asset_data(asset)
                for asset in root_content
                if EditorAssetLibrary.find_asset_data(
                    asset).get_class().get_name() == 'LevelSequence'
            ]

            if existing_sequences:
                for seq in existing_sequences:
                    sequences.append(seq.get_asset())
                    frame_ranges.append((
                        seq.get_asset().get_playback_start(),
                        seq.get_asset().get_playback_end()))
            else:
                sequence, frame_range = generate_sequence(h, h_dir)

                sequences.append(sequence)
                frame_ranges.append(frame_range)

        EditorAssetLibrary.make_directory(asset_dir)

        cam_seq = tools.create_asset(
            asset_name=f"{asset}_camera",
            package_path=asset_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        # Add sequences data to hierarchy
        for i in range(len(sequences) - 1):
            set_sequence_hierarchy(
                sequences[i], sequences[i + 1],
                frame_ranges[i][1],
                frame_ranges[i + 1][0], frame_ranges[i + 1][1],
                [level])

        project_name = get_current_project_name()
        data = get_asset_by_name(project_name, asset)["data"]
        cam_seq.set_display_rate(
            unreal.FrameRate(data.get("fps"), 1.0))
        cam_seq.set_playback_start(data.get('clipIn'))
        cam_seq.set_playback_end(data.get('clipOut') + 1)
        set_sequence_hierarchy(
            sequences[-1], cam_seq,
            frame_ranges[-1][1],
            data.get('clipIn'), data.get('clipOut'),
            [level])

        settings = unreal.MovieSceneUserImportFBXSettings()
        settings.set_editor_property('reduce_keys', False)

        if cam_seq:
            path = self.filepath_from_context(context)
            self._import_camera(
                EditorLevelLibrary.get_editor_world(),
                cam_seq,
                cam_seq.get_bindings(),
                settings,
                path
            )

        # Set range of all sections
        # Changing the range of the section is not enough. We need to change
        # the frame of all the keys in the section.
        for possessable in cam_seq.get_possessables():
            for tracks in possessable.get_tracks():
                for section in tracks.get_sections():
                    section.set_range(
                        data.get('clipIn'),
                        data.get('clipOut') + 1)
                    for channel in section.get_all_channels():
                        for key in channel.get_keys():
                            old_time = key.get_time().get_editor_property(
                                'frame_number')
                            old_time_value = old_time.get_editor_property(
                                'value')
                            new_time = old_time_value + (
                                data.get('clipIn') - data.get('frameStart')
                            )
                            key.set_time(unreal.FrameNumber(value=new_time))

        # Create Asset Container
        create_container(
            container=container_name, path=asset_dir)

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        imprint(f"{asset_dir}/{container_name}", data)

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(master_level)

        # Save all assets in the hierarchy
        asset_content = EditorAssetLibrary.list_assets(
            hierarchy_dir_list[0], recursive=True, include_folder=False
        )

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        curr_level_sequence = LevelSequenceLib.get_current_level_sequence()
        curr_time = LevelSequenceLib.get_current_time()
        is_cam_lock = LevelSequenceLib.is_camera_cut_locked_to_viewport()

        editor_subsystem = unreal.UnrealEditorSubsystem()
        vp_loc, vp_rot = editor_subsystem.get_level_viewport_camera_info()

        asset_dir = container.get('namespace')

        EditorLevelLibrary.save_current_level()

        _filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[asset_dir],
            recursive_paths=False)
        sequences = ar.get_assets(_filter)
        _filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[asset_dir],
            recursive_paths=True)
        maps = ar.get_assets(_filter)

        # There should be only one map in the list
        EditorLevelLibrary.load_level(maps[0].get_asset().get_path_name())

        level_sequence = sequences[0].get_asset()

        display_rate = level_sequence.get_display_rate()
        playback_start = level_sequence.get_playback_start()
        playback_end = level_sequence.get_playback_end()

        sequence_name = f"{container.get('asset')}_camera"

        # Get the actors in the level sequence.
        objs = unreal.SequencerTools.get_bound_objects(
            unreal.EditorLevelLibrary.get_editor_world(),
            level_sequence,
            level_sequence.get_bindings(),
            unreal.SequencerScriptingRange(
                has_start_value=True,
                has_end_value=True,
                inclusive_start=level_sequence.get_playback_start(),
                exclusive_end=level_sequence.get_playback_end()
            )
        )

        # Delete actors from the map
        for o in objs:
            if o.bound_objects[0].get_class().get_name() == "CineCameraActor":
                actor_path = o.bound_objects[0].get_path_name().split(":")[-1]
                actor = EditorLevelLibrary.get_actor_reference(actor_path)
                EditorLevelLibrary.destroy_actor(actor)

        # Remove the Level Sequence from the parent.
        # We need to traverse the hierarchy from the master sequence to find
        # the level sequence.
        root = "/Game/Ayon"
        namespace = container.get('namespace').replace(f"{root}/", "")
        ms_asset = namespace.split('/')[0]
        _filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        sequences = ar.get_assets(_filter)
        master_sequence = sequences[0].get_asset()
        _filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        levels = ar.get_assets(_filter)
        master_level = levels[0].get_asset().get_path_name()

        sequences = [master_sequence]

        parent = None
        sub_scene = None
        for s in sequences:
            tracks = s.get_master_tracks()
            subscene_track = None
            for t in tracks:
                if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                    subscene_track = t
            if subscene_track:
                sections = subscene_track.get_sections()
                for ss in sections:
                    if ss.get_sequence().get_name() == sequence_name:
                        parent = s
                        sub_scene = ss
                        break
                    sequences.append(ss.get_sequence())
                for i, ss in enumerate(sections):
                    ss.set_row_index(i)
            if parent:
                break

            assert parent, "Could not find the parent sequence"

        EditorAssetLibrary.delete_asset(level_sequence.get_path_name())

        settings = unreal.MovieSceneUserImportFBXSettings()
        settings.set_editor_property('reduce_keys', False)

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        new_sequence = tools.create_asset(
            asset_name=sequence_name,
            package_path=asset_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        new_sequence.set_display_rate(display_rate)
        new_sequence.set_playback_start(playback_start)
        new_sequence.set_playback_end(playback_end)

        sub_scene.set_sequence(new_sequence)

        self._import_camera(
            EditorLevelLibrary.get_editor_world(),
            new_sequence,
            new_sequence.get_bindings(),
            settings,
            str(representation["data"]["path"])
        )

        # Set range of all sections
        # Changing the range of the section is not enough. We need to change
        # the frame of all the keys in the section.
        project_name = get_current_project_name()
        asset = container.get('asset')
        data = get_asset_by_name(project_name, asset)["data"]

        for possessable in new_sequence.get_possessables():
            for tracks in possessable.get_tracks():
                for section in tracks.get_sections():
                    section.set_range(
                        data.get('clipIn'),
                        data.get('clipOut') + 1)
                    for channel in section.get_all_channels():
                        for key in channel.get_keys():
                            old_time = key.get_time().get_editor_property(
                                'frame_number')
                            old_time_value = old_time.get_editor_property(
                                'value')
                            new_time = old_time_value + (
                                data.get('clipIn') - data.get('frameStart')
                            )
                            key.set_time(unreal.FrameNumber(value=new_time))

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"])
        }
        imprint(f"{asset_dir}/{container.get('container_name')}", data)

        EditorLevelLibrary.save_current_level()

        asset_content = EditorAssetLibrary.list_assets(
            f"{root}/{ms_asset}", recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        EditorLevelLibrary.load_level(master_level)

        if curr_level_sequence:
            LevelSequenceLib.open_level_sequence(curr_level_sequence)
            LevelSequenceLib.set_current_time(curr_time)
            LevelSequenceLib.set_lock_camera_cut_to_viewport(is_cam_lock)

        editor_subsystem.set_level_viewport_camera_info(vp_loc, vp_rot)

    def remove(self, container):
        asset_dir = container.get('namespace')
        path = Path(asset_dir)

        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        _filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[asset_dir],
            recursive_paths=False)
        sequences = ar.get_assets(_filter)

        if not sequences:
            raise Exception("Could not find sequence.")

        world = ar.get_asset_by_object_path(
            EditorLevelLibrary.get_editor_world().get_path_name())

        _filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[asset_dir],
            recursive_paths=True)
        maps = ar.get_assets(_filter)

        # There should be only one map in the list
        if not maps:
            raise Exception("Could not find map.")

        map = maps[0]

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(map.get_asset().get_path_name())

        # Remove the camera from the level.
        actors = EditorLevelLibrary.get_all_level_actors()

        for a in actors:
            if a.__class__ == unreal.CineCameraActor:
                EditorLevelLibrary.destroy_actor(a)

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(world.get_asset().get_path_name())

        # There should be only one sequence in the path.
        sequence_name = sequences[0].asset_name

        # Remove the Level Sequence from the parent.
        # We need to traverse the hierarchy from the master sequence to find
        # the level sequence.
        root = "/Game/Ayon"
        namespace = container.get('namespace').replace(f"{root}/", "")
        ms_asset = namespace.split('/')[0]
        _filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        sequences = ar.get_assets(_filter)
        master_sequence = sequences[0].get_asset()
        _filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        levels = ar.get_assets(_filter)
        master_level = levels[0].get_full_name()

        sequences = [master_sequence]

        parent = None
        for s in sequences:
            tracks = s.get_master_tracks()
            subscene_track = None
            visibility_track = None
            for t in tracks:
                if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                    subscene_track = t
                if (t.get_class() ==
                        unreal.MovieSceneLevelVisibilityTrack.static_class()):
                    visibility_track = t
            if subscene_track:
                sections = subscene_track.get_sections()
                for ss in sections:
                    if ss.get_sequence().get_name() == sequence_name:
                        parent = s
                        subscene_track.remove_section(ss)
                        break
                    sequences.append(ss.get_sequence())
                # Update subscenes indexes.
                for i, ss in enumerate(sections):
                    ss.set_row_index(i)

            if visibility_track:
                sections = visibility_track.get_sections()
                for ss in sections:
                    if (unreal.Name(f"{container.get('asset')}_map_camera")
                            in ss.get_level_names()):
                        visibility_track.remove_section(ss)
                # Update visibility sections indexes.
                i = -1
                prev_name = []
                for ss in sections:
                    if prev_name != ss.get_level_names():
                        i += 1
                    ss.set_row_index(i)
                    prev_name = ss.get_level_names()
            if parent:
                break

        assert parent, "Could not find the parent sequence"

        # Create a temporary level to delete the layout level.
        EditorLevelLibrary.save_all_dirty_levels()
        EditorAssetLibrary.make_directory(f"{root}/tmp")
        tmp_level = f"{root}/tmp/temp_map"
        if not EditorAssetLibrary.does_asset_exist(f"{tmp_level}.temp_map"):
            EditorLevelLibrary.new_level(tmp_level)
        else:
            EditorLevelLibrary.load_level(tmp_level)

        # Delete the layout directory.
        EditorAssetLibrary.delete_directory(asset_dir)

        EditorLevelLibrary.load_level(master_level)
        EditorAssetLibrary.delete_directory(f"{root}/tmp")

        # Check if there isn't any more assets in the parent folder, and
        # delete it if not.
        asset_content = EditorAssetLibrary.list_assets(
            path.parent.as_posix(), recursive=False, include_folder=True
        )

        if len(asset_content) == 0:
            EditorAssetLibrary.delete_directory(path.parent.as_posix())
