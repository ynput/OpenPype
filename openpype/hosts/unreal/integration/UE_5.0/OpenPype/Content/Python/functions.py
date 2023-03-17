from pipeline import UNREAL_VERSION

import unreal


def delete_asset(asset_path):
    unreal.EditorAssetLibrary.delete_asset(asset_path)


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


def get_editor_world():
    world = None
    if UNREAL_VERSION.major == 5:
        world = unreal.UnrealEditorSubsystem().get_editor_world()
    else:
        world = unreal.EditorLevelLibrary.get_editor_world()
    return world.get_path_name()


def get_selected_assets():
    sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()

    return [obj.get_path_name() for obj in sel_objects]


def get_selected_actors():
    sel_actors = unreal.EditorUtilityLibrary.get_selected_level_actors()

    return [actor.get_path_name() for actor in sel_actors]


def get_system_path(asset_path):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    asset = ar.get_asset_by_object_path(asset_path).get_asset()

    return unreal.SystemLibrary.get_system_path(asset)
