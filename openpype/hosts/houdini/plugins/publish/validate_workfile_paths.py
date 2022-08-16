# -*- coding: utf-8 -*-
import os
import openpype.api
import pyblish.api
import hou


class ValidateWorkfilePaths(pyblish.api.InstancePlugin):
    """Validate workfile paths so they are absolute."""

    order = pyblish.api.ValidatorOrder
    families = ["workfile"]
    hosts = ["houdini"]
    label = "Validate Workfile Paths"
    actions = [openpype.api.RepairAction]
    optional = True

    node_types = ["file", "alembic"]
    prohibited_vars = ["$HIP", "$JOB"]

    def process(self, instance):
        invalid = self.get_invalid()
        self.log.info(
            "node types to check: {}".format(", ".join(self.node_types)))
        self.log.info(
            "prohibited vars: {}".format(", ".join(self.prohibited_vars))
        )
        if invalid:
            for param in invalid:
                self.log.error("{}: {}".format(
                   param.path(),
                   param.unexpandedString()))

            raise RuntimeError("Invalid paths found")

    @classmethod
    def get_invalid(cls):
        invalid = []
        for param, _ in hou.fileReferences():
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
        """Replace $HIP and $JOB vars for published path."""
        # determine path of published scene
        anatomy = instance.context.data['anatomy']
        template_data = instance.data.get("anatomyData")
        rep = instance.data.get("representations")[0].get("name")
        template_data["representation"] = rep
        template_data["ext"] = rep
        template_data["comment"] = None
        anatomy_filled = anatomy.format(template_data)
        template_filled = anatomy_filled["publish"]["path"]
        filepath = os.path.normpath(template_filled)
        hip_dir = os.path.dirname(filepath)
        invalid = cls.get_invalid()
        for param in invalid:
            cls.log.info("processing: {}".format(param.path()))
            # replace $HIP
            invalid_path = param.unexpandedString()
            param.set(invalid_path.replace("$HIP", hip_dir))
            # replace $JOB
            param.set(invalid_path.replace("$JOB", hip_dir))
            cls.log.info("Replacing {} for {}".format(invalid_path, hip_dir))
