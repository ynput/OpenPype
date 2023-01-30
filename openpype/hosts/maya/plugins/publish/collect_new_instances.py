from maya import cmds
import maya.api.OpenMaya as om

import pyblish.api


def get_all_children(nodes):
    """Return all children of `nodes` including each instanced child.
    Using maya.cmds.listRelatives(allDescendents=True) includes only the first
    instance. As such, this function acts as an optimal replacement with a
    focus on a fast query.

    """

    sel = om.MSelectionList()
    traversed = set()
    iterator = om.MItDag(om.MItDag.kDepthFirst)
    for node in nodes:

        if node in traversed:
            # Ignore if already processed as a child
            # before
            continue

        sel.clear()
        sel.add(node)
        dag = sel.getDagPath(0)

        iterator.reset(dag)
        # ignore self
        iterator.next()  # noqa: B305
        while not iterator.isDone():

            path = iterator.fullPathName()

            if path in traversed:
                iterator.prune()
                iterator.next()  # noqa: B305
                continue

            traversed.add(path)
            iterator.next()  # noqa: B305

    return list(traversed)


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
        if not members:
            self.log.warning("Empty instance: \"%s\" " % objset)
        else:
            # Collect members
            members = cmds.ls(members, long=True) or []

            dag_members = cmds.ls(members, type="dagNode", long=True)
            children = get_all_children(dag_members)
            children = cmds.ls(children, noIntermediate=True, long=True)
            parents = []
            if creator_attributes.get("includeParentHierarchy", True):
                # If `includeParentHierarchy` then include the parents
                # so they will also be picked up in the instance by validators
                parents = self.get_all_parents(members)
            members_hierarchy = list(set(members + children + parents))

            instance[:] = members_hierarchy

        # Store the exact members of the object set
        instance.data["setMembers"] = members

        # TODO: This might make more sense as a separate collector
        # Collect frameStartHandle and frameEndHandle if frames present
        if "frameStart" in instance.data:
            handle_start = instance.data.get("handleStart", 0)
            frame_start_handle = instance.data["frameStart"] - handle_start
            instance.data["frameStartHandle"] = frame_start_handle
        if "frameEnd" in instance.data:
            handle_end = instance.data.get("handleEnd", 0)
            frame_end_handle = instance.data["frameEnd"] + handle_end
            instance.data["frameEndHandle"] = frame_end_handle

    def get_all_parents(self, nodes):
        """Get all parents by using string operations (optimization)

        Args:
            nodes (list): the nodes which are found in the objectSet

        Returns:
            list
        """

        parents = []
        for node in nodes:
            splitted = node.split("|")
            items = ["|".join(splitted[0:i]) for i in range(2, len(splitted))]
            parents.extend(items)

        return list(set(parents))
