from collections import defaultdict
import logging
import os

from bson.objectid import ObjectId
import maya.cmds as cmds

from avalon import io

from openpype.pipeline import (
    remove_container,
    registered_host,
)
from openpype.hosts.maya.api import lib

from .vray_proxies import get_alembic_ids_cache

log = logging.getLogger(__name__)


def get_workfile():
    path = cmds.file(query=True, sceneName=True) or "untitled"
    return os.path.basename(path)


def get_workfolder():
    return os.path.dirname(cmds.file(query=True, sceneName=True))


def select(nodes):
    cmds.select(nodes)


def get_namespace_from_node(node):
    """Get the namespace from the given node

    Args:
        node (str): name of the node

    Returns:
        namespace (str)

    """
    parts = node.rsplit("|", 1)[-1].rsplit(":", 1)
    return parts[0] if len(parts) > 1 else u":"


def list_descendents(nodes):
    """Include full descendant hierarchy of given nodes.

    This is a workaround to cmds.listRelatives(allDescendents=True) because
    this way correctly keeps children instance paths (see Maya documentation)

    This fixes LKD-26: assignments not working as expected on instanced shapes.

    Return:
        list: List of children descendents of nodes

    """
    result = []
    while True:
        nodes = cmds.listRelatives(nodes,
                                   fullPath=True)
        if nodes:
            result.extend(nodes)
        else:
            return result


def get_selected_nodes():
    """Get information from current selection"""

    selection = cmds.ls(selection=True, long=True)
    hierarchy = list_descendents(selection)
    return list(set(selection + hierarchy))


def get_all_asset_nodes():
    """Get all assets from the scene, container based

    Returns:
        list: list of dictionaries
    """

    host = registered_host()

    nodes = []
    for container in host.ls():
        # We are not interested in looks but assets!
        if container["loader"] == "LookLoader":
            continue

        # Gather all information
        container_name = container["objectName"]
        nodes += lib.get_container_members(container_name)

    nodes = list(set(nodes))
    return nodes


def create_asset_id_hash(nodes):
    """Create a hash based on cbId attribute value
    Args:
        nodes (list): a list of nodes

    Returns:
        dict
    """
    node_id_hash = defaultdict(list)
    for node in nodes:
        # iterate over content of reference node
        if cmds.nodeType(node) == "reference":
            ref_hashes = create_asset_id_hash(
                list(set(cmds.referenceQuery(node, nodes=True, dp=True))))
            for asset_id, ref_nodes in ref_hashes.items():
                node_id_hash[asset_id] += ref_nodes
        elif cmds.pluginInfo('vrayformaya', query=True,
                             loaded=True) and cmds.nodeType(
                node) == "VRayProxy":
            path = cmds.getAttr("{}.fileName".format(node))
            ids = get_alembic_ids_cache(path)
            for k, _ in ids.items():
                pid = k.split(":")[0]
                if node not in node_id_hash[pid]:
                    node_id_hash[pid].append(node)

        else:
            value = lib.get_id(node)
            if value is None:
                continue

            asset_id = value.split(":")[0]
            node_id_hash[asset_id].append(node)

    return dict(node_id_hash)


def create_items_from_nodes(nodes):
    """Create an item for the view based the container and content of it

    It fetches the look document based on the asset ID found in the content.
    The item will contain all important information for the tool to work.

    If there is an asset ID which is not registered in the project's collection
    it will log a warning message.

    Args:
        nodes (list): list of maya nodes

    Returns:
        list of dicts

    """

    asset_view_items = []

    id_hashes = create_asset_id_hash(nodes)

    if not id_hashes:
        log.warning("No id hashes")
        return asset_view_items

    for _id, id_nodes in id_hashes.items():
        asset = io.find_one({"_id": ObjectId(_id)},
                            projection={"name": True})

        # Skip if asset id is not found
        if not asset:
            log.warning("Id not found in the database, skipping '%s'." % _id)
            log.warning("Nodes: %s" % id_nodes)
            continue

        # Collect available look subsets for this asset
        looks = lib.list_looks(asset["_id"])

        # Collect namespaces the asset is found in
        namespaces = set()
        for node in id_nodes:
            namespace = get_namespace_from_node(node)
            namespaces.add(namespace)

        asset_view_items.append({"label": asset["name"],
                                 "asset": asset,
                                 "looks": looks,
                                 "namespaces": namespaces})

    return asset_view_items


def remove_unused_looks():
    """Removes all loaded looks for which none of the shaders are used.

    This will cleanup all loaded "LookLoader" containers that are unused in
    the current scene.

    """

    host = registered_host()

    unused = []
    for container in host.ls():
        if container['loader'] == "LookLoader":
            members = lib.get_container_members(container['objectName'])
            look_sets = cmds.ls(members, type="objectSet")
            for look_set in look_sets:
                # If the set is used than we consider this look *in use*
                if cmds.sets(look_set, query=True):
                    break
            else:
                unused.append(container)

    for container in unused:
        log.info("Removing unused look container: %s", container['objectName'])
        remove_container(container)

    log.info("Finished removing unused looks. (see log for details)")
