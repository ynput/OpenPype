import unreal

from helpers import get_params
from pipeline import UNREAL_VERSION


def log(params):
    """Log message to Unreal Editor.

    Args:
        params (str): string containing a dictionary with parameters:
            message (str): message to log
            level (str): log level, can be "info", "warning" or "error"
    """
    message, level = get_params(params, "message", "level")

    if level == "info":
        unreal.log(message)
    elif level == "warning":
        unreal.log_warning(message)
    elif level == "error":
        unreal.log_error(message)
    else:
        raise ValueError(f"Unknown log level: {level}")


def delete_asset(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_path (str): path to asset to delete
    """
    asset_path = get_params(params, 'asset_path')

    unreal.EditorAssetLibrary.delete_asset(asset_path)


def does_asset_exist(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_path (str): path to asset to check
    """
    asset_path = get_params(params, 'asset_path')

    return {"return": unreal.EditorAssetLibrary.does_asset_exist(asset_path)}


def does_directory_exist(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            directory_path (str): path to directory to check
    """
    directory_path = get_params(params, 'directory_path')

    return {"return": unreal.EditorAssetLibrary.does_directory_exist(
        directory_path)}


def make_directory(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            directory_path (str): path to directory to create
    """
    directory_path = get_params(params, 'directory_path')

    unreal.EditorAssetLibrary.make_directory(directory_path)


def new_level(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            level_path (str): path to level to create
    """
    level_path = get_params(params, 'level_path')

    unreal.EditorLevelLibrary.new_level(level_path)


def load_level(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            level_path (str): path to level to load
    """
    level_path = get_params(params, 'level_path')

    unreal.EditorLevelLibrary.load_level(level_path)


def save_current_level():
    unreal.EditorLevelLibrary.save_current_level()


def save_all_dirty_levels():
    unreal.EditorLevelLibrary.save_all_dirty_levels()


def get_editor_world():
    if UNREAL_VERSION.major == 5:
        world = unreal.UnrealEditorSubsystem().get_editor_world()
    else:
        world = unreal.EditorLevelLibrary.get_editor_world()
    return world.get_path_name()


def get_selected_assets():
    sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()

    return {"return": [obj.get_path_name() for obj in sel_objects]}


def get_selected_actors():
    sel_actors = unreal.EditorUtilityLibrary.get_selected_level_actors()

    return {"return": [actor.get_path_name() for actor in sel_actors]}


def get_system_path(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            asset_path (str): path to asset to get system path for
    """
    asset_path = get_params(params, 'asset_path')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    asset = ar.get_asset_by_object_path(asset_path).get_asset()

    return {"return": unreal.SystemLibrary.get_system_path(asset)}
