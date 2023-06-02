# -*- coding: utf-8 -*-
"""Tools for loading looks to vray proxies."""
from collections import defaultdict
import logging

from maya import cmds

from openpype.client import get_last_version_by_subset_name
from openpype.pipeline import legacy_io
import openpype.hosts.maya.lib as maya_lib
from . import lib
from .alembic import get_alembic_ids_cache


log = logging.getLogger(__name__)


def assign_vrayproxy_shaders(vrayproxy, assignments):
    # type: (str, dict) -> None
    """Assign shaders to content of Vray Proxy.

    This will create shader overrides on Vray Proxy to assign shaders to its
    content.

    Todo:
        Allow to optimize and assign a single shader to multiple shapes at
        once or maybe even set it to the highest available path?

    Args:
        vrayproxy (str): Name of Vray Proxy
        assignments (dict): Mapping of shader assignments.

    Returns:
        None

    """
    # Clear all current shader assignments
    plug = vrayproxy + ".shaders"
    num = cmds.getAttr(plug, size=True)
    for i in reversed(range(num)):
        cmds.removeMultiInstance("{}[{}]".format(plug, i), b=True)

    # Create new assignment overrides
    index = 0
    for material, paths in assignments.items():
        for path in paths:
            plug = "{}.shaders[{}]".format(vrayproxy, index)
            cmds.setAttr(plug + ".shadersNames", path, type="string")
            cmds.connectAttr(material + ".outColor",
                             plug + ".shadersConnections", force=True)
            index += 1


def vrayproxy_assign_look(vrayproxy, subset="lookDefault"):
    # type: (str, str) -> None
    """Assign look to vray proxy.

    Args:
        vrayproxy (str): Name of vrayproxy to apply look to.
        subset (str): Name of look subset.

    Returns:
        None

    """
    path = cmds.getAttr(vrayproxy + ".fileName")

    nodes_by_id = get_alembic_ids_cache(path)
    if not nodes_by_id:
        log.warning("Alembic file has no cbId attributes: %s" % path)
        return

    # Group by asset id so we run over the look per asset
    node_ids_by_asset_id = defaultdict(set)
    for node_id in nodes_by_id:
        asset_id = node_id.split(":", 1)[0]
        node_ids_by_asset_id[asset_id].add(node_id)

    project_name = legacy_io.active_project()
    for asset_id, node_ids in node_ids_by_asset_id.items():

        # Get latest look version
        version = get_last_version_by_subset_name(
            project_name,
            subset_name=subset,
            asset_id=asset_id,
            fields=["_id"]
        )
        if not version:
            print("Didn't find last version for subset name {}".format(
                subset
            ))
            continue

        relationships = lib.get_look_relationships(version["_id"])
        shadernodes, _ = lib.load_look(version["_id"])

        # Get only the node ids and paths related to this asset
        # And get the shader edits the look supplies
        asset_nodes_by_id = {
            node_id: nodes_by_id[node_id] for node_id in node_ids
        }
        edits = list(
            maya_lib.iter_shader_edits(
                relationships, shadernodes, asset_nodes_by_id
            )
        )

        # Create assignments
        assignments = {}
        for edit in edits:
            if edit["action"] == "assign":
                nodes = edit["nodes"]
                shader = edit["shader"]
                if not cmds.ls(shader, type="shadingEngine"):
                    print("Skipping non-shader: %s" % shader)
                    continue

                inputs = cmds.listConnections(
                    shader + ".surfaceShader", source=True)
                if not inputs:
                    print("Shading engine missing material: %s" % shader)

                # Strip off component assignments
                for i, node in enumerate(nodes):
                    if "." in node:
                        log.warning(
                            ("Converting face assignment to full object "
                             "assignment. This conversion can be lossy: "
                             "{}").format(node))
                        nodes[i] = node.split(".")[0]

                material = inputs[0]
                assignments[material] = nodes

        assign_vrayproxy_shaders(vrayproxy, assignments)
