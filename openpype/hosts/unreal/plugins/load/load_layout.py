# -*- coding: utf-8 -*-
"""Loader for layouts."""
import os
import json
from pathlib import Path

import unreal
from unreal import EditorAssetLibrary
from unreal import EditorLevelLibrary
from unreal import EditorLevelUtils
from unreal import AssetToolsHelpers
from unreal import FBXImportType
from unreal import MathLibrary as umath

from openpype.pipeline import (
    discover_loader_plugins,
    loaders_from_representation,
    load_container,
    get_representation_path,
    AVALON_CONTAINER_ID,
    legacy_io,
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline


class LayoutLoader(plugin.Loader):
    """Load Layout from a JSON file"""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "code-fork"
    color = "orange"
    ASSET_ROOT = "/Game/OpenPype"

    def _get_asset_containers(self, path):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        asset_content = EditorAssetLibrary.list_assets(
            path, recursive=True)

        asset_containers = []

        # Get all the asset containers
        for a in asset_content:
            obj = ar.get_asset_by_object_path(a)
            if obj.get_asset().get_class().get_name() == 'AssetContainer':
                asset_containers.append(obj)

        return asset_containers

    @staticmethod
    def _get_fbx_loader(loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshFBXLoader"
        elif family == 'model':
            name = "StaticMeshFBXLoader"
        elif family == 'camera':
            name = "CameraLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    @staticmethod
    def _get_abc_loader(loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshAlembicLoader"
        elif family == 'model':
            name = "StaticMeshAlembicLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    def _get_data(self, asset_name):
        asset_doc = legacy_io.find_one({
            "type": "asset",
            "name": asset_name
        })

        return asset_doc.get("data")

    def _set_sequence_hierarchy(
        self, seq_i, seq_j, max_frame_i, min_frame_j, max_frame_j, map_paths
    ):
        # Get existing sequencer tracks or create them if they don't exist
        tracks = seq_i.get_master_tracks()
        subscene_track = None
        visibility_track = None
        for t in tracks:
            if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                subscene_track = t
            if (t.get_class() ==
                    unreal.MovieSceneLevelVisibilityTrack.static_class()):
                visibility_track = t
        if not subscene_track:
            subscene_track = seq_i.add_master_track(unreal.MovieSceneSubTrack)
        if not visibility_track:
            visibility_track = seq_i.add_master_track(
                unreal.MovieSceneLevelVisibilityTrack)

        # Create the sub-scene section
        subscenes = subscene_track.get_sections()
        subscene = None
        for s in subscenes:
            if s.get_editor_property('sub_sequence') == seq_j:
                subscene = s
                break
        if not subscene:
            subscene = subscene_track.add_section()
            subscene.set_row_index(len(subscene_track.get_sections()))
            subscene.set_editor_property('sub_sequence', seq_j)
            subscene.set_range(
                min_frame_j,
                max_frame_j + 1)

        # Create the visibility section
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        maps = []
        for m in map_paths:
            # Unreal requires to load the level to get the map name
            EditorLevelLibrary.save_all_dirty_levels()
            EditorLevelLibrary.load_level(m)
            maps.append(str(ar.get_asset_by_object_path(m).asset_name))

        vis_section = visibility_track.add_section()
        index = len(visibility_track.get_sections())

        vis_section.set_range(
            min_frame_j,
            max_frame_j + 1)
        vis_section.set_visibility(unreal.LevelVisibility.VISIBLE)
        vis_section.set_row_index(index)
        vis_section.set_level_names(maps)

        if min_frame_j > 1:
            hid_section = visibility_track.add_section()
            hid_section.set_range(
                1,
                min_frame_j)
            hid_section.set_visibility(unreal.LevelVisibility.HIDDEN)
            hid_section.set_row_index(index)
            hid_section.set_level_names(maps)
        if max_frame_j < max_frame_i:
            hid_section = visibility_track.add_section()
            hid_section.set_range(
                max_frame_j + 1,
                max_frame_i + 1)
            hid_section.set_visibility(unreal.LevelVisibility.HIDDEN)
            hid_section.set_row_index(index)
            hid_section.set_level_names(maps)

    def _process_family(
        self, assets, class_name, transform, sequence, inst_name=None
    ):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        actors = []
        bindings = []

        for asset in assets:
            obj = ar.get_asset_by_object_path(asset).get_asset()
            if obj.get_class().get_name() == class_name:
                actor = EditorLevelLibrary.spawn_actor_from_object(
                    obj,
                    transform.get('translation')
                )
                if inst_name:
                    try:
                        # Rename method leads to crash
                        # actor.rename(name=inst_name)

                        # The label works, although it make it slightly more
                        # complicated to check for the names, as we need to
                        # loop through all the actors in the level
                        actor.set_actor_label(inst_name)
                    except Exception as e:
                        print(e)
                actor.set_actor_rotation(unreal.Rotator(
                    umath.radians_to_degrees(
                        transform.get('rotation').get('x')),
                    -umath.radians_to_degrees(
                        transform.get('rotation').get('y')),
                    umath.radians_to_degrees(
                        transform.get('rotation').get('z')),
                ), False)
                actor.set_actor_scale3d(transform.get('scale'))

                if class_name == 'SkeletalMesh':
                    skm_comp = actor.get_editor_property(
                        'skeletal_mesh_component')
                    skm_comp.set_bounds_scale(10.0)

                actors.append(actor)

                binding = None
                for p in sequence.get_possessables():
                    if p.get_name() == actor.get_name():
                        binding = p
                        break

                if not binding:
                    binding = sequence.add_possessable(actor)

                bindings.append(binding)

        return actors, bindings

    def _import_animation(
        self, asset_dir, path, instance_name, skeleton, actors_dict,
        animation_file, bindings_dict, sequence
    ):
        anim_file = Path(animation_file)
        anim_file_name = anim_file.with_suffix('')

        anim_path = f"{asset_dir}/animations/{anim_file_name}"

        # Import animation
        task = unreal.AssetImportTask()
        task.options = unreal.FbxImportUI()

        task.set_editor_property(
            'filename', str(path.with_suffix(f".{animation_file}")))
        task.set_editor_property('destination_path', anim_path)
        task.set_editor_property(
            'destination_name', f"{instance_name}_animation")
        task.set_editor_property('replace_existing', False)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', False)

        # set import options here
        task.options.set_editor_property(
            'automated_import_should_detect_type', False)
        task.options.set_editor_property(
            'original_import_type', FBXImportType.FBXIT_SKELETAL_MESH)
        task.options.set_editor_property(
            'mesh_type_to_import', FBXImportType.FBXIT_ANIMATION)
        task.options.set_editor_property('import_mesh', False)
        task.options.set_editor_property('import_animations', True)
        task.options.set_editor_property('override_full_name', True)
        task.options.set_editor_property('skeleton', skeleton)

        task.options.anim_sequence_import_data.set_editor_property(
            'animation_length',
            unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME
        )
        task.options.anim_sequence_import_data.set_editor_property(
            'import_meshes_in_bone_hierarchy', False)
        task.options.anim_sequence_import_data.set_editor_property(
            'use_default_sample_rate', False)
        task.options.anim_sequence_import_data.set_editor_property(
            'custom_sample_rate', 25.0) # TODO: get from database
        task.options.anim_sequence_import_data.set_editor_property(
            'import_custom_attribute', True)
        task.options.anim_sequence_import_data.set_editor_property(
            'import_bone_tracks', True)
        task.options.anim_sequence_import_data.set_editor_property(
            'remove_redundant_keys', False)
        task.options.anim_sequence_import_data.set_editor_property(
            'convert_scene', True)

        AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        asset_content = unreal.EditorAssetLibrary.list_assets(
            anim_path, recursive=False, include_folder=False
        )

        animation = None

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)
            imported_asset_data = unreal.EditorAssetLibrary.find_asset_data(a)
            imported_asset = unreal.AssetRegistryHelpers.get_asset(
                imported_asset_data)
            if imported_asset.__class__ == unreal.AnimSequence:
                animation = imported_asset
                break

        if animation:
            actor = None
            if actors_dict.get(instance_name):
                for a in actors_dict.get(instance_name):
                    if a.get_class().get_name() == 'SkeletalMeshActor':
                        actor = a
                        break

            animation.set_editor_property('enable_root_motion', True)
            actor.skeletal_mesh_component.set_editor_property(
                'animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            actor.skeletal_mesh_component.animation_data.set_editor_property(
                'anim_to_play', animation)

            # Add animation to the sequencer
            bindings = bindings_dict.get(instance_name)

            ar = unreal.AssetRegistryHelpers.get_asset_registry()

            for binding in bindings:
                tracks = binding.get_tracks()
                track = None
                if not tracks:
                    track = binding.add_track(
                        unreal.MovieSceneSkeletalAnimationTrack)
                else:
                    track = tracks[0]

                sections = track.get_sections()
                section = None
                if not sections:
                    section = track.add_section()
                else:
                    section = sections[0]

                    sec_params = section.get_editor_property('params')
                    curr_anim = sec_params.get_editor_property('animation')

                    if curr_anim:
                        # Checks if the animation path has a container.
                        # If it does, it means that the animation is already
                        # in the sequencer.
                        anim_path = str(Path(
                            curr_anim.get_path_name()).parent
                        ).replace('\\', '/')

                        filter = unreal.ARFilter(
                            class_names=["AssetContainer"],
                            package_paths=[anim_path],
                            recursive_paths=False)
                        containers = ar.get_assets(filter)

                        if len(containers) > 0:
                            return

                section.set_range(
                    sequence.get_playback_start(),
                    sequence.get_playback_end())
                sec_params = section.get_editor_property('params')
                sec_params.set_editor_property('animation', animation)

    def _generate_sequence(self, h, h_dir):
        tools = unreal.AssetToolsHelpers().get_asset_tools()

        sequence = tools.create_asset(
            asset_name=h,
            package_path=h_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        asset_data = legacy_io.find_one({
            "type": "asset",
            "name": h_dir.split('/')[-1]
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

        sequence.set_display_rate(
            unreal.FrameRate(asset_data.get('data').get("fps"), 1.0))
        sequence.set_playback_start(min_frame)
        sequence.set_playback_end(max_frame)

        tracks = sequence.get_master_tracks()
        track = None
        for t in tracks:
            if (t.get_class() ==
                    unreal.MovieSceneCameraCutTrack.static_class()):
                track = t
                break
        if not track:
            track = sequence.add_master_track(
                unreal.MovieSceneCameraCutTrack)

        return sequence, (min_frame, max_frame)

    def _process(self, lib_path, asset_dir, sequence, loaded=None):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        with open(lib_path, "r") as fp:
            data = json.load(fp)

        all_loaders = discover_loader_plugins()

        if not loaded:
            loaded = []

        path = Path(lib_path)

        skeleton_dict = {}
        actors_dict = {}
        bindings_dict = {}

        loaded_assets = []

        for element in data:
            reference = None
            if element.get('reference_fbx'):
                reference = element.get('reference_fbx')
            elif element.get('reference_abc'):
                reference = element.get('reference_abc')

            # If reference is None, this element is skipped, as it cannot be
            # imported in Unreal
            if not reference:
                continue

            instance_name = element.get('instance_name')

            skeleton = None

            if reference not in loaded:
                loaded.append(reference)

                family = element.get('family')
                loaders = loaders_from_representation(
                    all_loaders, reference)

                loader = None

                if reference == element.get('reference_fbx'):
                    loader = self._get_fbx_loader(loaders, family)
                elif reference == element.get('reference_abc'):
                    loader = self._get_abc_loader(loaders, family)

                if not loader:
                    continue

                options = {
                    # "asset_dir": asset_dir
                }

                assets = load_container(
                    loader,
                    reference,
                    namespace=instance_name,
                    options=options
                )

                container = None

                for asset in assets:
                    obj = ar.get_asset_by_object_path(asset).get_asset()
                    if obj.get_class().get_name() == 'AssetContainer':
                        container = obj
                    if obj.get_class().get_name() == 'Skeleton':
                        skeleton = obj

                loaded_assets.append(container.get_path_name())

                instances = [
                    item for item in data
                    if (item.get('reference_fbx') == reference or
                        item.get('reference_abc') == reference)]

                for instance in instances:
                    transform = instance.get('transform')
                    inst = instance.get('instance_name')

                    actors = []

                    if family == 'model':
                        actors, _ = self._process_family(
                            assets, 'StaticMesh', transform, sequence, inst)
                    elif family == 'rig':
                        actors, bindings = self._process_family(
                            assets, 'SkeletalMesh', transform, sequence, inst)
                        actors_dict[inst] = actors
                        bindings_dict[inst] = bindings

                if skeleton:
                    skeleton_dict[reference] = skeleton
            else:
                skeleton = skeleton_dict.get(reference)

            animation_file = element.get('animation')

            if animation_file and skeleton:
                self._import_animation(
                    asset_dir, path, instance_name, skeleton, actors_dict,
                    animation_file, bindings_dict, sequence)

        return loaded_assets

    @staticmethod
    def _remove_family(assets, components, class_name, prop_name):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        objects = []
        for a in assets:
            obj = ar.get_asset_by_object_path(a)
            if obj.get_asset().get_class().get_name() == class_name:
                objects.append(obj)
        for obj in objects:
            for comp in components:
                if comp.get_editor_property(prop_name) == obj.get_asset():
                    comp.get_owner().destroy_actor()

    def _remove_actors(self, path):
        asset_containers = self._get_asset_containers(path)

        # Get all the static and skeletal meshes components in the level
        components = EditorLevelLibrary.get_all_level_actors_components()
        static_meshes_comp = [
            c for c in components
            if c.get_class().get_name() == 'StaticMeshComponent']
        skel_meshes_comp = [
            c for c in components
            if c.get_class().get_name() == 'SkeletalMeshComponent']

        # For all the asset containers, get the static and skeletal meshes.
        # Then, check the components in the level and destroy the matching
        # actors.
        for asset_container in asset_containers:
            package_path = asset_container.get_editor_property('package_path')
            family = EditorAssetLibrary.get_metadata_tag(
                asset_container.get_asset(), 'family')
            assets = EditorAssetLibrary.list_assets(
                str(package_path), recursive=False)
            if family == 'model':
                self._remove_family(
                    assets, static_meshes_comp, 'StaticMesh', 'static_mesh')
            elif family == 'rig':
                self._remove_family(
                    assets, skel_meshes_comp, 'SkeletalMesh', 'skeletal_mesh')

    def load(self, context, name, namespace, options):
        """Load and containerise representation into Content Browser.

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
            options (dict): Those would be data to be imprinted. This is not
                used now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """
        # Create directory for asset and avalon container
        hierarchy = context.get('asset').get('data').get('parents')
        root = self.ASSET_ROOT
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
        asset_dir, container_name = tools.create_unique_asset_name(
            "{}/{}/{}".format(hierarchy_dir, asset, name), suffix="")

        container_name += suffix

        EditorAssetLibrary.make_directory(asset_dir)

        # Create map for the shot, and create hierarchy of map. If the maps
        # already exist, we will use them.
        h_dir = hierarchy_dir_list[0]
        h_asset = hierarchy[0]
        master_level = f"{h_dir}/{h_asset}_map.{h_asset}_map"
        if not EditorAssetLibrary.does_asset_exist(master_level):
            EditorLevelLibrary.new_level(f"{h_dir}/{h_asset}_map")

        level = f"{asset_dir}/{asset}_map.{asset}_map"
        EditorLevelLibrary.new_level(f"{asset_dir}/{asset}_map")

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
        for (h_dir, h) in zip(hierarchy_dir_list, hierarchy):
            root_content = EditorAssetLibrary.list_assets(
                h_dir, recursive=False, include_folder=False)

            existing_sequences = [
                EditorAssetLibrary.find_asset_data(asset)
                for asset in root_content
                if EditorAssetLibrary.find_asset_data(
                    asset).get_class().get_name() == 'LevelSequence'
            ]

            if not existing_sequences:
                sequence, frame_range = self._generate_sequence(h, h_dir)

                sequences.append(sequence)
                frame_ranges.append(frame_range)
            else:
                for e in existing_sequences:
                    sequences.append(e.get_asset())
                    frame_ranges.append((
                        e.get_asset().get_playback_start(),
                        e.get_asset().get_playback_end()))

        shot = tools.create_asset(
            asset_name=asset,
            package_path=asset_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        # sequences and frame_ranges have the same length
        for i in range(0, len(sequences) - 1):
            self._set_sequence_hierarchy(
                sequences[i], sequences[i + 1],
                frame_ranges[i][1],
                frame_ranges[i + 1][0], frame_ranges[i + 1][1],
                [level])

        data = self._get_data(asset)
        shot.set_display_rate(
            unreal.FrameRate(data.get("fps"), 1.0))
        shot.set_playback_start(0)
        shot.set_playback_end(data.get('clipOut') - data.get('clipIn') + 1)
        self._set_sequence_hierarchy(
            sequences[-1], shot,
            frame_ranges[-1][1],
            data.get('clipIn'), data.get('clipOut'),
            [level])

        EditorLevelLibrary.load_level(level)

        loaded_assets = self._process(self.fname, asset_dir, shot)

        for s in sequences:
            EditorAssetLibrary.save_asset(s.get_full_name())

        EditorLevelLibrary.save_current_level()

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
            "family": context["representation"]["context"]["family"],
            "loaded_assets": loaded_assets
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        asset_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        EditorLevelLibrary.load_level(master_level)

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

        # # Create a temporary level to delete the layout level.
        # EditorLevelLibrary.save_all_dirty_levels()
        # EditorAssetLibrary.make_directory(f"{root}/tmp")
        # tmp_level = f"{root}/tmp/temp_map"
        # if not EditorAssetLibrary.does_asset_exist(f"{tmp_level}.temp_map"):
        #     EditorLevelLibrary.new_level(tmp_level)
        # else:
        #     EditorLevelLibrary.load_level(tmp_level)

        # Get layout level
        filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[asset_dir],
            recursive_paths=False)
        levels = ar.get_assets(filter)
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[asset_dir],
            recursive_paths=False)
        sequences = ar.get_assets(filter)

        layout_level = levels[0].get_editor_property('object_path')

        EditorLevelLibrary.save_all_dirty_levels()
        EditorLevelLibrary.load_level(layout_level)

        # Delete all the actors in the level
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in actors:
            unreal.EditorLevelLibrary.destroy_actor(actor)

        EditorLevelLibrary.save_current_level()

        EditorAssetLibrary.delete_directory(f"{asset_dir}/animations/")

        source_path = get_representation_path(representation)

        loaded_assets = self._process(
            source_path, asset_dir, sequences[0].get_asset())

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"]),
            "loaded_assets": loaded_assets
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
        """
        Delete the layout. First, check if the assets loaded with the layout
        are used by other layouts. If not, delete the assets.
        """
        path = Path(container.get("namespace"))

        containers = unreal_pipeline.ls()
        layout_containers = [
            c for c in containers
            if (c.get('asset_name') != container.get('asset_name') and
                c.get('family') == "layout")]

        # Check if the assets have been loaded by other layouts, and deletes
        # them if they haven't.
        for asset in container.get('loaded_assets'):
            layouts = [
                lc for lc in layout_containers
                if asset in lc.get('loaded_assets')]

            if len(layouts) == 0:
                EditorAssetLibrary.delete_directory(str(Path(asset).parent))

        # Remove the Level Sequence from the parent.
        # We need to traverse the hierarchy from the master sequence to find
        # the level sequence.
        root = "/Game/OpenPype"
        namespace = container.get('namespace').replace(f"{root}/", "")
        ms_asset = namespace.split('/')[0]
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        sequences = ar.get_assets(filter)
        master_sequence = sequences[0].get_asset()
        filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[f"{root}/{ms_asset}"],
            recursive_paths=False)
        levels = ar.get_assets(filter)
        master_level = levels[0].get_editor_property('object_path')

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
                    if ss.get_sequence().get_name() == container.get('asset'):
                        parent = s
                        subscene_track.remove_section(ss)
                        break
                    sequences.append(ss.get_sequence())
                # Update subscenes indexes.
                i = 0
                for ss in sections:
                    ss.set_row_index(i)
                    i += 1

            if visibility_track:
                sections = visibility_track.get_sections()
                for ss in sections:
                    if (unreal.Name(f"{container.get('asset')}_map")
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
        EditorAssetLibrary.delete_directory(str(path))

        EditorLevelLibrary.load_level(master_level)
        EditorAssetLibrary.delete_directory(f"{root}/tmp")

        EditorLevelLibrary.save_current_level()

        # Delete the parent folder if there aren't any more layouts in it.
        asset_content = EditorAssetLibrary.list_assets(
            str(path.parent), recursive=False, include_folder=True
        )

        if len(asset_content) == 0:
            EditorAssetLibrary.delete_directory(str(path.parent))
