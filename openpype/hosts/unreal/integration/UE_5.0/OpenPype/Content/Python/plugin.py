from pathlib import Path

import unreal

from helpers import (
    get_params,
    format_string,
    get_asset,
    get_subsequences
)
from pipeline import (
    UNREAL_VERSION,
    ls,
)


def create_look(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            path (str): path to the instance
            selected_asset (str): path to the selected asset
    """
    path, selected_asset = get_params(params, 'path', 'selected_asset')

    # Create a new cube static mesh
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    cube = ar.get_asset_by_object_path("/Engine/BasicShapes/Cube.Cube")

    # Get the mesh of the selected object
    original_mesh = ar.get_asset_by_object_path(selected_asset).get_asset()
    materials = original_mesh.get_editor_property('static_materials')

    members = []

    # Add the materials to the cube
    for material in materials:
        mat_name = material.get_editor_property('material_slot_name')
        object_path = f"{path}/{mat_name}.{mat_name}"
        unreal_object = unreal.EditorAssetLibrary.duplicate_loaded_asset(
            cube.get_asset(), object_path
        )

        # Remove the default material of the cube object
        unreal_object.get_editor_property('static_materials').pop()

        unreal_object.add_material(
            material.get_editor_property('material_interface'))

        members.append(object_path)

        unreal.EditorAssetLibrary.save_asset(object_path)

    return {"return": members}


def create_render(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            path (str): path to the instance
            selected_asset (str): path to the selected asset
    """
    selected_asset_path = get_params(params, 'path', 'selected_asset')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    selected_asset = ar.get_asset_by_object_path(
        selected_asset_path).get_asset()

    if selected_asset.get_class().get_name() != "LevelSequence":
        unreal.log_error(
            f"Skipping {selected_asset.get_name()}. It isn't a Level "
            "Sequence.")

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
        return master_seq, master_lvl, master_seq_data

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
                return master_seq, master_lvl, master_seq_data

            seq_data_list.append(curr_data)

    return None, None, None


def create_unique_asset_name(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            root (str): root path of the asset
            asset (str): name of the asset
            name (str): name of the subset
            version (int): version of the subset
            suffix (str): suffix of the asset
    """
    root, asset, name, version, suffix = get_params(
        params, 'root', 'asset', 'name', 'version', 'suffix')

    if not suffix:
        suffix = ""

    tools = unreal.AssetToolsHelpers().get_asset_tools()
    subset = f"{name}_v{version:03d}" if version else name
    return {"return": tools.create_unique_asset_name(
        f"{root}/{asset}/{subset}", suffix)}


def get_current_level():
    curr_level = (unreal.LevelEditorSubsystem().get_current_level()
                  if UNREAL_VERSION >= 5
                  else unreal.EditorLevelLibrary.get_editor_world())

    curr_level_path = curr_level.get_outer().get_path_name()
    # If the level path does not start with "/Game/", the current
    # level is a temporary, unsaved level.
    return {
        "return": curr_level_path
        if curr_level_path.startswith("/Game/") else None}


def add_level_to_world(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            level_path (str): path to the level
    """
    level_path = get_params(params, 'level_path')

    unreal.EditorLevelUtils.add_level_to_world(
        unreal.EditorLevelLibrary.get_editor_world(),
        level_path,
        unreal.LevelStreamingDynamic
    )


def list_assets(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            directory_path (str): path to the directory
            recursive (bool): whether to list assets recursively
            include_folder (bool): whether to include folders
    """
    directory_path, recursive, include_folder = get_params(
        params, 'directory_path', 'recursive', 'include_folder')

    return {"return": list(unreal.EditorAssetLibrary.list_assets(
        directory_path, recursive, include_folder))}


def get_assets_of_class(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_list (list): list of assets
            class_name (str): name of the class
    """
    asset_list, class_name = get_params(params, 'asset_list', 'class_name')

    assets = []
    for asset in asset_list:
        if unreal.EditorAssetLibrary.does_asset_exist(asset):
            asset_object = unreal.EditorAssetLibrary.load_asset(asset)
            if asset_object.get_class().get_name() == class_name:
                assets.append(asset)
    return {"return": assets}


def get_all_assets_of_class(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            class_name (str): name of the class
            path (str): path to the directory
            recursive (bool): whether to list assets recursively
    """
    class_name, path, recursive = get_params(
        params, 'class_name', 'path', 'recursive')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    ar_filter = unreal.ARFilter(
        class_names=[class_name],
        package_paths=[path],
        recursive_paths=recursive)

    assets = ar.get_assets(ar_filter)

    return {
        "return": [str(asset.get_editor_property('object_path'))
                   for asset in assets]}


def get_first_asset_of_class(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            class_name (str): name of the class
            path (str): path to the directory
            recursive (bool): whether to list assets recursively
    """
    return get_all_assets_of_class(params)[0]


def _get_first_asset_of_class(class_name, path, recursive):
    """
    Args:
        class_name (str): name of the class
        path (str): path to the directory
        recursive (bool): whether to list assets recursively
    """
    return get_first_asset_of_class(format_string(str({
        "class_name": class_name,
        "path": path,
        "recursive": recursive}))).get('return')


def save_listed_assets(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_list (list): list of assets
    """
    asset_list = get_params(params, 'asset_list')

    for asset in asset_list:
        unreal.EditorAssetLibrary.save_asset(asset)


def _import(
    filename, destination_path, destination_name, replace_existing,
    automated, save, options, options_properties, options_extra_properties
):
    """
    Args:
        filename (str): path to the file
        destination_path (str): path to the destination
        destination_name (str): name of the destination
        replace_existing (bool): whether to replace existing assets
        automated (bool): whether to import the asset automatically
        save (bool): whether to save the asset
        options: options for the import
        options_properties (list): list of properties for the options
        options_extra_properties (list): list of extra properties for the
            options
    """
    task = unreal.AssetImportTask()

    task.set_editor_property('filename', filename)
    task.set_editor_property('destination_path', destination_path)
    task.set_editor_property('destination_name', destination_name)
    task.set_editor_property('replace_existing', replace_existing)
    task.set_editor_property('automated', automated)
    task.set_editor_property('save', save)

    for prop in options_properties:
        options.set_editor_property(prop[0], eval(prop[1]))

    for prop in options_extra_properties:
        options.get_editor_property(prop[0]).set_editor_property(
            prop[1], eval(prop[2]))

    task.options = options

    return task


def import_abc_task(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            filename (str): path to the file
            destination_path (str): path to the destination
            destination_name (str): name of the file
            replace_existing (bool): whether to replace existing assets
            automated (bool): whether to run the task automatically
            save (bool): whether to save the asset
            options_properties (list): list of properties for the options
            sub_options_properties (list): list of properties that require
                extra processing
            conversion_settings (dict): dictionary of conversion settings
    """
    (filename, destination_path, destination_name, replace_existing,
     automated, save, options_properties, sub_options_properties,
     conversion_settings) = get_params(
        params, 'filename', 'destination_path', 'destination_name',
        'replace_existing', 'automated', 'save', 'options_properties',
        'sub_options_properties', 'conversion_settings')

    task = _import(
        filename, destination_path, destination_name, replace_existing,
        automated, save, unreal.AbcImportSettings(),
        options_properties, sub_options_properties)

    if conversion_settings:
        conversion = unreal.AbcConversionSettings(
            preset=unreal.AbcConversionPreset.CUSTOM,
            flip_u=conversion_settings.get("flip_u"),
            flip_v=conversion_settings.get("flip_v"),
            rotation=conversion_settings.get("rotation"),
            scale=conversion_settings.get("scale"))

        task.options.conversion_settings = conversion

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


def import_fbx_task(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            task_properties (list): list of properties for the task
            options_properties (list): list of properties for the options
            options_extra_properties (list): list of extra properties for the
                options
    """
    (filename, destination_path, destination_name, replace_existing,
     automated, save, options_properties, sub_options_properties) = get_params(
        params, 'filename', 'destination_path', 'destination_name',
        'replace_existing', 'automated', 'save', 'options_properties',
        'sub_options_properties')

    task = _import(
        filename, destination_path, destination_name, replace_existing,
        automated, save, unreal.FbxImportUI(),
        options_properties, sub_options_properties)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


def get_sequence_frame_range(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            sequence_path (str): path to the sequence
    """
    sequence_path = get_params(params, 'sequence_path')

    sequence = get_asset(sequence_path)
    return {"return": (
        sequence.get_playback_start(), sequence.get_playback_end())}


def generate_sequence(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_name (str): name of the asset
            asset_path (str): path to the asset
            start_frame (int): start frame of the sequence
            end_frame (int): end frame of the sequence
            fps (int): frames per second
    """
    asset_name, asset_path, start_frame, end_frame, fps = get_params(
        params, 'asset_name', 'asset_path', 'start_frame', 'end_frame', 'fps')

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

    return {"return": sequence.get_path_name()}


def generate_master_sequence(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_name (str): name of the asset
            asset_path (str): path to the asset
            start_frame (int): start frame of the sequence
            end_frame (int): end frame of the sequence
            fps (int): frames per second
    """
    sequence_path = generate_sequence(params).get("return")
    sequence = get_asset(sequence_path)

    tracks = sequence.get_master_tracks()
    track = next(
        (
            t
            for t in tracks
            if t.get_class().get_name() == "MovieSceneCameraCutTrack"
        ),
        None
    )
    if not track:
        sequence.add_master_track(unreal.MovieSceneCameraCutTrack)

    return {"return": sequence.get_path_name()}


def set_sequence_hierarchy(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            parent_path (str): path to the parent sequence
            child_path (str): path to the child sequence
            child_start_frame (int): start frame of the child sequence
            child_end_frame (int): end frame of the child sequence
    """
    parent_path, child_path, child_start_frame, child_end_frame = get_params(
        params, 'parent_path', 'child_path', 'child_start_frame',
        'child_end_frame')

    parent = get_asset(parent_path)
    child = get_asset(child_path)

    # Get existing sequencer tracks or create them if they don't exist
    tracks = parent.get_master_tracks()
    subscene_track = next(
        (
            t
            for t in tracks
            if t.get_class().get_name() == "MovieSceneSubTrack"
        ),
        None,
    )
    if not subscene_track:
        subscene_track = parent.add_master_track(
            unreal.MovieSceneSubTrack)

    # Create the sub-scene section
    subscenes = subscene_track.get_sections()
    subscene = next(
        (
            s
            for s in subscenes
            if s.get_editor_property('sub_sequence') == child
        ),
        None,
    )
    if not subscene:
        subscene = subscene_track.add_section()
        subscene.set_row_index(len(subscene_track.get_sections()))
        subscene.set_editor_property('sub_sequence', child)
        subscene.set_range(child_start_frame, child_end_frame + 1)


def set_sequence_visibility(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            parent_path (str): path to the parent sequence
            parent_end_frame (int): end frame of the parent sequence
            child_start_frame (int): start frame of the child sequence
            child_end_frame (int): end frame of the child sequence
            map_paths (list): list of paths to the maps
    """
    (parent_path, parent_end_frame, child_start_frame, child_end_frame,
     map_paths) = get_params(params, 'parent_path', 'parent_end_frame',
                             'child_start_frame', 'child_end_frame',
                             'map_paths')

    parent = get_asset(parent_path)

    # Get existing sequencer tracks or create them if they don't exist
    tracks = parent.get_master_tracks()
    visibility_track = next(
        (
            t
            for t in tracks
            if t.get_class().get_name() == "MovieSceneLevelVisibilityTrack"
        ),
        None,
    )
    if not visibility_track:
        visibility_track = parent.add_master_track(
            unreal.MovieSceneLevelVisibilityTrack)

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


def _get_transform(import_data, basis_data, transform_data):
    """
    Args:
        import_data (unreal.FbxImportUI): import data
        basis_data (list): basis data
        transform_data (list): transform data
    """
    filename = import_data.get_first_filename()
    path = Path(filename)

    conversion = unreal.Matrix.IDENTITY.transform()
    tuning = unreal.Matrix.IDENTITY.transform()

    basis = unreal.Matrix(
        basis_data[0],
        basis_data[1],
        basis_data[2],
        basis_data[3]
    ).transform()
    transform = unreal.Matrix(
        transform_data[0],
        transform_data[1],
        transform_data[2],
        transform_data[3]
    ).transform()

    # Check for the conversion settings. We cannot access
    # the alembic conversion settings, so we assume that
    # the maya ones have been applied.
    if path.suffix == '.fbx':
        loc = import_data.import_translation
        rot = import_data.import_rotation.to_vector()
        scale = import_data.import_uniform_scale
        conversion = unreal.Transform(
            location=[loc.x, loc.y, loc.z],
            rotation=[rot.x, -rot.y, -rot.z],
            scale=[scale, scale, scale]
        )
        tuning = unreal.Transform(
            rotation=[0.0, 0.0, 0.0],
            scale=[1.0, 1.0, 1.0]
        )
    elif path.suffix == '.abc':
        # This is the standard conversion settings for
        # alembic files from Maya.
        conversion = unreal.Transform(
            location=[0.0, 0.0, 0.0],
            rotation=[90.0, 0.0, 0.0],
            scale=[1.0, -1.0, 1.0]
        )
        tuning = unreal.Transform(
            rotation=[0.0, 0.0, 0.0],
            scale=[1.0, 1.0, 1.0]
        )

    new_transform = basis.inverse() * transform * basis
    return tuning * conversion.inverse() * new_transform


def process_family(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            assets (list): list of paths to the assets
            class_name (str): name of the class to spawn
            instance_name (str): name of the instance
            transform (list): list of 4 vectors representing the transform
            basis (list): list of 4 vectors representing the basis
            sequence_path (str): path to the sequence
    """
    (assets, class_name, instance_name, transform, basis,
     sequence_path) = get_params(params, 'assets', 'class_name',
                                 'instance_name', 'transform', 'basis',
                                 'sequence_path')

    basis = eval(basis)
    transform = eval(transform)

    actors = []
    bindings = []

    component_property = ''
    mesh_property = ''

    if class_name == 'SkeletalMesh':
        component_property = 'skeletal_mesh_component'
        mesh_property = 'skeletal_mesh'
    elif class_name == 'StaticMesh':
        component_property = 'static_mesh_component'
        mesh_property = 'static_mesh'

    sequence = get_asset(sequence_path) if sequence_path else None

    for asset in assets:
        obj = get_asset(asset)
        if obj and obj.get_class().get_name() == class_name:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
                obj, unreal.Vector(0.0, 0.0, 0.0))
            actor.set_actor_label(instance_name)

            component = actor.get_editor_property(component_property)
            mesh = component.get_editor_property(mesh_property)
            import_data = mesh.get_editor_property('asset_import_data')

            transform = _get_transform(import_data, basis, transform)

            actor.set_actor_transform(transform, False, True)

            if class_name == 'SkeletalMesh':
                skm_comp = actor.get_editor_property('skeletal_mesh_component')
                skm_comp.set_bounds_scale(10.0)

            actors.append(actor.get_path_name())

            if sequence:
                binding = next(
                    (
                        p
                        for p in sequence.get_possessables()
                        if p.get_name() == actor.get_name()
                    ),
                    None,
                )
                if not binding:
                    binding = sequence.add_possessable(actor)

                bindings.append(binding.get_id().to_string())

    return {"return": (actors, bindings)}


def apply_animation_to_actor(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            actor_path (str): path to the actor
            animation_path (str): path to the animation
    """
    actor_path, animation_path = get_params(
        params, 'actor_path', 'animation_path')

    actor = get_asset(actor_path)
    animation = get_asset(animation_path)

    animation.set_editor_property('enable_root_motion', True)

    actor.skeletal_mesh_component.set_editor_property(
        'animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    actor.skeletal_mesh_component.animation_data.set_editor_property(
        'anim_to_play', animation)


def apply_animation(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            animation_path (str): path to the animation
            instance_name (str): name of the instance
            sequences (str): list of paths to the sequences
    """
    animation_path, instance_name, sequences = get_params(
        params, 'animation_path', 'instance_name', 'sequences')

    animation = get_asset(animation_path)

    anim_track_class = "MovieSceneSkeletalAnimationTrack"
    anim_section_class = "MovieSceneSkeletalAnimationSection"

    for sequence_path in sequences:
        sequence = get_asset(sequence_path)
        possessables = [
            possessable for possessable in sequence.get_possessables()
            if possessable.get_display_name() == instance_name]

        for possessable in possessables:
            tracks = [
                track for track in possessable.get_tracks()
                if (track.get_class().get_name() == anim_track_class)]

            if not tracks:
                track = possessable.add_track(
                    unreal.MovieSceneSkeletalAnimationTrack)
                tracks.append(track)

            for track in tracks:
                sections = [
                    section for section in track.get_sections()
                    if (section.get_class().get_name == anim_section_class)]

                if not sections:
                    sections.append(track.add_section())

                for section in sections:
                    section.params.set_editor_property('animation', animation)
                    section.set_range(
                        sequence.get_playback_start(),
                        sequence.get_playback_end() - 1)
                    section.set_completion_mode(
                        unreal.MovieSceneCompletionMode.KEEP_STATE)


def add_animation_to_sequencer(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            sequence_path (str): path to the sequence
            binding_guid (str): guid of the binding
            animation_path (str): path to the animation
    """
    sequence_path, binding_guid, animation_path = get_params(
        params, 'sequence_path', 'binding_guid', 'animation_path')

    sequence = get_asset(sequence_path)
    animation = get_asset(animation_path)

    binding = next(
        (
            b
            for b in sequence.get_possessables()
            if b.get_id().to_string() == binding_guid
        ),
        None,
    )
    tracks = binding.get_tracks()
    track = tracks[0] if tracks else binding.add_track(
        unreal.MovieSceneSkeletalAnimationTrack)

    sections = track.get_sections()
    if not sections:
        section = track.add_section()
    else:
        section = sections[0]

        sec_params = section.get_editor_property('params')
        if curr_anim := sec_params.get_editor_property('animation'):
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


def import_camera(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            sequence_path (str): path to the sequence
            import_filename (str): path to the fbx file
    """
    sequence_path, import_filename = get_params(
        params, 'sequence_path', 'import_filename')

    sequence = get_asset(sequence_path)

    world = unreal.EditorLevelLibrary.get_editor_world()

    settings = unreal.MovieSceneUserImportFBXSettings()
    settings.set_editor_property('reduce_keys', False)

    if UNREAL_VERSION.major == 4 and UNREAL_VERSION.minor <= 26:
        unreal.SequencerTools.import_fbx(
            world,
            sequence,
            sequence.get_bindings(),
            settings,
            import_filename
        )
    elif ((UNREAL_VERSION.major == 4 and UNREAL_VERSION.minor >= 27) or
          UNREAL_VERSION.major == 5):
        unreal.SequencerTools.import_level_sequence_fbx(
            world,
            sequence,
            sequence.get_bindings(),
            settings,
            import_filename
        )
    else:
        raise NotImplementedError(
            f"Unreal version {UNREAL_VERSION.major} not supported")


def get_actor_and_skeleton(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            instance_name (str): name of the instance
    """
    instance_name = get_params(params, 'instance_name')

    actor_subsystem = unreal.EditorActorSubsystem()
    actors = actor_subsystem.get_all_level_actors()
    actor = None
    for a in actors:
        if a.get_class().get_name() != "SkeletalMeshActor":
            continue
        if a.get_actor_label() == instance_name:
            actor = a
            break
    if not actor:
        raise RuntimeError(f"Could not find actor {instance_name}")

    skeleton = actor.skeletal_mesh_component.skeletal_mesh.skeleton

    return {"return": (actor.get_path_name(), skeleton.get_path_name())}


def get_skeleton_from_skeletal_mesh(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            skeletal_mesh_path (str): path to the skeletal mesh
    """
    skeletal_mesh_path = get_params(params, 'skeletal_mesh_path')

    skeletal_mesh = unreal.EditorAssetLibrary.load_asset(skeletal_mesh_path)
    skeleton = skeletal_mesh.get_editor_property('skeleton')

    return {"return": skeleton.get_path_name()}


def remove_asset(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            path (str): path to the asset
    """
    path = get_params(params, 'path')

    parent_path = Path(path).parent.as_posix()

    unreal.EditorAssetLibrary.delete_directory(path)

    asset_content = unreal.EditorAssetLibrary.list_assets(
        parent_path, recursive=False, include_folder=True
    )

    if len(asset_content) == 0:
        unreal.EditorAssetLibrary.delete_directory(parent_path)


def delete_all_bound_assets(params):
    """
    Delete from the current level all the assets that are bound to the
    level sequence.

    Args:
        params (str): string containing a dictionary with parameters:
            level_sequence_path (str): path to the level sequence
    """
    level_sequence_path = get_params(params, 'level_sequence_path')

    level_sequence = get_asset(level_sequence_path)

    # Get the actors in the level sequence.
    bound_objs = unreal.SequencerTools.get_bound_objects(
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
    for obj in bound_objs:
        actor_path = obj.bound_objects[0].get_path_name().split(":")[-1]
        actor = unreal.EditorLevelLibrary.get_actor_reference(actor_path)
        unreal.EditorLevelLibrary.destroy_actor(actor)


def remove_camera(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            root (str): path to the root folder
            asset_dir (str): path to the asset folder
    """
    root, asset_dir = get_params(params, 'root', 'asset_dir')

    parent_path = Path(asset_dir).parent.as_posix()

    old_sequence = _get_first_asset_of_class("LevelSequence", asset_dir, False)
    level = _get_first_asset_of_class("World", parent_path, True)

    unreal.EditorLevelLibrary.save_all_dirty_levels()
    unreal.EditorLevelLibrary.load_level(level)

    # There should be only one sequence in the path.
    level_sequence = get_asset(old_sequence)
    sequence_name = level_sequence.get_fname()

    delete_all_bound_assets(level_sequence.get_path_name())

    # Remove the Level Sequence from the parent.
    # We need to traverse the hierarchy from the master sequence to find
    # the level sequence.
    namespace = asset_dir.replace(f"{root}/", "")
    ms_asset = namespace.split('/')[0]
    master_sequence = get_asset(_get_first_asset_of_class(
        "LevelSequence", f"{root}/{ms_asset}", False))

    sequences = [master_sequence]

    parent_sequence = None
    for sequence in sequences:
        tracks = sequence.get_master_tracks()
        # Get the subscene track.
        if subscene_track := next(
            (
                track
                for track in tracks
                if track.get_class().get_name() == "MovieSceneSubTrack"
            ),
            None,
        ):
            sections = subscene_track.get_sections()
            for section in sections:
                if section.get_sequence().get_name() == sequence_name:
                    parent_sequence = sequence
                    subscene_track.remove_section(section)
                    break
                sequences.append(section.get_sequence())
            # Update subscenes indexes.
            for i, section in enumerate(sections):
                section.set_row_index(i)

        if parent_sequence:
            break

    assert parent_sequence, "Could not find the parent sequence"

    unreal.EditorAssetLibrary.delete_asset(level_sequence.get_path_name())

    # Check if there isn't any more assets in the parent folder, and
    # delete it if not.
    asset_content = unreal.EditorAssetLibrary.list_assets(
        parent_path, recursive=False, include_folder=True
    )

    if len(asset_content) == 0:
        unreal.EditorAssetLibrary.delete_directory(parent_path)

    return parent_sequence.get_path_name()


def _remove_subsequences(master_sequence, asset):
    """
    Traverse hierarchy to remove subsequences.

    Args:
        master_sequence (LevelSequence): master sequence
        asset (str): asset name
    """
    sequences = [master_sequence]

    parent = None
    for sequence in sequences:
        tracks = sequence.get_master_tracks()
        subscene_track = None
        visibility_track = None
        for track in tracks:
            if track.get_class().get_name() == "MovieSceneSubTrack":
                subscene_track = track
            if (track.get_class().get_name() ==
                    "MovieSceneLevelVisibilityTrack"):
                visibility_track = track

        if subscene_track:
            sections = subscene_track.get_sections()
            for section in sections:
                if section.get_sequence().get_name() == asset:
                    parent = sequence
                    subscene_track.remove_section(section)
                    break
                sequences.append(section.get_sequence())
            # Update subscenes indexes.
            for i, section in enumerate(sections):
                section.set_row_index(i)

        if visibility_track:
            sections = visibility_track.get_sections()
            for section in sections:
                if (unreal.Name(f"{asset}_map")
                        in section.get_level_names()):
                    visibility_track.remove_section(section)
            # Update visibility sections indexes.
            i = -1
            prev_name = []
            for section in sections:
                if prev_name != section.get_level_names():
                    i += 1
                section.set_row_index(i)
                prev_name = section.get_level_names()

        if parent:
            break

    assert parent, "Could not find the parent sequence"


def _remove_sequences_in_hierarchy(asset_dir, level_sequence, asset, root):
    delete_all_bound_assets(level_sequence.get_path_name())

    # Remove the Level Sequence from the parent.
    # We need to traverse the hierarchy from the master sequence to
    # find the level sequence.
    namespace = asset_dir.replace(f"{root}/", "")
    ms_asset = namespace.split('/')[0]
    master_sequence = get_asset(_get_first_asset_of_class(
        "LevelSequence", f"{root}/{ms_asset}", False))
    master_level = _get_first_asset_of_class(
        "World", f"{root}/{ms_asset}", False)

    _remove_subsequences(master_sequence, asset)

    return master_level


def remove_layout(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            root (str): path to the root folder
            asset (str): path to the asset
            asset_dir (str): path to the asset folder
            asset_name (str): name of the asset
            loaded_assets (str): list of loaded assets
            create_sequences (str): boolean to create sequences
    """
    (root, asset, asset_dir, asset_name, loaded_assets,
     create_sequences) = get_params(params, 'root', 'asset', 'asset_dir',
                                    'asset_name', 'loaded_assets',
                                    'create_sequences')

    path = Path(asset_dir)
    parent_path = path.parent.as_posix()

    level_sequence = get_asset(_get_first_asset_of_class(
        "LevelSequence", path.as_posix(), False))
    level = _get_first_asset_of_class("World", parent_path, True)

    unreal.EditorLevelLibrary.load_level(level)

    containers = ls()
    layout_containers = [
        c for c in containers
        if c.get('asset_name') != asset_name and c.get('family') == "layout"]

    # Check if the assets have been loaded by other layouts, and deletes
    # them if they haven't.
    for loaded_asset in eval(loaded_assets):
        layouts = [
            lc for lc in layout_containers
            if loaded_asset in lc.get('loaded_assets')]

        if not layouts:
            unreal.EditorAssetLibrary.delete_directory(
                Path(loaded_asset).parent.as_posix())

            # Delete the parent folder if there aren't any more
            # layouts in it.
            asset_content = unreal.EditorAssetLibrary.list_assets(
                Path(loaded_asset).parent.parent.as_posix(), recursive=False,
                include_folder=True
            )

            if len(asset_content) == 0:
                unreal.EditorAssetLibrary.delete_directory(
                    str(Path(loaded_asset).parent.parent))

    master_level = None

    if create_sequences:
        master_level = _remove_sequences_in_hierarchy(
            asset_dir, level_sequence, asset, root)

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    if not actors:
        # Delete the level if it's empty.
        # Create a temporary level to delete the layout level.
        unreal.EditorLevelLibrary.save_all_dirty_levels()
        unreal.EditorAssetLibrary.make_directory(f"{root}/tmp")
        tmp_level = f"{root}/tmp/temp_map"
        if not unreal.EditorAssetLibrary.does_asset_exist(
                f"{tmp_level}.temp_map"):
            unreal.EditorLevelLibrary.new_level(tmp_level)
        else:
            unreal.EditorLevelLibrary.load_level(tmp_level)

    # Delete the layout directory.
    unreal.EditorAssetLibrary.delete_directory(path.as_posix())

    if not actors:
        unreal.EditorAssetLibrary.delete_directory(path.parent.as_posix())

    if create_sequences:
        unreal.EditorLevelLibrary.load_level(master_level)
        unreal.EditorAssetLibrary.delete_directory(f"{root}/tmp")


def match_actor(params):
    """
    Match existing actors in the scene to the layout that is being loaded.
    It will create a container for each of them, and apply the transformations
    from the layout.

    Args:
        params (str): string containing a dictionary with parameters:
            actors_matched (list): list of actors already matched
            lasset (dict): dictionary containing the layout asset
            repr_data (dict): dictionary containing the representation
    """
    actors_matched, lasset, repr_data = get_params(
        params, 'actors_matched', 'lasset', 'repr_data')

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    for actor in actors:
        if actor.get_class().get_name() != 'StaticMeshActor':
            continue
        if actor in actors_matched:
            continue

        # Get the original path of the file from which the asset has
        # been imported.
        smc = actor.get_editor_property('static_mesh_component')
        mesh = smc.get_editor_property('static_mesh')
        import_data = mesh.get_editor_property('asset_import_data')
        filename = import_data.get_first_filename()
        path = Path(filename)

        if (not path.name or
                path.name not in repr_data.get('data').get('path')):
            continue

        actor.set_actor_label(lasset.get('instance_name'))

        mesh_path = Path(mesh.get_path_name()).parent.as_posix()

        # Set the transform for the actor.
        basis_data = lasset.get('basis')
        transform_data = lasset.get('transform_matrix')
        transform = _get_transform(import_data, basis_data, transform_data)

        actor.set_actor_transform(transform, False, True)

        return True, mesh_path

    return False, None


def _spawn_actor(obj, lasset):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
        obj, unreal.Vector(0.0, 0.0, 0.0)
    )

    actor.set_actor_label(lasset.get('instance_name'))
    smc = actor.get_editor_property('static_mesh_component')
    mesh = smc.get_editor_property('static_mesh')
    import_data = mesh.get_editor_property('asset_import_data')

    basis_data = lasset.get('basis')
    transform_data = lasset.get('transform_matrix')
    transform = _get_transform(import_data, basis_data, transform_data)

    actor.set_actor_transform(transform, False, True)


def spawn_existing_actors(params):
    """
    Spawn actors that have already been loaded from the layout asset.

    Args:
        params (str): string containing a dictionary with parameters:
            repr_data (dict): dictionary containing the representation
            lasset (dict): dictionary containing the layout asset
    """
    repr_data, lasset = get_params(params, 'repr_data', 'lasset')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    all_containers = ls()

    for container in all_containers:
        representation = container.get('representation')

        if representation != str(repr_data.get('_id')):
            continue

        asset_dir = container.get('namespace')

        _filter = unreal.ARFilter(
            class_names=["StaticMesh"],
            package_paths=[asset_dir],
            recursive_paths=False)
        assets = ar.get_assets(_filter)

        for asset in assets:
            obj = asset.get_asset()
            _spawn_actor(obj, lasset)

        return True

    return False


def spawn_actors(params):
    """
    Spawn actors from a list of assets.

    Args:
        params (str): string containing a dictionary with parameters:
            lasset (dict): dictionary containing the layout asset
            repr_data (dict): dictionary containing the representation
    """
    assets, lasset = get_params(params, 'assets', 'lasset')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    for asset in assets:
        obj = ar.get_asset_by_object_path(asset).get_asset()
        if obj.get_class().get_name() != 'StaticMesh':
            continue
        _spawn_actor(obj, lasset)

    return True


def remove_unmatched_actors(params):
    """
    Remove actors that have not been matched to the layout.

    Args:
        params (str): string containing a dictionary with parameters:
            actors_matched (list): list of actors already matched
    """
    actors_matched = get_params(params, 'actors_matched')

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    for actor in actors:
        if actor.get_class().get_name() != 'StaticMeshActor':
            continue
        if actor not in actors_matched:
            unreal.log_warning(f"Actor {actor.get_name()} not matched.")
            unreal.EditorLevelLibrary.destroy_actor(actor)
