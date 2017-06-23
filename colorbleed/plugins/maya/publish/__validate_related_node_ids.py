import pyblish.api
import colorbleed.api

import cbra.utils.maya.node_uuid as id_utils
import cbra.lib


class ValidateRelatedNodeIds(pyblish.api.InstancePlugin):
    """Validate nodes have related colorbleed ids.

    An ID is 'related' if its built in the current Item.

    Note that this doesn't ensure it's from the current Task. An ID created
    from `lookdev` has the same relation to the Item as one coming from others,
    like `rigging` or `modeling`.

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.model']
    hosts = ['maya']
    label = 'Related Id Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.GenerateUUIDsOnInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        """Return the member nodes that are invalid"""

        context = instance.context
        current_file = context.data.get('currentFile', None)
        if not current_file:
            raise RuntimeError("No current file information: "
                               "{0}".format(current_file))

        try:
            context = cbra.lib.parse_context(current_file)
        except RuntimeError, e:
            cls.log.error("Can't generate UUIDs because scene isn't "
                          "in new-style pipeline: ".format(current_file))
            raise e

        def to_item(id):
            """Split the item id part from a node id"""
            return id.rsplit(":", 1)[0]

        # Generate a fake id in the current context to retrieve the item
        # id prefix that should match with ids on the nodes
        fake_node = "__node__"
        ids = id_utils.generate_ids(context, [fake_node])
        id = ids[fake_node]
        item_prefix = to_item(id)

        # Take only the ids with more than one member
        invalid = list()
        invalid_items = set()
        for member in instance:
            member_id = id_utils.get_id(member)

            # skip nodes without ids
            if not member_id:
                continue

            if not member_id.startswith(item_prefix):
                invalid.append(member)
                invalid_items.add(to_item(member_id))

        # Log invalid item ids
        if invalid_items:
            for item_id in sorted(invalid_items):
                cls.log.warning("Found invalid item id: {0}".format(item_id))

        return invalid

    def process(self, instance):
        """Process all meshes"""

        # Ensure all nodes have a cbId
        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Nodes found with non-related "
                               "asset IDs: {0}".format(invalid))
