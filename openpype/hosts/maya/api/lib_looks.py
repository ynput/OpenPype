import json
import logging
from collections import defaultdict
from maya import cmds

from openpype.client import (
    get_subsets,
    get_representation_by_name,
    get_last_versions
)
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    get_container_members,
    get_id,
    apply_attributes
)
from openpype.pipeline import (
    legacy_io,
    registered_host,
    discover_loader_plugins,
    loaders_from_representation,
    load_container,
    get_representation_path
)

log = logging.getLogger(__name__)


def list_looks(asset_id, project_name=None):
    """Return all look subsets for the given asset

    This assumes all look subsets start with "look*" in their names.
    """
    if project_name is None:
        project_name = legacy_io.active_project()

    # # get all subsets with look leading in
    # the name associated with the asset
    # TODO this should probably look for family 'look' instead of checking
    #   subset name that can not start with family
    subset_docs = get_subsets(project_name, asset_ids=[asset_id])
    return [
        subset_doc
        for subset_doc in subset_docs
        if subset_doc["name"].startswith("look")
    ]


def assign_look_by_version(nodes, version_id, project_name=None):
    """Assign nodes a specific published look version by id.

    This assumes the nodes correspond with the asset.

    Args:
        nodes(list): nodes to assign look to
        version_id (bson.ObjectId): database id of the version
        project_name (str): project name for the project where the version id
            should exist.

    Returns:
        None
    """

    if project_name is None:
        project_name = legacy_io.active_project()

    # Get representations of shader file and relationships
    look_representation = get_representation_by_name(
        project_name, "ma", version_id
    )
    json_representation = get_representation_by_name(
        project_name, "json", version_id
    )

    # See if representation is already loaded, if so reuse it.
    host = registered_host()
    representation_id = str(look_representation['_id'])
    for container in host.ls():
        if (container['loader'] == "LookLoader" and
                container['representation'] == representation_id):
            log.info("Reusing loaded look ..")
            container_node = container['objectName']
            break
    else:
        log.info("Using look for the first time ..")

        # Load file
        _loaders = discover_loader_plugins()
        loaders = loaders_from_representation(_loaders, representation_id)
        Loader = next((i for i in loaders if i.__name__ == "LookLoader"), None)
        if Loader is None:
            raise RuntimeError("Could not find LookLoader, this is a bug")

        # Reference the look file
        with maintained_selection():
            container_node = load_container(Loader, look_representation)

    # Get container members
    shader_nodes = get_container_members(container_node)

    # Load relationships
    shader_relation = get_representation_path(json_representation)
    with open(shader_relation, "r") as f:
        relationships = json.load(f)

    # Assign relationships
    apply_shaders(relationships, shader_nodes, nodes)


def _assign_looks(asset_id_nodes, subset_name, project_name):

    asset_ids = list(asset_id_nodes.keys())
    subset_docs = get_subsets(
        project_name, subset_names=[subset_name], asset_ids=asset_ids
    )
    subset_docs_by_asset_id = {
        str(subset_doc["parent"]): subset_doc
        for subset_doc in subset_docs
    }
    subset_ids = {
        subset_doc["_id"]
        for subset_doc in subset_docs_by_asset_id.values()
    }
    last_version_docs = get_last_versions(
        project_name,
        subset_ids=subset_ids,
        fields=["_id", "name", "data.families"]
    )
    last_version_docs_by_subset_id = {
        last_version_doc["parent"]: last_version_doc
        for last_version_doc in last_version_docs
    }

    for asset_id, asset_nodes in asset_id_nodes.items():
        # create objectId for database
        subset_doc = subset_docs_by_asset_id.get(asset_id)
        if not subset_doc:
            log.warning("No subset '{}' found for {}".format(subset_name,
                                                             asset_id))
            continue

        last_version = last_version_docs_by_subset_id.get(subset_doc["_id"])
        if not last_version:
            log.warning((
                "Not found last version for subset '{}' on asset with id {}"
            ).format(subset_name, asset_id))
            continue

        families = last_version.get("data", {}).get("families") or []
        if "look" not in families:
            log.warning((
                "Last version for subset '{}' on asset with id {}"
                " does not have look family"
            ).format(subset_name, asset_id))
            continue

        log.debug("Assigning look '{}' <v{:03d}>".format(
            subset_name, last_version["name"]))

        assign_look_by_version(asset_nodes,
                               last_version["_id"],
                               project_name=project_name)


def assign_look(nodes, subset="lookDefault"):
    """Assigns a look to a node.

    Optimizes the nodes by grouping by asset id and finding
    related subset by name.

    Args:
        nodes (list): all nodes to assign the look to
        subset (str): name of the subset to find
    """
    active_project_name = legacy_io.active_project()

    # Group all nodes by project and asset id to optimize the queries
    # for the look assignments itself
    project_asset_id_nodes = defaultdict(lambda: defaultdict(list))
    fallback_nodes = []
    for node in nodes:
        if cmds.attributeQuery("source_id", node=node, exists=True):
            # Get node project + asset from source_id attribute
            source_id = cmds.getAttr("{}.source_id".format(node))
            project_name, asset_id = source_id.split(":", 1)
            project_asset_id_nodes[project_name][asset_id].append(node)

        else:
            # Group all nodes per asset id (backwards compatible: cbId)
            pype_id = get_id(node)
            if not pype_id:
                continue

            parts = pype_id.split(":", 1)
            asset_id, node_id = parts
            project_asset_id_nodes[active_project_name][asset_id].append(node)
            fallback_nodes.append(node)

    if fallback_nodes:
        log.debug("Falling back to legacy `cbId` look assignment due to "
                  "missing `source_id` attribute for nodes: {}".format(nodes))

    for project_name, asset_id_nodes in project_asset_id_nodes.items():
        _assign_looks(asset_id_nodes=asset_id_nodes,
                      subset_name=subset,
                      project_name=project_name)


def apply_shaders(relationships, shadernodes, nodes):
    """Link shadingEngine to the right nodes based on relationship data

    Relationship data is constructed of a collection of `sets` and `attributes`
    `sets` corresponds with the shaderEngines found in the lookdev.
    Each set has the keys `name`, `members` and `uuid`, the `members`
    hold a collection of node information `name` and `uuid`.

    Args:
        relationships (dict): relationship data
        shadernodes (list): list of nodes of the shading objectSets (includes
            VRayObjectProperties and shadingEngines)
        nodes (list): list of nodes to apply shader to

    Returns:
        None
    """

    attributes = relationships.get("attributes", [])
    shader_data = relationships.get("relationships", {})

    shading_engines = cmds.ls(shadernodes, type="objectSet", long=True)
    assert shading_engines, "Error in retrieving objectSets from reference"

    # region compute lookup
    nodes_by_id = defaultdict(list)
    for node in nodes:
        nodes_by_id[get_id(node)].append(node)

    shading_engines_by_id = defaultdict(list)
    for shad in shading_engines:
        shading_engines_by_id[get_id(shad)].append(shad)
    # endregion

    # region assign shading engines and other sets
    for data in shader_data.values():
        # collect all unique IDs of the set members
        shader_uuid = data["uuid"]
        member_uuids = [member["uuid"] for member in data["members"]]

        filtered_nodes = list()
        for m_uuid in member_uuids:
            filtered_nodes.extend(nodes_by_id[m_uuid])

        id_shading_engines = shading_engines_by_id[shader_uuid]
        if not id_shading_engines:
            log.error("No shader found with cbId "
                      "'{}'".format(shader_uuid))
            continue
        elif len(id_shading_engines) > 1:
            log.error("Skipping shader assignment. "
                      "More than one shader found with cbId "
                      "'{}'. (found: {})".format(shader_uuid,
                                                 id_shading_engines))
            continue

        if not filtered_nodes:
            log.warning("No nodes found for shading engine "
                        "'{0}'".format(id_shading_engines[0]))
            continue
        try:
            cmds.sets(filtered_nodes, forceElement=id_shading_engines[0])
        except RuntimeError as rte:
            log.error("Error during shader assignment: {}".format(rte))

    # endregion

    apply_attributes(attributes, nodes_by_id)


def iter_shader_edits(relationships, shader_nodes, nodes_by_id, label=None):
    """Yield edits as a set of actions."""

    attributes = relationships.get("attributes", [])
    shader_data = relationships.get("relationships", {})

    shading_engines = cmds.ls(shader_nodes, type="objectSet", long=True)
    assert shading_engines, "Error in retrieving objectSets from reference"

    # region compute lookup
    shading_engines_by_id = defaultdict(list)
    for shad in shading_engines:
        shading_engines_by_id[get_id(shad)].append(shad)
    # endregion

    # region assign shading engines and other sets
    for data in shader_data.values():
        # collect all unique IDs of the set members
        shader_uuid = data["uuid"]
        member_uuids = [
            (member["uuid"], member.get("components"))
            for member in data["members"]]

        filtered_nodes = list()
        for _uuid, components in member_uuids:
            nodes = nodes_by_id.get(_uuid, None)
            if nodes is None:
                continue

            if components:
                # Assign to the components
                nodes = [".".join([node, components]) for node in nodes]

            filtered_nodes.extend(nodes)

        id_shading_engines = shading_engines_by_id[shader_uuid]
        if not id_shading_engines:
            log.error("{} - No shader found with cbId "
                      "'{}'".format(label, shader_uuid))
            continue
        elif len(id_shading_engines) > 1:
            log.error("{} - Skipping shader assignment. "
                      "More than one shader found with cbId "
                      "'{}'. (found: {})".format(label, shader_uuid,
                                                 id_shading_engines))
            continue

        if not filtered_nodes:
            log.warning("{} - No nodes found for shading engine "
                        "'{}'".format(label, id_shading_engines[0]))
            continue

        yield {"action": "assign",
               "uuid": data["uuid"],
               "nodes": filtered_nodes,
               "shader": id_shading_engines[0]}

    for data in attributes:
        nodes = nodes_by_id.get(data["uuid"], [])
        attr_value = data["attributes"]
        yield {"action": "setattr",
               "uuid": data["uuid"],
               "nodes": nodes,
               "attributes": attr_value}


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
    # type: (str) -> tuple
    """Load look from version.

    Get look from version and invoke Loader for it.

    Args:
        version_id (str): Version ID

    Returns:
        tuple: 2-tuple of (look members, look container node)

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
        with maintained_selection():
            container_node = load_container(loader, look_representation)[0]

    return get_container_members(container_node), container_node