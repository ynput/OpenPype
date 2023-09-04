from maya import cmds

import pyblish.api
from openpype.hosts.maya.api.lib import get_all_children


class CollectNewInstances(pyblish.api.InstancePlugin):
    """Gather members for instances and pre-defined attribute

    This collector takes into account assets that are associated with
    an objectSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"

    Limitations:
        - Does not take into account nodes connected to those
            within an objectSet. Extractors are assumed to export
            with history preserved, but this limits what they will
            be able to achieve and the amount of data available
            to validators. An additional collector could also
            append this input data into the instance, as we do
            for `pype.rig` with collect_history.

    """

    label = "Collect New Instance Data"
    order = pyblish.api.CollectorOrder
    hosts = ["maya"]

    valid_empty_families = {"workfile", "renderlayer"}

    def process(self, instance):

        objset = instance.data.get("instance_node")
        if not objset:
            self.log.debug("Instance has no `instance_node` data")

        # TODO: We might not want to do this in the future
        # Merge creator attributes into instance.data just backwards compatible
        # code still runs as expected
        creator_attributes = instance.data.get("creator_attributes", {})
        if creator_attributes:
            instance.data.update(creator_attributes)

        members = cmds.sets(objset, query=True) or []
        if members:
            # Collect members
            members = cmds.ls(members, long=True) or []

            # Collect full hierarchy
            dag_members = cmds.ls(members, type="dagNode", long=True)
            children = get_all_children(dag_members,
                                        ignore_intermediate_objects=True)

            members_hierarchy = set(members)
            members_hierarchy.update(children)
            if creator_attributes.get("includeParentHierarchy", True):
                members_hierarchy.update(self.get_all_parents(dag_members))

            instance[:] = members_hierarchy

        elif instance.data["family"] not in self.valid_empty_families:
            self.log.warning("Empty instance: \"%s\" " % objset)
        # Store the exact members of the object set
        instance.data["setMembers"] = members

        # TODO: This might make more sense as a separate collector
        # Convert frame values to integers
        for attr_name in (
            "handleStart", "handleEnd", "frameStart", "frameEnd",
        ):
            value = instance.data.get(attr_name)
            if value is not None:
                instance.data[attr_name] = int(value)

        if "frameStart" in instance.data and "frameEnd" in instance.data:
            # Take handles from context if not set locally on the instance
            for key in ["handleStart", "handleEnd"]:
                if key not in instance.data:
                    value = instance.context.data[key]
                    if value is not None:
                        value = int(value)
                    instance.data[key] = value

            # Compute frameStartHandle and frameEndHandle
            instance.data["frameStartHandle"] = int(
                instance.data["frameStart"] - instance.data["handleStart"]
            )
            instance.data["frameEndHandle"] = int(
                instance.data["frameEnd"] + instance.data["handleEnd"]
            )

    def get_all_parents(self, nodes):
        """Get all parents by using string operations (optimization)

        Args:
            nodes (iterable): the nodes which are found in the objectSet

        Returns:
            set
        """

        parents = set()
        for node in nodes:
            splitted = node.split("|")
            items = ["|".join(splitted[0:i]) for i in range(2, len(splitted))]
            parents.update(items)

        return parents
