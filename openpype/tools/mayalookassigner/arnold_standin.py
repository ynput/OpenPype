import os
import re
from collections import defaultdict
import json
import logging

from maya import cmds

from openpype.pipeline import (
    legacy_io,
    get_representation_path,
    registered_host,
    discover_loader_plugins,
    loaders_from_representation,
    load_container
)
from openpype.client import (
    get_representation_by_name,
    get_last_version_by_subset_name
)
from openpype.hosts.maya.api import lib


log = logging.getLogger(__name__)


ATTRIBUTE_MAPPING = {
    "aiSubdivType": "subdiv_type",
    "aiSubdivIterations": "subdiv_iterations"
}


def get_cbid_by_node(path):
    """Get cbid from Arnold Scene Source.

    Args:
        path (string): Path to Arnold Scene Source.

    Returns:
        (dict): Dictionary with node full name/path and CBID.
    """
    import arnold
    results = {}

    arnold.AiBegin()

    arnold.AiMsgSetConsoleFlags(arnold.AI_LOG_ALL)

    arnold.AiSceneLoad(None, path, None)

    # Iterate over all shader nodes
    iter = arnold.AiUniverseGetNodeIterator(arnold.AI_NODE_SHAPE)
    while not arnold.AiNodeIteratorFinished(iter):
        node = arnold.AiNodeIteratorGetNext(iter)
        if arnold.AiNodeIs(node, "polymesh"):
            node_name = arnold.AiNodeGetName(node)
            try:
                results[arnold.AiNodeGetStr(node, "cbId")].append(node_name)
            except KeyError:
                results[arnold.AiNodeGetStr(node, "cbId")] = [node_name]

    arnold.AiNodeIteratorDestroy(iter)
    arnold.AiEnd()

    return results


def get_standin_path(node):
    path = cmds.getAttr(node + ".dso")

    # Account for frame extension.
    basename = os.path.basename(path)
    current_frame = 1
    pattern = "(#+)"
    matches = re.findall(pattern, basename)
    if matches:
        substring = "%{}d".format(str(len(matches[0])).zfill(2))
        path = path.replace(matches[0], substring)
        path = path % current_frame

    return path


def assign_look(standin, subset):
    log.info("Assigning {} to {}.".format(subset, standin))

    nodes_by_id = get_cbid_by_node(get_standin_path(standin))

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

        # Relationships.
        json_representation = get_representation_by_name(
            project_name, representation_name="json", version_id=version["_id"]
        )

        # Load relationships
        shader_relation = get_representation_path(json_representation)
        with open(shader_relation, "r") as f:
            relationships = json.load(f)

        # Load look.
        # Get representations of shader file and relationships
        look_representation = get_representation_by_name(
            project_name, representation_name="ma", version_id=version["_id"]
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
            loaders = loaders_from_representation(
                all_loaders, representation_id
            )
            loader = next(
                (i for i in loaders if i.__name__ == "LookLoader"), None)
            if loader is None:
                raise RuntimeError("Could not find LookLoader, this is a bug")

            # Reference the look file
            with lib.maintained_selection():
                container_node = load_container(loader, look_representation)

        # Get container members
        shader_nodes = lib.get_container_members(container_node)
        namespace = shader_nodes[0].split(":")[0]

        # Get only the node ids and paths related to this asset
        # And get the shader edits the look supplies
        asset_nodes_by_id = {
            node_id: nodes_by_id[node_id] for node_id in node_ids
        }
        edits = list(
            lib.iter_shader_edits(
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

                inputs = cmds.listConnections(
                    edit["shader"] + ".surfaceShader", source=True)
                if not inputs:
                    log.info(
                        "Shading engine missing material: %s" % edit["shader"]
                    )

                # Strip off component assignments
                for i, node in enumerate(edit["nodes"]):
                    if "." in node:
                        log.warning(
                            ("Converting face assignment to full object "
                             "assignment. This conversion can be lossy: "
                             "{}").format(node))
                        edit["nodes"][i] = node.split(".")[0]

                assignment = "shader='{}'".format(inputs[0])
                for node in edit["nodes"]:
                    node_assignments[node].append(assignment)

            if edit["action"] == "setattr":
                for attr, value in edit["attributes"].items():
                    if attr not in ATTRIBUTE_MAPPING:
                        log.warning(
                            "Skipping setting attribute {} on {} because it is"
                            " not recognized.".format(attr, edit["nodes"])
                        )
                        continue

                    if isinstance(value, str):
                        value = "'{}'".format(value)

                    assignment = "{}={}".format(ATTRIBUTE_MAPPING[attr], value)

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

            with lib.maintained_selection():
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

            cmds.sets(operator, edit=True, addElement=container_node[0])
