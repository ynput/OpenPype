# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import  PublishValidationError
from openpype.pipeline.publish import RepairAction
from pymxs import runtime as rt


class ValidateSceneSaved(pyblish.api.InstancePlugin):
    """Validate that workfile was saved."""

    order = pyblish.api.ValidatorOrder
    families = ["workfile"]
    hosts = ["max"]
    label = "Validate Workfile is saved"

    def process(self, instance):
        if not rt.maxFilePath or not rt.maxFileName:
            raise PublishValidationError(
                "Workfile is not saved", title=self.label)
