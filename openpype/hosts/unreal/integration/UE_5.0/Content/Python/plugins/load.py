import ast
from pathlib import Path

import unreal


def get_asset(path):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    return ar.get_asset_by_object_path(path).get_asset()


def create_unique_asset_name(root, asset, name, version="", suffix=""):
    tools = unreal.AssetToolsHelpers().get_asset_tools()
    subset = f"{name}_v{version:03d}" if version else name
    return tools.create_unique_asset_name(
        f"{root}/{asset}/{subset}", suffix)


def does_asset_exist(asset_path):
    return unreal.EditorAssetLibrary.does_asset_exist(asset_path)


def does_directory_exist(directory_path):
    return unreal.EditorAssetLibrary.does_directory_exist(directory_path)


def make_directory(directory_path):
    unreal.EditorAssetLibrary.make_directory(directory_path)


def new_level(level_path):
    unreal.EditorLevelLibrary.new_level(level_path)


def load_level(level_path):
    unreal.EditorLevelLibrary.load_level(level_path)


def save_current_level():
    unreal.EditorLevelLibrary.save_current_level()


def save_all_dirty_levels():
    unreal.EditorLevelLibrary.save_all_dirty_levels()


def add_level_to_world(level_path):
    unreal.EditorLevelUtils.add_level_to_world(
        unreal.EditorLevelLibrary.get_editor_world(),
        level_path,
        unreal.LevelStreamingDynamic
    )


def list_assets(directory_path, recursive, include_folder):
    recursive = ast.literal_eval(recursive)
    include_folder = ast.literal_eval(include_folder)
    return str(unreal.EditorAssetLibrary.list_assets(
        directory_path, recursive, include_folder))


def get_assets_of_class(asset_list, class_name):
    asset_list = ast.literal_eval(asset_list)
    assets = []
    for asset in asset_list:
        if unreal.EditorAssetLibrary.does_asset_exist(asset):
            asset_object = unreal.EditorAssetLibrary.load_asset(asset)
            if asset_object.get_class().get_name() == class_name:
                assets.append(asset)
    return assets


def save_listed_assets(asset_list):
    asset_list = ast.literal_eval(asset_list)
    for asset in asset_list:
        unreal.EditorAssetLibrary.save_asset(asset)


def _import(
    task_arg, options_arg,
    task_properties, options_properties, options_extra_properties
):
    task = task_arg
    options = options_arg

    task_properties = ast.literal_eval(task_properties)
    for prop in task_properties:
        task.set_editor_property(prop[0], eval(prop[1]))

    options_properties = ast.literal_eval(options_properties)
    for prop in options_properties:
        options.set_editor_property(prop[0], eval(prop[1]))

    options_extra_properties = ast.literal_eval(options_extra_properties)
    for prop in options_extra_properties:
        options.get_editor_property(prop[0]).set_editor_property(
            prop[1], eval(prop[2]))

    return task, options


def import_abc_task(task_properties, options_properties, options_extra_properties):
    task, options = _import(
        unreal.AssetImportTask(), unreal.AbcImportSettings(),
        task_properties, options_properties, options_extra_properties)

    task.options = options

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


def import_fbx_task(task_properties, options_properties, options_extra_properties):
    task, options = _import(
        unreal.AssetImportTask(), unreal.FbxImportUI(),
        task_properties, options_properties, options_extra_properties)

    task.options = options

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


def get_sequence_frame_range(sequence_path):
    sequence = get_asset(sequence_path)
    return str((sequence.get_playback_start(), sequence.get_playback_end()))


def generate_sequence(asset_name, asset_path, start_frame, end_frame, fps):
    tools = unreal.AssetToolsHelpers().get_asset_tools()

    sequence = tools.create_asset(
        asset_name=asset_name,
        package_path=asset_path,
        asset_class=unreal.LevelSequence,
        factory=unreal.LevelSequenceFactoryNew()
    )

    sequence.set_display_rate(unreal.FrameRate(fps, 1.0))
    sequence.set_playback_start(start_frame)
    sequence.set_playback_end(end_frame)

    return sequence.get_path_name()


def generate_master_sequence(
    asset_name, asset_path, start_frame, end_frame, fps
):
    sequence_path = generate_sequence(
        asset_name, asset_path, start_frame, end_frame, fps)
    sequence = get_asset(sequence_path)

    tracks = sequence.get_master_tracks()
    track = None
    for t in tracks:
        if (t.get_class() == unreal.MovieSceneCameraCutTrack.static_class()):
            track = t
            break
    if not track:
        track = sequence.add_master_track(unreal.MovieSceneCameraCutTrack)

    return sequence.get_path_name()

def set_sequence_hierarchy(
    parent_path, child_path,
    parent_end_frame, child_start_frame, child_end_frame, map_paths_str
):
    map_paths = ast.literal_eval(map_paths_str)

    parent = get_asset(parent_path)
    child = get_asset(child_path)

    # Get existing sequencer tracks or create them if they don't exist
    tracks = parent.get_master_tracks()
    subscene_track = None
    visibility_track = None
    for t in tracks:
        if (t.get_class() == 
                unreal.MovieSceneSubTrack.static_class()):
            subscene_track = t
        if (t.get_class() ==
                unreal.MovieSceneLevelVisibilityTrack.static_class()):
            visibility_track = t
    if not subscene_track:
        subscene_track = parent.add_master_track(
            unreal.MovieSceneSubTrack)
    if not visibility_track:
        visibility_track = parent.add_master_track(
            unreal.MovieSceneLevelVisibilityTrack)

    # Create the sub-scene section
    subscenes = subscene_track.get_sections()
    subscene = None
    for s in subscenes:
        if s.get_editor_property('sub_sequence') == child:
            subscene = s
            break
    if not subscene:
        subscene = subscene_track.add_section()
        subscene.set_row_index(len(subscene_track.get_sections()))
        subscene.set_editor_property('sub_sequence', child)
        subscene.set_range(child_start_frame, child_end_frame + 1)

    # Create the visibility section
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    maps = []
    for m in map_paths:
        # Unreal requires to load the level to get the map name
        unreal.EditorLevelLibrary.save_all_dirty_levels()
        unreal.EditorLevelLibrary.load_level(m)
        maps.append(str(ar.get_asset_by_object_path(m).asset_name))

    vis_section = visibility_track.add_section()
    index = len(visibility_track.get_sections())

    vis_section.set_range(child_start_frame, child_end_frame + 1)
    vis_section.set_visibility(unreal.LevelVisibility.VISIBLE)
    vis_section.set_row_index(index)
    vis_section.set_level_names(maps)

    if child_start_frame > 1:
        hid_section = visibility_track.add_section()
        hid_section.set_range(1, child_start_frame)
        hid_section.set_visibility(unreal.LevelVisibility.HIDDEN)
        hid_section.set_row_index(index)
        hid_section.set_level_names(maps)
    if child_end_frame < parent_end_frame:
        hid_section = visibility_track.add_section()
        hid_section.set_range(child_end_frame + 1, parent_end_frame + 1)
        hid_section.set_visibility(unreal.LevelVisibility.HIDDEN)
        hid_section.set_row_index(index)
        hid_section.set_level_names(maps)


def process_family(assets_str, class_name, transform_str, basis_str, sequence_path):
    assets = ast.literal_eval(assets_str)
    basis = ast.literal_eval(transform_str)
    transform = ast.literal_eval(basis_str)

    actors = []
    bindings = []

    sequence = get_asset(sequence_path) if sequence_path else None

    for asset in assets:
        print(asset)
        obj = get_asset(asset)
        if obj and obj.get_class().get_name() == class_name:
            basis_matrix = unreal.Matrix(
                basis[0],
                basis[1],
                basis[2],
                basis[3]
            )
            transform_matrix = unreal.Matrix(
                transform[0],
                transform[1],
                transform[2],
                transform[3]
            )
            new_transform = (
                basis_matrix.get_inverse() * transform_matrix * basis_matrix
            ).transform()
            actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
                obj, new_transform.translation)
            actor.set_actor_rotation(new_transform.rotation.rotator(), False)
            actor.set_actor_scale3d(new_transform.scale3d)

            if class_name == 'SkeletalMesh':
                skm_comp = actor.get_editor_property('skeletal_mesh_component')
                skm_comp.set_bounds_scale(10.0)

            actors.append(actor.get_path_name())

            if sequence:
                binding = None
                for p in sequence.get_possessables():
                    if p.get_name() == actor.get_name():
                        binding = p
                        break

                if not binding:
                    binding = sequence.add_possessable(actor)

                bindings.append(binding.get_id().to_string())

    return (actors, bindings)


def apply_animation_to_actor(actor_path, animation_path):
    actor = get_asset(actor_path)
    animation = get_asset(animation_path)

    animation.set_editor_property('enable_root_motion', True)

    actor.skeletal_mesh_component.set_editor_property(
        'animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    actor.skeletal_mesh_component.animation_data.set_editor_property(
        'anim_to_play', animation)

def add_animation_to_sequencer(sequence_path, binding_guid, animation_path):
    sequence = get_asset(sequence_path)
    animation = get_asset(animation_path)

    binding = None
    for b in sequence.get_possessables():
        if b.get_id().to_string() == binding_guid:
            binding = b
            break

    tracks = binding.get_tracks()
    track = None
    track = tracks[0] if tracks else binding.add_track(
        unreal.MovieSceneSkeletalAnimationTrack)

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
            # If it does, it means that the animation is
            # already in the sequencer.
            anim_path = str(Path(
                curr_anim.get_path_name()).parent
            ).replace('\\', '/')

            ar = unreal.AssetRegistryHelpers.get_asset_registry()

            _filter = unreal.ARFilter(
                class_names=["AssetContainer"],
                package_paths=[anim_path],
                recursive_paths=False)
            containers = ar.get_assets(_filter)

            if len(containers) > 0:
                return

    section.set_range(
        sequence.get_playback_start(),
        sequence.get_playback_end())
    sec_params = section.get_editor_property('params')
    sec_params.set_editor_property('animation', animation)

