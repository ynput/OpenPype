import os
import tempfile
import functools
import logging
import re
from enum import Enum


import bpy
from bpy.app.handlers import persistent


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class ModifiersTypes(Enum):
    MESH_SEQUENCE_CACHE = 'MESH_SEQUENCE_CACHE'
    NODES = 'NODES'


class ObjectsTypes(Enum):
    MESH = 'MESH'


class Regex(Enum):
    VERSION = '(v\d{3})'
    VERSION_IN_PATH = r'[^a-zA-Z\d](v\d{3})[^a-zA-Z\d]'


class Folders(Enum):
    ANIMATION = 'animation'
    PUBLISH = 'publish'


SHAPE = 'ShapeDeformed'
SCALE = 0.01


bl_info = {
    "name": "Update paths to last version",
    "description": "Update all concerned paths in scene to automatically target the last version existing",
    "author": "Quad",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "category": "Render",
    "location": "View 3D > UI",
}


class UpdatePathsToAnimation(bpy.types.Operator):
    bl_idname = "paths.update_paths_to_animation"
    bl_label = "Update tasks in scene objects paths"

    def execute(self, context):
        mesh_objects = get_objects_by_type(ObjectsTypes.MESH.value)
        mesh_sequence_caches = get_modifiers_by_type(
            modifier_type=ModifiersTypes.MESH_SEQUENCE_CACHE.value,
            given_objects=mesh_objects
        )
        modifiers_cache_files = [modifier.cache_file for modifier in mesh_sequence_caches]

        create_library_override_for(
            collections=bpy.context.scene.collection,
            objects=mesh_objects,
            modifiers_cache_files=modifiers_cache_files
        )

        update_mesh_sequence_caches(mesh_objects)
        apply_scale(mesh_objects, SCALE)
        disable_uv_data_reading(mesh_sequence_caches)

        return {'FINISHED'}


class UpdateObjectsPathsVersion(bpy.types.Operator):
    bl_idname = "paths.update_objects_paths_version"
    bl_label = "Update versions in scene objects paths"

    def execute(self, context):
        mesh_objects = get_objects_by_type(ObjectsTypes.MESH.value)
        mesh_sequence_caches = get_modifiers_by_type(
            modifier_type=ModifiersTypes.MESH_SEQUENCE_CACHE.value,
            given_objects=mesh_objects
        )
        modifiers_cache_files = [modifier.cache_file for modifier in mesh_sequence_caches]
        create_library_override_for(
            collections=bpy.context.scene.collection,
            objects=mesh_objects,
            modifiers_cache_files=modifiers_cache_files
        )

        update_versions(bpy.data.cache_files)
        disable_uv_data_reading(mesh_sequence_caches)

        return {'FINISHED'}


def get_objects_by_type(object_type):
    return [obj for obj in bpy.data.objects if obj.type == object_type]


def get_modifiers_by_type(modifier_type, given_objects=None):
    retrieved_modifiers = list()
    given_objects = given_objects if given_objects else bpy.data.objects
    for obj in given_objects:
        for modifier in obj.modifiers:
            if modifier.type == modifier_type:
                retrieved_modifiers.append(modifier)
    return retrieved_modifiers


def create_library_override_for(collections=[], objects=[], modifiers_cache_files=[]):
    collections = collections if collections else bpy.context.scene.collection
    objects = objects if objects else bpy.data.objects

    override_collection_and_children(collections)
    override_objects(objects)
    make_local(modifiers_cache_files)


def override_collection_and_children(collection):
    if collection.library:
        collection.override_create(remap_local_usages=True)

    for child in collection.children:
        override_collection_and_children(child)


def override_objects(all_objects):
    local_objects = _get_local_objects_names(all_objects)
    for obj in _get_linked_objects(all_objects):
        if obj.name not in local_objects:
            obj.override_create(remap_local_usages=True)


def make_local(all_objects):
    local_objects = _get_local_objects_names(all_objects)
    for obj in _get_linked_objects(all_objects):
        if obj.name not in local_objects:
            obj.make_local()


def _get_linked_objects(objects):
    return [obj for obj in objects if obj.library]


def _get_local_objects_names(objects):
    return [obj.name for obj in objects if not obj.library]


def update_versions(cache_files):
    for cache_file in cache_files:
        absolute_file_path = bpy.path.abspath(cache_file.filepath)

        if not _is_animation_file(absolute_file_path):
            logging.warning(f'Cache file {cache_file.name} does not point to an animation file. Skipping...')
            continue

        current_version = extract_version_from_filepath(absolute_file_path)
        versions_directory = absolute_file_path.split(current_version)[0]
        last_version_available = retrieve_higher_version_from_directory(versions_directory)
        if current_version == last_version_available:
            log.info(f"No newer version found for alembic {cache_file.name} (current is {current_version})")
            return

        cache_file.filepath = absolute_file_path.replace(current_version, last_version_available)
        cache_file.name = cache_file.filepath.split('\\')[-1]
        log.info(f"Alembic named {cache_file.name} has been updated from version {current_version} to {last_version_available}")


def _is_animation_file(filepath):
    splitted_filepath = filepath.replace('\\', '/').split('/')
    splitted_filepath.index(Folders.PUBLISH.value)+1
    return splitted_filepath[splitted_filepath.index(Folders.PUBLISH.value)+1] == Folders.ANIMATION.value


def extract_version_from_filepath(filepath):
    results = re.search(Regex.VERSION_IN_PATH.value, filepath)
    return results.groups()[-1]


def extract_path_before_version(filepath):
    results = re.split(Regex.VERSION_IN_PATH.value, filepath)
    return results[0]


def retrieve_higher_version_from_directory(directory):
    return [
        folder for folder in os.listdir(directory) if
        re.match(Regex.VERSION.value, folder) and
        os.path.isdir(os.path.join(directory, folder))
    ][-1]


def extract_name_from_alembic_path(alembic_path):
    return alembic_path.split('\\')[-1]


def update_mesh_sequence_caches(objects):
    updated_cache_files = list()
    for blender_object in objects:
        for modifier in get_modifiers_by_type(ModifiersTypes.MESH_SEQUENCE_CACHE.value, [blender_object]):
            cache_file = modifier.cache_file
            if cache_file not in updated_cache_files:
                update_cache_files_data(cache_file, modifier.object_path)
                updated_cache_files.append(cache_file)

            replace_object_path_target(modifier, blender_object.name)


def update_cache_files_data(cache_file, modifier_object_path):
    alembic_path = generate_path_to_new_alembic(modifier_object_path)
    if alembic_path == cache_file.filepath:
        return

    cache_file.filepath = alembic_path
    cache_file_previous_name = cache_file.name
    cache_file.name = extract_name_from_alembic_path(alembic_path)
    log.info(f"Alembic named {cache_file_previous_name} has been updated with filepath {cache_file.filepath}")


def replace_object_path_target(modifier, object_name):
    splitted_path = modifier.object_path.split('/')
    splitted_path[-1] = f"{object_name}{SHAPE}"
    modifier.object_path = '/'.join(splitted_path)


def generate_path_to_new_alembic(modifier_object_path):
    asset_name = extract_asset_name_from_object_path(modifier_object_path)
    animation_directory = generate_animation_directory(asset_name)
    last_version = retrieve_higher_version_from_directory(animation_directory)
    alembic_file = retrieve_alembic_file_from_subset_directory(animation_directory, last_version)
    return os.path.join(
        animation_directory,
        last_version,
        alembic_file
    )


def extract_asset_name_from_object_path(object_path):
    return os.path.normpath(object_path).split(os.path.sep)[1].split('_')[0]


def generate_animation_directory(asset_name):
    return os.path.join(
        _extract_shot_directory_from_path(bpy.data.filepath),
        Folders.PUBLISH.value,
        Folders.ANIMATION.value,
        f'{asset_name}_{Folders.ANIMATION.value}'
    )


def _extract_shot_directory_from_path(given_filepath):
    return '/'.join(os.path.normpath(given_filepath).split(os.path.sep)[:-3])


def retrieve_alembic_file_from_subset_directory(directory, version):
    version_directory = os.path.join(directory, version)
    return next(
        iter(
            alembic_file for alembic_file in os.listdir(version_directory) if
            alembic_file.endswith('.abc') and
            extract_version_from_filepath(os.path.join(version_directory, alembic_file)) == version
        )
    )


def apply_scale(objects, scale):
    for blender_object in objects:
        blender_object.scale = (scale, scale, scale)


def disable_uv_data_reading(mesh_sequence_caches):
    for mesh_sequence_cache in mesh_sequence_caches:
        mesh_sequence_cache.read_data = {'COLOR', 'POLY', 'VERT'}


class SelectObjectTypesToUpdate(bpy.types.Panel):
    bl_idname = "paths.objects_types_selector"
    bl_label = "Select object types to update"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Quad"

    update_alembics = bpy.props.BoolProperty(default=True)
    update_shader_files = bpy.props.BoolProperty(default=True)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("paths.update_paths_to_animation", text="Update alembics to animation", icon="MESH_CUBE")
        col.operator("paths.update_objects_paths_version", text="Update alembics versions", icon="MESH_CUBE")


def register():
        bpy.utils.register_class(SelectObjectTypesToUpdate)
        bpy.utils.register_class(UpdatePathsToAnimation)
        bpy.utils.register_class(UpdateObjectsPathsVersion)


def unregister():
        bpy.utils.unregister_class(SelectObjectTypesToUpdate)
        bpy.utils.unregister_class(UpdatePathsToAnimation)
        bpy.utils.unregister_class(UpdateObjectsPathsVersion)
