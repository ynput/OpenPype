from maya import cmds

import pyblish.api
from openpype.pipeline.publish import (
    ValidateContentsOrder, PublishValidationError, RepairAction
)
from openpype.pipeline import discover_legacy_creator_plugins
from openpype.hosts.maya.api.lib import imprint


class ValidateInstanceAttributes(pyblish.api.InstancePlugin):
    """Validate Instance Attributes.

    New attributes can be introduced as new features come in. Old instances
    will need to be updated with these attributes for the documentation to make
    sense, and users do not have to recreate the instances.
    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["*"]
    label = "Instance Attributes"
    plugins_by_family = {
        p.family: p for p in discover_legacy_creator_plugins()
    }
    actions = [RepairAction]

    @classmethod
    def get_missing_attributes(self, instance):
        plugin = self.plugins_by_family[instance.data["family"]]
        subset = instance.data["subset"]
        asset = instance.data["asset"]
        objset = instance.data["objset"]

        missing_attributes = {}
        for key, value in plugin(subset, asset).data.items():
            if not cmds.objExists("{}.{}".format(objset, key)):
                missing_attributes[key] = value

        return missing_attributes

    def process(self, instance):
        objset = instance.data.get("objset")
        if objset is None:
            self.log.debug(
                "Skipping {} because no objectset found.".format(instance)
            )
            return

        missing_attributes = self.get_missing_attributes(instance)
        if missing_attributes:
            raise PublishValidationError(
                "Missing attributes on {}:\n{}".format(
                    objset, missing_attributes
                )
            )

    @classmethod
    def repair(cls, instance):
        imprint(instance.data["objset"], cls.get_missing_attributes(instance))
