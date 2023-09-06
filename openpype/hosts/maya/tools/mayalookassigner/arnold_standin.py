import os
import json
from collections import defaultdict
import logging

from maya import cmds

from openpype.pipeline import legacy_io
from openpype.client import get_last_version_by_subset_name
from openpype.hosts.maya import api
# NOTE hornet update for lib module clash in python 2.7
try:
    import lib
except:
    from . import lib
try:
    from .h_alembic import get_alembic_ids_cache
except:
    from .alembic import get_alembic_ids_cache
# END

log = logging.getLogger(__name__)


ATTRIBUTE_MAPPING = {
    "primaryVisibility": "visibility",  # Camera
    "castsShadows": "visibility",  # Shadow
    "receiveShadows": "receive_shadows",
    "aiSelfShadows": "self_shadows",
    "aiOpaque": "opaque",
    "aiMatte": "matte",
    "aiVisibleInDiffuseTransmission": "visibility",
    "aiVisibleInSpecularTransmission": "visibility",
    "aiVisibleInVolume": "visibility",
    "aiVisibleInDiffuseReflection": "visibility",
    "aiVisibleInSpecularReflection": "visibility",
    "aiSubdivUvSmoothing": "subdiv_uv_smoothing",
    "aiDispHeight": "disp_height",
    "aiDispPadding": "disp_padding",
    "aiDispZeroValue": "disp_zero_value",
    "aiStepSize": "step_size",
    "aiVolumePadding": "volume_padding",
    "aiSubdivType": "subdiv_type",
    "aiSubdivIterations": "subdiv_iterations"
}


def calculate_visibility_mask(attributes):
    # https://arnoldsupport.com/2018/11/21/backdoor-setting-visibility/
    mapping = {
        "primaryVisibility": 1,  # Camera
        "castsShadows": 2,  # Shadow
        "aiVisibleInDiffuseTransmission": 4,
        "aiVisibleInSpecularTransmission": 8,
        "aiVisibleInVolume": 16,
        "aiVisibleInDiffuseReflection": 32,
        "aiVisibleInSpecularReflection": 64
    }
    mask = 255
    for attr, value in mapping.items():
        if attributes.get(attr, True):
            continue

        mask -= value

    return mask


def get_nodes_by_id(standin):
    """Get node id from aiStandIn via json sidecar.

    Args:
        standin (string): aiStandIn node.

    Returns:
        (dict): Dictionary with node full name/path and id.
    """
    path = cmds.getAttr(standin + ".dso")

    if path.endswith(".abc"):
        # Support alembic files directly
        return get_alembic_ids_cache(path)

    json_path = None
    for f in os.listdir(os.path.dirname(path)):
        if f.endswith(".json"):
            json_path = os.path.join(os.path.dirname(path), f)
            break

    if not json_path:
        log.warning("Could not find json file for {}.".format(standin))
        return {}

    with open(json_path, "r") as f:
        return json.load(f)


def shading_engine_assignments(shading_engine, attribute, nodes, assignments):
    """Full assignments with shader or disp_map.

    Args:
        shading_engine (string): Shading engine for material.
        attribute (string): "surfaceShader" or "displacementShader"
        nodes: (list): Nodes paths relative to aiStandIn.
        assignments (dict): Assignments by nodes.
    """
    shader_inputs = cmds.listConnections(
        shading_engine + "." + attribute, source=True
    )
    if not shader_inputs:
        log.info(
            "Shading engine \"{}\" missing input \"{}\"".format(
                shading_engine, attribute
            )
        )
        return

    # Strip off component assignments
    for i, node in enumerate(nodes):
        if "." in node:
            log.warning(
                "Converting face assignment to full object assignment. This "
                "conversion can be lossy: {}".format(node)
            )
            nodes[i] = node.split(".")[0]

    shader_type = "shader" if attribute == "surfaceShader" else "disp_map"
    assignment = "{}='{}'".format(shader_type, shader_inputs[0])
    for node in nodes:
        assignments[node].append(assignment)


def assign_look(standin, subset):
    log.info("Assigning {} to {}.".format(subset, standin))

    nodes_by_id = get_nodes_by_id(standin)

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
            log.info("Didn't find last version for subset name {}".format(
                subset
            ))
            continue

        relationships = lib.get_look_relationships(version["_id"])
        shader_nodes, container_node = lib.load_look(version["_id"])
        namespace = shader_nodes[0].split(":")[0]

        # Get only the node ids and paths related to this asset
        # And get the shader edits the look supplies
        asset_nodes_by_id = {
            node_id: nodes_by_id[node_id] for node_id in node_ids
        }
        edits = list(
            api.lib.iter_shader_edits(
                relationships, shader_nodes, asset_nodes_by_id
            )
        )

        # Create assignments
        node_assignments = {}
        for edit in edits:
            for node in edit["nodes"]:
                if node not in node_assignments:
                    node_assignments[node] = []

            if edit["action"] == "assign":
                if not cmds.ls(edit["shader"], type="shadingEngine"):
                    log.info("Skipping non-shader: %s" % edit["shader"])
                    continue

                shading_engine_assignments(
                    shading_engine=edit["shader"],
                    attribute="surfaceShader",
                    nodes=edit["nodes"],
                    assignments=node_assignments
                )
                shading_engine_assignments(
                    shading_engine=edit["shader"],
                    attribute="displacementShader",
                    nodes=edit["nodes"],
                    assignments=node_assignments
                )

            if edit["action"] == "setattr":
                visibility = False
                for attr, value in edit["attributes"].items():
                    if attr not in ATTRIBUTE_MAPPING:
                        log.warning(
                            "Skipping setting attribute {} on {} because it is"
                            " not recognized.".format(attr, edit["nodes"])
                        )
                        continue

                    if isinstance(value, str):
                        value = "'{}'".format(value)

                    if ATTRIBUTE_MAPPING[attr] == "visibility":
                        visibility = True
                        continue

                    assignment = "{}={}".format(ATTRIBUTE_MAPPING[attr], value)

                    for node in edit["nodes"]:
                        node_assignments[node].append(assignment)

                if visibility:
                    mask = calculate_visibility_mask(edit["attributes"])
                    assignment = "visibility={}".format(mask)

                    for node in edit["nodes"]:
                        node_assignments[node].append(assignment)

        # Assign shader
        # Clear all current shader assignments
        plug = standin + ".operators"
        num = cmds.getAttr(plug, size=True)
        for i in reversed(range(num)):
            cmds.removeMultiInstance("{}[{}]".format(plug, i), b=True)

        # Create new assignment overrides
        index = 0
        for node, assignments in node_assignments.items():
            if not assignments:
                continue

            with api.lib.maintained_selection():
                operator = cmds.createNode("aiSetParameter")
                operator = cmds.rename(operator, namespace + ":" + operator)

            cmds.setAttr(operator + ".selection", node, type="string")
            for i, assignment in enumerate(assignments):
                cmds.setAttr(
                    "{}.assignment[{}]".format(operator, i),
                    assignment,
                    type="string"
                )

                cmds.connectAttr(
                    operator + ".out", "{}[{}]".format(plug, index)
                )

                index += 1

            cmds.sets(operator, edit=True, addElement=container_node)
