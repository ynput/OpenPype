# -*- coding: utf-8 -*-
import pyblish.api
import hou
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from openpype.pipeline.publish import RepairAction

from openpype.pipeline.publish import RepairAction


class ValidateWorkfilePaths(
        pyblish.api.InstancePlugin, OptionalPyblishPluginMixin):
    """Validate workfile paths so they are absolute."""

    order = pyblish.api.ValidatorOrder
    families = ["workfile"]
    hosts = ["houdini"]
    label = "Validate Workfile Paths"
    actions = [RepairAction]
    optional = True

    node_types = ["file", "alembic"]
    prohibited_vars = ["$HIP", "$JOB"]

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        """Apply project settings to creator"""
        settings = (
            project_settings["houdini"]["publish"]["ValidateWorkfilePaths"]
        )

        cls.node_types = settings.get("node_types", cls.node_types)
        cls.prohibited_vars = settings.get("prohibited_vars", cls.prohibited_vars)

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid()
        self.log.debug(
            "Checking node types: {}".format(", ".join(self.node_types)))
        self.log.debug(
            "Searching prohibited vars: {}".format(
                ", ".join(self.prohibited_vars)
            )
        )

        if invalid:
            all_container_vars = set()
            for param in invalid:
                value = param.unexpandedString()
                contained_vars = [
                    var for var in self.prohibited_vars
                    if var in value
                ]
                all_container_vars.update(contained_vars)

                self.log.error(
                    "Parm {} contains prohibited vars {}: {}".format(
                        param.path(),
                        ", ".join(contained_vars),
                        value)
                )

            message = (
                "Prohibited vars {} found in parameter values".format(
                    ", ".join(all_container_vars)
                )
            )
            raise PublishValidationError(message, title=self.label)

    @classmethod
    def get_invalid(cls):
        invalid = []
        for param, _ in hou.fileReferences():
            # it might return None for some reason
            if not param:
                continue
            # skip nodes we are not interested in
            if param.node().type().name() not in cls.node_types:
                continue

            if any(
                    v for v in cls.prohibited_vars
                    if v in param.unexpandedString()):
                invalid.append(param)

        return invalid

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid()
        for param in invalid:
            cls.log.info("Processing: {}".format(param.path()))
            cls.log.info("Replacing {} for {}".format(
                param.unexpandedString(),
                hou.text.expandString(param.unexpandedString())))
            param.set(hou.text.expandString(param.unexpandedString()))
