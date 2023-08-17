from collections import defaultdict

import pyblish.api
from openpype.pipeline.publish import (
    ValidatePipelineOrder,
    PublishValidationError
)
import openpype.hosts.maya.api.action
from openpype.hosts.maya.api import lib


class ValidateNodeIdsUnique(pyblish.api.InstancePlugin):
    """Validate the nodes in the instance have a unique Colorbleed Id

    Here we ensure that what has been added to the instance is unique.

    The validator can allow instanced nodes however a warning will be logged
    due to instanced nodes being unable to have a unique `cbId` attribute.
    The `cbId` attribute is what is used to uniquely define a specific node
    in the scene and is used by the look development system to store and assign
    the shaders per node. For instances this means that they cannot have unique
    shaders assigned, thus a warning is logged if instances are detected.

    """

    order = ValidatePipelineOrder
    label = 'Non Duplicate Instance Members (ID)'
    hosts = ['maya']
    families = ["model",
                "look",
                "rig",
                "yetiRig"]

    actions = [openpype.hosts.maya.api.action.SelectInvalidAction,
               openpype.hosts.maya.api.action.GenerateUUIDsOnInvalidAction]

    allow_instances = True

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)
        if invalid:
            label = "Nodes found with non-unique asset IDs"
            raise PublishValidationError(
                message="{}: {}".format(label, invalid),
                title="Non-unique asset ids on nodes",
                description="{}\n- {}".format(label,
                                              "\n- ".join(sorted(invalid)))
            )

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        # Check only non intermediate shapes
        # todo: must the instance itself ensure to have no intermediates?
        # todo: how come there are intermediates?
        from maya import cmds
        instance_members = cmds.ls(instance, noIntermediate=True, long=True)

        # Collect each id with their members
        ids = defaultdict(list)
        for member in instance_members:
            object_id = lib.get_id(member)
            if not object_id:
                continue
            ids[object_id].append(member)

        # Take only the ids with more than one member
        invalid = list()
        _iteritems = getattr(ids, "iteritems", ids.items)
        for _ids, members in _iteritems():

            if cls.allow_instances:
                unique_members = cls._get_unique_instanced_members(members)
            else:
                unique_members = members

            if len(unique_members) > 1:
                cls.log.error("ID found on multiple nodes: '%s'" % members)
                invalid.extend(members)

        return invalid

    @classmethod
    def _get_unique_instanced_members(cls, members):
        """Filter instanced meshes to only be present once."""

        from maya import cmds

        # Filter to all unique members that are not instances of itself
        # to only invalidate when multiple nodes are found not of the
        # same instance.
        unique_members = []
        processed_instance_paths = set()
        instance_groups = defaultdict(set)
        for member in members:
            all_paths = cmds.ls(member, allPaths=True, long=True)

            # Get all instance paths for this node
            if member in processed_instance_paths:
                instance_groups[tuple(all_paths)].add(member)
                continue

            if len(all_paths) > 1:
                processed_instance_paths.update(all_paths)
                instance_groups[tuple(all_paths)].add(member)
            unique_members.append(member)

        for _instance_grp, instance_members in instance_groups.items():
            if len(instance_members) < 2:
                # Ignore nodes that are instances but their instances
                # don't appear in the export
                continue

            # Log to the user about the usage of instances. They are
            # set to be allowed but can cause issues with lookdev since
            # they cannot have unique shader assignments due to how
            # the `cbId` attribute is shared between the instances
            cls.log.warning("Instanced members detected. This is ok, "
                            "but can introduce issues due to not "
                            "having a unique `cbId` for each node. "
                            "Instanced nodes: "
                            "{}".format(instance_members))

        return unique_members
