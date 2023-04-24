import json
import logging

from openpype.pipeline import (
    legacy_io,
    get_representation_path,
    registered_host,
    discover_loader_plugins,
    loaders_from_representation,
    load_container
)
from openpype.client import get_representation_by_name
from openpype.hosts.maya.api import lib


log = logging.getLogger(__name__)


def get_look_relationships(version_id):
    # type: (str) -> dict
    """Get relations for the look.

    Args:
        version_id (str): Parent version Id.

    Returns:
        dict: Dictionary of relations.
    """

    project_name = legacy_io.active_project()
    json_representation = get_representation_by_name(
        project_name, representation_name="json", version_id=version_id
    )

    # Load relationships
    shader_relation = get_representation_path(json_representation)
    with open(shader_relation, "r") as f:
        relationships = json.load(f)

    return relationships


def load_look(version_id):
    # type: (str) -> list
    """Load look from version.

    Get look from version and invoke Loader for it.

    Args:
        version_id (str): Version ID

    Returns:
        list of shader nodes.

    """

    project_name = legacy_io.active_project()
    # Get representations of shader file and relationships
    look_representation = get_representation_by_name(
        project_name, representation_name="ma", version_id=version_id
    )

    # See if representation is already loaded, if so reuse it.
    host = registered_host()
    representation_id = str(look_representation['_id'])
    for container in host.ls():
        if (container['loader'] == "LookLoader" and
                container['representation'] == representation_id):
            log.info("Reusing loaded look ...")
            container_node = container['objectName']
            break
    else:
        log.info("Using look for the first time ...")

        # Load file
        all_loaders = discover_loader_plugins()
        loaders = loaders_from_representation(all_loaders, representation_id)
        loader = next(
            (i for i in loaders if i.__name__ == "LookLoader"), None)
        if loader is None:
            raise RuntimeError("Could not find LookLoader, this is a bug")

        # Reference the look file
        with lib.maintained_selection():
            container_node = load_container(loader, look_representation)[0]

    return lib.get_container_members(container_node), container_node
