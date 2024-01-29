# -*- coding: utf-8 -*-
"""Validate model nodes names."""
import re

import pyblish.api
from pymxs import runtime as rt

from openpype.hosts.max.api.action import SelectInvalidAction

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder)


class ValidateModelName(pyblish.api.InstancePlugin,
                        OptionalPyblishPluginMixin):
    """Validate Model Name
    Validation regex is (?P<subset>.*)_(GEO) by default.
    e.g. (subset_name)_GEO should be your model name

    starts with (somename)_GEO

    """
    optional = True
    order = ValidateContentsOrder
    hosts = ["max"]
    families = ["model"]
    label = "Validate Model Name"
    actions = [SelectInvalidAction]
    regex = ""

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        model_names = [model.name for model in instance.data.get("members")]
        cls.log.debug(model_names)
        if not model_names:
            cls.log.error("No Model found in the OP Data.")
            invalid.append(model_names)
        for name in model_names:
            invalid_model_name = cls.get_invalid_model_name(instance, name)
            invalid.extend(invalid_model_name)

        return invalid

    @classmethod
    def get_invalid_model_name(cls, instance, name):
        invalid = []
        regex = cls.regex
        reg = re.compile(regex)
        matched_name = reg.match(name)
        project_name = instance.context.data["projectName"]
        current_asset_name = instance.context.data["asset"]
        if matched_name is None:
            cls.log.error("invalid model name on: {}".format(name))
            cls.log.error("name doesn't match regex {}".format(regex))
            invalid.append((rt.getNodeByName(name),
                            "Model name doesn't match regex"))
        else:
            if "asset" in reg.groupindex:
                if matched_name.group("asset") != current_asset_name:
                    cls.log.error(
                        "Invalid asset name of the model {}.".format(name)
                    )
                    invalid.append((rt.getNodeByName(name),
                                   "Model with invalid asset name"))
            if "subset" in reg.groupindex:
                if matched_name.group("subset") != instance.name:
                    cls.log.error(
                        "Invalid subset name of the model {}.".format(name)
                    )
                    invalid.append((rt.getNodeByName(name),
                                   "Model with invalid subset name"))
            if "project" in reg.groupindex:
                if matched_name.group("project") != project_name:
                    cls.log.error(
                        "Invalid project name of the model {}.".format(name)
                    )
                    invalid.append((rt.getNodeByName(name),
                                   "Model with invalid project name"))
        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            self.log.debug("Skipping Validate Model Name...")
            return

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                "Model naming is invalid. See the log.")
