from collections import defaultdict
import logging
import os

import maya.cmds as cmds

from openpype.client import get_asset_by_id
from openpype.pipeline import (
    legacy_io,
    remove_container,
    registered_host,
)
from openpype.hosts.maya.api import lib, lib_looks

from .alembic import get_alembic_ids_cache, get_alembic_source_ids_cache
from . import arnold_standin

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


def get_selected_nodes():
    """Get information from current selection"""

    selection = cmds.ls(selection=True, long=True)
    hierarchy = lib.get_all_children(selection)
    return list(set(selection + hierarchy))


def get_all_nodes():
    """Get all nodes from the scene.

    Returns:
        list: list of nodes
    """
    return cmds.ls(dag=True, noIntermediate=True, long=True)


def create_asset_id_hash(nodes):
    """Create a hash based on source_id attribute value

    This also implements the hashing for legacy `cbId` attributes.

    Args:
        nodes (list): a list of nodes

    Returns:
        dict
    """
    node_id_hash = defaultdict(list)

    active_project = legacy_io.active_project()
    has_vray = cmds.pluginInfo('vrayformaya', query=True, loaded=True)
    has_mtoa = cmds.pluginInfo('mtoa', query=True, loaded=True)

    def _get_legacy_id_key(id):
        asset_id = id.split(":", 1)[0]
        return (active_project, asset_id)

    for node in nodes:
        # iterate over content of reference node
        if cmds.nodeType(node) == "reference":
            ref_members = list(
                set(cmds.referenceQuery(node, nodes=True, dagPath=True))
            )
            ref_hashes = create_asset_id_hash(ref_members)
            for asset_id, ref_nodes in ref_hashes.items():
                node_id_hash[asset_id] += ref_nodes

        elif has_vray and cmds.nodeType(node) == "VRayProxy":
            path = cmds.getAttr("{}.fileName".format(node))

            source_id_paths = get_alembic_source_ids_cache(path)
            for key in source_id_paths.keys():
                node_id_hash[key] = node

            # legacy `cbId`
            legacy_id_paths = get_alembic_ids_cache(path)
            for _id in legacy_id_paths.keys():
                node_id_hash[_get_legacy_id_key(_id)].append(node)

        elif has_mtoa and cmds.nodeType(node) == "aiStandIn":
            # TODO: For the non alembic support we'll need to add extra
            #   source id into the extracted json next to the published standin

            # legacy `cbId`
            for _id in arnold_standin.get_nodes_by_id(node).keys():
                node_id_hash[_get_legacy_id_key(_id)].append(node)

        else:
            if cmds.attributeQuery("source_id", node=node, exists=True):
                # Get node project + asset from source_id attribute
                source_id = cmds.getAttr("{}.source_id".format(node))
                project_name, asset_id = source_id.split(":", 1)
                node_id_hash[(project_name, asset_id)].append(node)

            else:

                # legacy `cbId`
                value = lib.get_id(node)
                if value is None:
                    continue

                node_id_hash[_get_legacy_id_key(value)].append(node)

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

    for (project_name, asset_id), id_nodes in id_hashes.items():
        asset = get_asset_by_id(project_name, asset_id, fields=["name"])

        # Skip if asset id is not found
        if not asset:
            log.warning("Id not found in the database, skipping '%s'." % _id)
            log.warning("Nodes: %s" % id_nodes)
            continue

        # Collect available look subsets for this asset
        looks = lib_looks.list_looks(asset["_id"])

        # Collect namespaces the asset is found in
        namespaces = set()
        for node in id_nodes:
            namespace = get_namespace_from_node(node)
            namespaces.add(namespace)

        asset_view_items.append({
            "label": asset["name"],
            "asset": asset,
            "looks": looks,
            "namespaces": namespaces,
            "project_name": project_name
        })

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
