import ast

import unreal


def create_unique_asset_name(root, asset, name, version, suffix=""):
    tools = unreal.AssetToolsHelpers().get_asset_tools()
    return tools.create_unique_asset_name(
        f"{root}/{asset}/{name}_v{version:03d}", suffix)


def does_directory_exist(directory_path):
    return unreal.EditorAssetLibrary.does_directory_exist(directory_path)


def make_directory(directory_path):
    unreal.EditorAssetLibrary.make_directory(directory_path)


def import_task(task_properties, options_properties, options_extra_properties):
    task = unreal.AssetImportTask()
    options = unreal.FbxImportUI()

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

    task.options = options

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])


def list_assets(directory_path, recursive, include_folder):
    recursive = ast.literal_eval(recursive)
    include_folder = ast.literal_eval(include_folder)
    return str(unreal.EditorAssetLibrary.list_assets(
        directory_path, recursive, include_folder))


def save_listed_assets(asset_list):
    asset_list = ast.literal_eval(asset_list)
    for asset in asset_list:
        unreal.EditorAssetLibrary.save_asset(asset)
