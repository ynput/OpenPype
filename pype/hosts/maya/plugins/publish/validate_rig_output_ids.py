import pymel.core as pc

import pyblish.api

import pype.api
import pype.hosts.maya.action
from pype.hosts.maya.lib import undo_chunk


class ValidateRigOutputIds(pyblish.api.InstancePlugin):
    """Validate rig output ids.

    Ids must share the same id as similarly named nodes in the scene. This is
    to ensure the id from the model is preserved through animation.

    """
    order = pype.api.ValidateContentsOrder + 0.05
    label = "Rig Output Ids"
    hosts = ["maya"]
    families = ["rig"]
    actions = [pype.api.RepairAction,
               pype.hosts.maya.action.SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance, compute=True)
        if invalid:
            raise RuntimeError("Found nodes with mismatched IDs.")

    @classmethod
    def get_invalid(cls, instance, compute=False):
        invalid = cls.get_invalid_matches(instance, compute=compute)
        return [x["node"].longName() for x in invalid]

    @classmethod
    def get_invalid_matches(cls, instance, compute=False):
        invalid = []

        if compute:
            out_set = next(x for x in instance if x.endswith("out_SET"))
            instance_nodes = pc.sets(out_set, query=True)
            instance_nodes.extend(
                [x.getShape() for x in instance_nodes if x.getShape()])

            scene_nodes = pc.ls(type="transform") + pc.ls(type="mesh")
            scene_nodes = set(scene_nodes) - set(instance_nodes)

            for instance_node in instance_nodes:
                matches = []
                basename = instance_node.name(stripNamespace=True)
                for scene_node in scene_nodes:
                    if scene_node.name(stripNamespace=True) == basename:
                        matches.append(scene_node)

                if matches:
                    ids = [instance_node.cbId.get()]
                    ids.extend([x.cbId.get() for x in matches])
                    ids = set(ids)

                    if len(ids) > 1:
                        cls.log.error(
                            "\"{}\" id mismatch to: {}".format(
                                instance_node.longName(), matches
                            )
                        )
                        invalid.append(
                            {"node": instance_node, "matches": matches}
                        )

            instance.data["mismatched_output_ids"] = invalid
        else:
            invalid = instance.data["mismatched_output_ids"]

        return invalid

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid_matches(instance)

        multiple_ids_match = []
        for data in invalid:
            ids = [x.cbId.get() for x in data["matches"]]

            # If there are multiple scene ids matched, and error needs to be
            # raised for manual correction.
            if len(ids) > 1:
                multiple_ids_match.append(data)
                continue

            data["node"].cbId.set(ids[0])

        if multiple_ids_match:
            raise RuntimeError(
                "Multiple matched ids found. Please repair manually: "
                "{}".format(multiple_ids_match)
            )
