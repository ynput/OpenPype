# -*- coding: utf-8 -*-
"""Validate content of animation family."""
import pyblish.api
from pyblish.api import Instance
import openpype.api
import openpype.hosts.maya.api.action
from openpype.pipeline import PublishXmlValidationError


class ValidateAnimationContent(pyblish.api.InstancePlugin):
    """Adheres to the content of 'animation' family

    - Must have collected `out_hierarchy` data.
    - All nodes in `out_hierarchy` must be in the instance.

    """

    order = openpype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["animation"]
    label = "Animation Content"
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        # type: (Instance) -> list
        out_set = next((i for i in instance.data["setMembers"] if
                        i.endswith("out_SET")), None)

        if not out_set:
            raise PublishXmlValidationError(
                "Invalid animation instance structure", cls,
                key="missing_out_set",
                formatting_data={"instance": instance.name})

        if 'out_hierarchy' not in instance.data:
            raise PublishXmlValidationError(
                "Missing collected data", cls,
                key="out_hierarchy_not_collected",
                formatting_data={"instance": instance.name})

        # All nodes in the `out_hierarchy` must be among the nodes that are
        # in the instance. The nodes in the instance are found from the top
        # group, as such this tests whether all nodes are under that top group.

        lookup = set(instance[:])
        invalid = [node for node in instance.data['out_hierarchy'] if
                   node not in lookup]

        return invalid

    def process(self, instance):
        # type: (Instance) -> None
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishXmlValidationError(
                "Invalid animation content", self,
                formatting_data={"nodes": ", ".join(invalid)})
