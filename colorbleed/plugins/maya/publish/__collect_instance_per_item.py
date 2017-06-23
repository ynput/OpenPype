from collections import defaultdict

from maya import cmds

import cbra.utils.maya.node_uuid as node_uuid
import cbra.lib

import pyblish.api


class CollectInstancePerItem(pyblish.api.ContextPlugin):
    """Collect instances from the Maya scene and breaks them down per item id

    An instance is identified by having an _INST suffix
    and a .family user-defined attribute.

    All other user-defined attributes of the object set
    is accessible within each instance's data.

    This collector breaks the instances down to each Item member it contains, 
    by using the IDs on the nodes in the instance it will split up the instance
    into separate instances for each unique "item" id it finds.
    
    Note:
        - Only breaks down based on children members and ignores parent members.
        - Discards members without IDs.

    """

    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["maya"]
    label = "Instance per Item"

    _include_families = ["colorbleed.look"]

    def process(self, context):

        invalid = list()

        for objset in cmds.ls("*_SET",
                              objectsOnly=True,
                              type='objectSet',
                              long=True,
                              recursive=True):  # Include namespace

            try:
                family = cmds.getAttr("{}.family".format(objset))
            except ValueError:
                self.log.error("Found: %s found, but no family." % objset)
                continue

            if family not in self._include_families:
                continue

            # ignore referenced sets
            if cmds.referenceQuery(objset, isNodeReferenced=True):
                continue

            instances = self.build_instances(context, objset)
            if not instances:

                # Log special error messages when objectSet is completely
                # empty (has no members) to clarify to artists the root of
                # their problem.
                if not cmds.sets(objset, query=True):
                    self.log.error("Instance objectSet has no members: "
                                   "{}".format(objset))

                self.log.error("No instances retrieved from objectSet: "
                               "{}".format(objset))
                invalid.append(objset)

        if invalid:
            raise RuntimeError("Invalid instances: {}".format(invalid))

        # Sort context based on family
        context[:] = sorted(
            context, key=lambda instance: instance.data("family"))

    def build_instances(self, context, objset):
        """Build the instances for a single instance objectSet
        
        Returns:
            list: The constructed instances from the objectSet.
            
        """

        self.log.info("Collecting: %s" % objset)

        short_name = objset.rsplit("|", 1)[-1].rsplit(":", 1)[-1]

        # Default data
        default_data = {"name": short_name[:-5],
                        "subset": "default"}

        # Get user data from user defined attributes
        user_data = dict()
        for attr in cmds.listAttr(objset, userDefined=True):
            try:
                value = cmds.getAttr("{}.{}".format(objset, attr))
                user_data[attr] = value
            except RuntimeError:
                continue

        # Maintain nested object sets
        members = cmds.sets(objset, query=True)
        members = cmds.ls(members, long=True)

        children = cmds.listRelatives(members,
                                      allDescendents=True,
                                      fullPath=True) or []

        # Exclude intermediate objects
        children = cmds.ls(children, noIntermediate=True, long=True)

        nodes = members + children
        nodes = list(set(nodes))

        # Group nodes using ids to an Item
        nodes_id = node_uuid.build_cache(nodes, include_without_ids=True)

        # Log warning for nodes without ids
        if None in nodes_id:
            self.log.warning("Skipping nodes without ids: "
                             "{}".format(nodes_id[None]))

        # ignore nodes without ids
        context.data["instancePerItemNodesWithoutId"] = nodes_id.pop(None,
                                                                     None)

        item_groups = defaultdict(list)

        for id, nodes in nodes_id.iteritems():
            item_id = id.rsplit(":", 1)[0]
            item_groups[item_id].extend(nodes)

        instances = list()
        for item_id, item_nodes in item_groups.iteritems():

            ctx = node_uuid.parse_id("{}:fake_node_uuid".format(item_id))

            # Use itemPath to parse full blown context using official lib
            ctx = cbra.lib.parse_context(ctx['itemPath'])

            item = ctx.get('item', None)
            if item is None:
                self.log.info("Unparsed item id: {}".format(item_id))
                self.log.error("Item can't be parsed and seems to be "
                               "non-existent. Was an asset renamed? Or your"
                               "project set incorrectly?")
                raise RuntimeError("Item not parsed. See log for description.")

            instance = context.create_instance(objset)

            # Set the related members
            instance[:] = item_nodes
            instance.data['setMembers'] = item_nodes

            # Set defaults and user data
            instance.data.update(default_data.copy())
            instance.data.update(user_data.copy())

            # Override the label to be clear
            name = instance.data['name']
            instance.data['label'] = "{0} ({1})".format(name, item)

            # Store that the instance is collected per item
            instance.data['_instancePerItem'] = True
            instance.data['_itemContext'] = ctx

            assert "family" in instance.data, "No family data in instance"
            assert "name" in instance.data, ("No objectSet name data "
                                             "in instance")

            instances.append(instance)

        return instances
