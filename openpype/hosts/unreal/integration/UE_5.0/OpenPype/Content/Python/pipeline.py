import os
import semver

import unreal

from helpers import (
    get_params,
    cast_map_to_str_dict
)

UNREAL_VERSION = semver.VersionInfo(
    *os.getenv("OPENPYPE_UNREAL_VERSION").split(".")
)


def parse_container(params):
    """To get data from container, AssetContainer must be loaded.

    Args:
        params (str): string containing a dictionary with parameters:
            container (str): path to container
    """
    container = get_params(params, "container")

    asset = unreal.EditorAssetLibrary.load_asset(container)
    data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
    data["objectName"] = asset.get_name()
    data = cast_map_to_str_dict(data)

    return {"return": data}


def imprint(params):
    """Imprint data to container.

    Args:
        params (str): string containing a dictionary with parameters:
            node (str): path to container
            data (dict): data to imprint
    """
    node, data = get_params(params, "node", "data")

    loaded_asset = unreal.EditorAssetLibrary.load_asset(node)
    for key, value in data.items():
        # Support values evaluated at imprint
        if callable(value):
            value = value()
        # Unreal doesn't support NoneType in metadata values
        if value is None:
            value = ""
        unreal.EditorAssetLibrary.set_metadata_tag(
            loaded_asset, key, str(value)
        )

    with unreal.ScopedEditorTransaction("OpenPype containerising"):
        unreal.EditorAssetLibrary.save_asset(node)


def create_folder(params):
    """Create new folder.

    If folder exists, append number at the end and try again, incrementing
    if needed.

    Args:
        params (str): string containing a dictionary with parameters:
            root (str): path root
            name (str): folder name

    Returns:
        str: folder name

    Example:
        >>> create_folder("/Game/Foo")
        /Game/Foo
        >>> create_folder("/Game/Foo")
        /Game/Foo1

    """
    root, name = get_params(params, "root", "name")

    eal = unreal.EditorAssetLibrary
    index = 1
    while True:
        if eal.does_directory_exist(f"{root}/{name}"):
            name = f"{name}{index}"
            index += 1
        else:
            eal.make_directory(f"{root}/{name}")
            break

    return {"return": name}


def project_content_dir():
    """Get project content directory.

    Returns:
        str: path to project content directory

    """
    return {"return": unreal.Paths.project_content_dir()}


def create_container(params):
    """Helper function to create Asset Container class on given path.

    This Asset Class helps to mark given path as Container
    and enable asset version control on it.

    Args:
        params (str): string containing a dictionary with parameters:
            container (str): Asset Container name
            path (str): Path where to create Asset Container. This path should
                point into container folder

    Returns:
        :class:`unreal.Object`: instance of created asset

    Example:

        create_container(
            "/Game/modelingFooCharacter_CON",
            "modelingFooCharacter_CON"
        )

    """
    container, path = get_params(params, "container", "path")

    factory = unreal.AssetContainerFactory()
    tools = unreal.AssetToolsHelpers().get_asset_tools()

    return {"return": tools.create_asset(container, path, None, factory)}


def create_publish_instance(params):
    """Helper function to create OpenPype Publish Instance on given path.

    This behaves similarly as :func:`create_openpype_container`.

    Args:
        params (str): string containing a dictionary with parameters:
            path (str): Path where to create Publish Instance.
                This path should point into container folder
            instance (str): Publish Instance name

    Returns:
        :class:`unreal.Object`: instance of created asset

    Example:

        create_publish_instance(
            "/Game/modelingFooCharacter_INST",
            "modelingFooCharacter_INST"
        )

    """
    instance, path = get_params(params, "instance", "path")

    factory = unreal.OpenPypePublishInstanceFactory()
    tools = unreal.AssetToolsHelpers().get_asset_tools()
    return {"return": tools.create_asset(instance, path, None, factory)}


def ls():
    """List all containers.

    List all found in *Content Manager* of Unreal and return
    metadata from them. Adding `objectName` to set.

    """
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    class_name = [
        "/Script/OpenPype",
        "AssetContainer"
    ] if (
            UNREAL_VERSION.major == 5
            and UNREAL_VERSION.minor > 0
    ) else "AssetContainer"  # noqa
    openpype_containers = ar.get_assets_by_class(class_name, True)

    containers = []

    # get_asset_by_class returns AssetData. To get all metadata we need to
    # load asset. get_tag_values() work only on metadata registered in
    # Asset Registry Project settings (and there is no way to set it with
    # python short of editing ini configuration file).
    for asset_data in openpype_containers:
        asset = asset_data.get_asset()
        data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
        data["objectName"] = asset_data.asset_name
        data = cast_map_to_str_dict(data)

        containers.append(data)

    return {"return": containers}


def ls_inst():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    # UE 5.1 changed how class name is specified
    class_name = [
        "/Script/OpenPype",
        "OpenPypePublishInstance"
    ] if (
            UNREAL_VERSION.major == 5
            and UNREAL_VERSION.minor > 0
    ) else "OpenPypePublishInstance"  # noqa
    openpype_instances = ar.get_assets_by_class(class_name, True)

    instances = []

    # get_asset_by_class returns AssetData. To get all metadata we need to
    # load asset. get_tag_values() work only on metadata registered in
    # Asset Registry Project settings (and there is no way to set it with
    # python short of editing ini configuration file).
    for asset_data in openpype_instances:
        asset = asset_data.get_asset()
        data = unreal.EditorAssetLibrary.get_metadata_tag_values(asset)
        data["objectName"] = asset_data.asset_name
        data = cast_map_to_str_dict(data)

        instances.append(data)

    return {"return": instances}


def containerise(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            root (str): root path of the container
            name (str): name of the container
            data (dict): data of the container
            suffix (str): suffix of the container
    """
    root, name, data, suffix = get_params(
        params, 'root', 'name', 'data', 'suffix')

    suffix = suffix or "_CON"

    container_name = f"{name}{suffix}"

    # Check if container already exists
    if not unreal.EditorAssetLibrary.does_asset_exist(
            f"{root}/{container_name}"):
        create_container(str({
            "container": container_name,
            "path": root}))

    imprint(
        str({"node": f"{root}/{container_name}", "data": data}))

    assets = unreal.EditorAssetLibrary.list_assets(root, True, True)

    for asset in assets:
        unreal.EditorAssetLibrary.save_asset(asset)


def instantiate(params):
    """
    Args:
        params (str): string containing a dictionary with parameters:
            root (str): root path of the instance
            name (str): name of the instance
            data (dict): data of the instance
            assets (list): list of assets to add to the instance
            suffix (str): suffix of the instance
    """
    root, name, data, assets, suffix = get_params(
        params, 'root', 'name', 'data', 'assets', 'suffix')

    suffix = suffix or "_INS"

    instance_name = f"{name}{suffix}"

    pub_instance = create_publish_instance(
        str({"instance": instance_name, "path": root})).get("return")

    unreal.EditorAssetLibrary.save_asset(pub_instance.get_path_name())

    pub_instance.set_editor_property('add_external_assets', True)
    asset_data = pub_instance.get_editor_property('asset_data_external')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    for asset in assets:
        obj = ar.get_asset_by_object_path(asset).get_asset()
        asset_data.add(obj)

    imprint(
        str({"node": f"{root}/{instance_name}", "data": data}))
