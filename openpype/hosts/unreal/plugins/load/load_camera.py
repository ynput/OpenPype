# -*- coding: utf-8 -*-
"""Load camera from FBX."""
from pathlib import Path

import unreal
from unreal import EditorAssetLibrary
from unreal import EditorLevelLibrary
from unreal import EditorLevelUtils

from openpype.pipeline import (
    AVALON_CONTAINER_ID,
    legacy_io,
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline


class CameraLoader(plugin.Loader):
    """Load Unreal StaticMesh from FBX"""

    families = ["camera"]
    label = "Load Camera"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def _get_data(self, asset_name):
        asset_doc = legacy_io.find_one({
            "type": "asset",
            "name": asset_name
        })

        return asset_doc.get("data")

    def _set_sequence_hierarchy(
        self, seq_i, seq_j, min_frame_j, max_frame_j
    ):
        tracks = seq_i.get_master_tracks()
        track = None
        for t in tracks:
            if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                track = t
                break
        if not track:
            track = seq_i.add_master_track(unreal.MovieSceneSubTrack)

        subscenes = track.get_sections()
        subscene = None
        for s in subscenes:
            if s.get_editor_property('sub_sequence') == seq_j:
                subscene = s
                break
        if not subscene:
            subscene = track.add_section()
            subscene.set_row_index(len(track.get_sections()))
            subscene.set_editor_property('sub_sequence', seq_j)
            subscene.set_range(
                min_frame_j,
                max_frame_j + 1)

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

        # Create directory for asset and avalon container
        hierarchy = context.get('asset').get('data').get('parents')
        root = "/Game/OpenPype"
        hierarchy_dir = root
        hierarchy_dir_list = []
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
            hierarchy_dir_list.append(hierarchy_dir)
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

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
            f_numbers = []
            for f in folders:
                # Get number from folder name. Splits the string by "_" and
                # removes the last element (which is a "/").
                f_numbers.append(int(f.split("_")[-1][:-1]))
            f_numbers.sort()
            if not f_numbers:
                unique_number = 1
            else:
                unique_number = f_numbers[-1] + 1

        asset_dir, container_name = tools.create_unique_asset_name(
            f"{hierarchy_dir}/{asset}/{name}_{unique_number:02d}", suffix="")

        asset_path = Path(asset_dir)
        asset_path_parent = str(asset_path.parent.as_posix())

        container_name += suffix

        EditorAssetLibrary.make_directory(asset_dir)

        # Create map for the shot, and create hierarchy of map. If the maps
        # already exist, we will use them.
        h_dir = hierarchy_dir_list[0]
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"
        if not EditorAssetLibrary.does_asset_exist(master_level):
            EditorLevelLibrary.new_level(f"{h_dir}/{h_asset}_map")

        level = f"{asset_path_parent}/{asset}_map.{asset}_map"
        if not EditorAssetLibrary.does_asset_exist(level):
            EditorLevelLibrary.new_level(f"{asset_path_parent}/{asset}_map")

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
        sequences = []
        frame_ranges = []
        i = 0
        for h in hierarchy_dir_list:
            root_content = EditorAssetLibrary.list_assets(
                h, recursive=False, include_folder=False)

            existing_sequences = [
                EditorAssetLibrary.find_asset_data(asset)
                for asset in root_content
                if EditorAssetLibrary.find_asset_data(
                    asset).get_class().get_name() == 'LevelSequence'
            ]

            if not existing_sequences:
                scene = tools.create_asset(
                    asset_name=hierarchy[i],
                    package_path=h,
                    asset_class=unreal.LevelSequence,
                    factory=unreal.LevelSequenceFactoryNew()
                )

                asset_data = legacy_io.find_one({
                    "type": "asset",
                    "name": h.split('/')[-1]
                })

                id = asset_data.get('_id')

                start_frames = []
                end_frames = []

                elements = list(
                    legacy_io.find({"type": "asset", "data.visualParent": id}))
                for e in elements:
                    start_frames.append(e.get('data').get('clipIn'))
                    end_frames.append(e.get('data').get('clipOut'))

                    elements.extend(legacy_io.find({
                        "type": "asset",
                        "data.visualParent": e.get('_id')
                    }))

                min_frame = min(start_frames)
                max_frame = max(end_frames)

                scene.set_display_rate(
                    unreal.FrameRate(asset_data.get('data').get("fps"), 1.0))
                scene.set_playback_start(min_frame)
                scene.set_playback_end(max_frame)

                sequences.append(scene)
                frame_ranges.append((min_frame, max_frame))
            else:
                for e in existing_sequences:
                    sequences.append(e.get_asset())
                    frame_ranges.append((
                        e.get_asset().get_playback_start(),
                        e.get_asset().get_playback_end()))

            i += 1

        EditorAssetLibrary.make_directory(asset_dir)

        cam_seq = tools.create_asset(
            asset_name=f"{asset}_camera",
            package_path=asset_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        # Add sequences data to hierarchy
        for i in range(0, len(sequences) - 1):
            self._set_sequence_hierarchy(
                sequences[i], sequences[i + 1],
                frame_ranges[i + 1][0], frame_ranges[i + 1][1])

        data = self._get_data(asset)
        cam_seq.set_display_rate(
            unreal.FrameRate(data.get("fps"), 1.0))
        cam_seq.set_playback_start(0)
        cam_seq.set_playback_end(data.get('clipOut') - data.get('clipIn') + 1)
        self._set_sequence_hierarchy(
            sequences[-1], cam_seq,
            data.get('clipIn'), data.get('clipOut'))

        settings = unreal.MovieSceneUserImportFBXSettings()
        settings.set_editor_property('reduce_keys', False)

        if cam_seq:
            unreal.SequencerTools.import_fbx(
                EditorLevelLibrary.get_editor_world(),
                cam_seq,
                cam_seq.get_bindings(),
                settings,
                self.fname
            )

        # Create Asset Container
        unreal_pipeline.create_container(
            container=container_name, path=asset_dir)

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(master_level)

        asset_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        root = "/Game/OpenPype"

        asset_dir = container.get('namespace')

        context = representation.get("context")

        hierarchy = context.get('hierarchy').split("/")
        h_dir = f"{root}/{hierarchy[0]}"
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"

        EditorLevelLibrary.save_current_level()

        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[asset_dir],
            recursive_paths=False)
        sequences = ar.get_assets(filter)
        filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[str(Path(asset_dir).parent.as_posix())],
            recursive_paths=True)
        maps = ar.get_assets(filter)

        # There should be only one map in the list
        EditorLevelLibrary.load_level(maps[0].get_full_name())

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
        root = "/Game/OpenPype"
        namespace = container.get('namespace').replace(f"{root}/", "")
        ms_asset = namespace.split('/')[0]
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        sequences = ar.get_assets(filter)
        master_sequence = sequences[0].get_asset()

        sequences = [master_sequence]

        parent = None
        sub_scene = None
        for s in sequences:
            tracks = s.get_master_tracks()
            subscene_track = None
            for t in tracks:
                if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                    subscene_track = t
                    break
            if subscene_track:
                sections = subscene_track.get_sections()
                for ss in sections:
                    if ss.get_sequence().get_name() == sequence_name:
                        parent = s
                        sub_scene = ss
                        # subscene_track.remove_section(ss)
                        break
                    sequences.append(ss.get_sequence())
                # Update subscenes indexes.
                i = 0
                for ss in sections:
                    ss.set_row_index(i)
                    i += 1

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

        unreal.SequencerTools.import_fbx(
            EditorLevelLibrary.get_editor_world(),
            new_sequence,
            new_sequence.get_bindings(),
            settings,
            str(representation["data"]["path"])
        )

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"])
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container.get('container_name')), data)

        EditorLevelLibrary.save_current_level()

        asset_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        EditorLevelLibrary.load_level(master_level)

    def remove(self, container):
        path = Path(container.get("namespace"))
        parent_path = str(path.parent.as_posix())

        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"{str(path.as_posix())}"],
            recursive_paths=False)
        sequences = ar.get_assets(filter)

        if not sequences:
            raise Exception("Could not find sequence.")

        world = ar.get_asset_by_object_path(
            EditorLevelLibrary.get_editor_world().get_path_name())

        filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[f"{parent_path}"],
            recursive_paths=True)
        maps = ar.get_assets(filter)

        # There should be only one map in the list
        if not maps:
            raise Exception("Could not find map.")

        map = maps[0]

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(map.get_full_name())

        # Remove the camera from the level.
        actors = EditorLevelLibrary.get_all_level_actors()

        for a in actors:
            if a.__class__ == unreal.CineCameraActor:
                EditorLevelLibrary.destroy_actor(a)

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(world.get_full_name())

        # There should be only one sequence in the path.
        sequence_name = sequences[0].asset_name

        # Remove the Level Sequence from the parent.
        # We need to traverse the hierarchy from the master sequence to find
        # the level sequence.
        root = "/Game/OpenPype"
        namespace = container.get('namespace').replace(f"{root}/", "")
        ms_asset = namespace.split('/')[0]
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        sequences = ar.get_assets(filter)
        master_sequence = sequences[0].get_asset()

        sequences = [master_sequence]

        parent = None
        for s in sequences:
            tracks = s.get_master_tracks()
            subscene_track = None
            for t in tracks:
                if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                    subscene_track = t
                    break
            if subscene_track:
                sections = subscene_track.get_sections()
                for ss in sections:
                    if ss.get_sequence().get_name() == sequence_name:
                        parent = s
                        subscene_track.remove_section(ss)
                        break
                    sequences.append(ss.get_sequence())
                # Update subscenes indexes.
                i = 0
                for ss in sections:
                    ss.set_row_index(i)
                    i += 1

            if parent:
                break

        assert parent, "Could not find the parent sequence"

        EditorAssetLibrary.delete_directory(str(path.as_posix()))

        # Check if there isn't any more assets in the parent folder, and
        # delete it if not.
        asset_content = EditorAssetLibrary.list_assets(
            parent_path, recursive=False, include_folder=True
        )

        if len(asset_content) == 0:
            EditorAssetLibrary.delete_directory(parent_path)
