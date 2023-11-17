import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)
from pymxs import runtime as rt


class ValidateTyFlowSplinesData(pyblish.api.InstancePlugin,
                                OptionalPyblishPluginMixin):
    """Validate TyFlow Splines data when the export mode is Tycache(Splints)"""

    order = pyblish.api.ValidatorOrder
    families = ["tycache"]
    hosts = ["max"]
    label = "TyFlow Splines Data"

    def process(self, instance):
        pass
