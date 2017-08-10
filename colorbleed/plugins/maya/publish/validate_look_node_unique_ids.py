import pprint
from collections import defaultdict

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateLookNodeUniqueIds(pyblish.api.InstancePlugin):
    """Validate look sets have unique colorbleed id attributes

    """

    order = colorbleed.api.ValidatePipelineOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Id Unique Attributes'
    actions = [colorbleed.api.SelectInvalidAction,
               colorbleed.api.RepairAction]

    @classmethod
    def get_invalid(cls, instance):

        invalid = []
        uuids_dict = defaultdict(list)

        relationships = instance.data["lookData"]["relationships"]
        pprint.pprint(relationships)
        for objectset, relationship in relationships.items():
            cls.log.info("Validating lookData for '%s'" % objectset)
            # check if node has UUID and this matches with found node
            for member in relationship["members"]:
                node = member["name"]
                member_uuid = member["uuid"]
                uuid_query = lib.get_id(node)

                if not member_uuid:
                    cls.log.error("No UUID found for '{}'".format(node))
                    invalid.append(node)
                    continue

                if uuid_query != member_uuid:
                    cls.log.error("UUID in lookData does not match with "
                                  "queried UUID of '{}'".format(node))
                    invalid.append(node)
                    continue

                # check if the uuid has already passed through the check
                # if so it means its a duplicate.
                uuids_dict[objectset].append(uuid_query)

        for objectset, member_uuids in uuids_dict.items():
            stored = len(member_uuids)
            unique = len(set(member_uuids))
            if unique != stored:
                rel_members = relationships[objectset]["members"]
                invalid.extend([i["name"] for i in rel_members if
                                i["uuid"] not in unique])

        return invalid

    def process(self, instance):
        """Process all meshes"""

        invalid = self.get_invalid(instance)
        if invalid:
            for item in invalid:
                self.log.error("Invalid node : %s" % item)
            raise RuntimeError("Nodes found without unique "
                               "IDs, see records")
