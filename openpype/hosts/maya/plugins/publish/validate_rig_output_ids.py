from collections import defaultdict

from maya import cmds

import pyblish.api

import openpype.hosts.maya.api.action
from openpype.hosts.maya.api.lib import get_id, set_id
from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishValidationError
)


def get_basename(node):
    """Return node short name without namespace"""
    return node.rsplit("|", 1)[-1].rsplit(":", 1)[-1]


class ValidateRigOutputIds(pyblish.api.InstancePlugin):
    """Validate rig output ids.

    Ids must share the same id as similarly named nodes in the scene. This is
    to ensure the id from the model is preserved through animation.

    """
    order = ValidateContentsOrder + 0.05
    label = "Rig Output Ids"
    hosts = ["maya"]
    families = ["rig"]
    actions = [RepairAction,
               openpype.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance, compute=True)
        if invalid:
            raise PublishValidationError("Found nodes with mismatched IDs.")

    @classmethod
    def get_invalid(cls, instance, compute=False):
        invalid_matches = cls.get_invalid_matches(instance, compute=compute)
        return list(invalid_matches.keys())

    @classmethod
    def get_invalid_matches(cls, instance, compute=False):
        invalid = {}

        if compute:
            out_set = cls.get_node(instance)
            if not out_set:
                instance.data["mismatched_output_ids"] = invalid
                return invalid

            instance_nodes = cmds.sets(out_set, query=True, nodesOnly=True)
            instance_nodes = cmds.ls(instance_nodes, long=True)
            for node in instance_nodes:
                shapes = cmds.listRelatives(node, shapes=True, fullPath=True)
                if shapes:
                    instance_nodes.extend(shapes)

            scene_nodes = cmds.ls(type="transform", long=True)
            scene_nodes += cmds.ls(type="mesh", long=True)
            scene_nodes = set(scene_nodes) - set(instance_nodes)

            scene_nodes_by_basename = defaultdict(list)
            for node in scene_nodes:
                basename = get_basename(node)
                scene_nodes_by_basename[basename].append(node)

            for instance_node in instance_nodes:
                basename = get_basename(instance_node)
                if basename not in scene_nodes_by_basename:
                    continue

                matches = scene_nodes_by_basename[basename]

                ids = set(get_id(node) for node in matches)
                ids.add(get_id(instance_node))

                if len(ids) > 1:
                    cls.log.error(
                        "\"{}\" id mismatch to: {}".format(
                            instance_node, matches
                        )
                    )
                    invalid[instance_node] = matches

            instance.data["mismatched_output_ids"] = invalid
        else:
            invalid = instance.data["mismatched_output_ids"]

        return invalid

    @classmethod
    def repair(cls, instance):
        invalid_matches = cls.get_invalid_matches(instance)

        multiple_ids_match = []
        for instance_node, matches in invalid_matches.items():
            ids = set(get_id(node) for node in matches)

            # If there are multiple scene ids matched, and error needs to be
            # raised for manual correction.
            if len(ids) > 1:
                multiple_ids_match.append({"node": instance_node,
                                           "matches": matches})
                continue

            id_to_set = next(iter(ids))
            set_id(instance_node, id_to_set, overwrite=True)

        if multiple_ids_match:
            raise PublishValidationError(
                "Multiple matched ids found. Please repair manually: "
                "{}".format(multiple_ids_match)
            )

    @classmethod
    def get_node(cls, instance):
        """Get target object nodes from out_SET

        Args:
            instance (str): instance

        Returns:
            list: list of object nodes from out_SET
        """
        return instance.data["rig_sets"].get("out_SET")


class ValidateSkeletonRigOutputIds(ValidateRigOutputIds):
    """Validate rig output ids from the skeleton sets.

    Ids must share the same id as similarly named nodes in the scene. This is
    to ensure the id from the model is preserved through animation.

    """
    order = ValidateContentsOrder + 0.05
    label = "Skeleton Rig Output Ids"
    hosts = ["maya"]
    families = ["rig.fbx"]

    @classmethod
    def get_node(cls, instance):
        """Get target object nodes from skeletonMesh_SET

        Args:
            instance (str): instance

        Returns:
            list: list of object nodes from skeletonMesh_SET
        """
        return instance.data["rig_sets"].get("skeletonMesh_SET")
