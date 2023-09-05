import pyblish.api
from maya import cmds

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
)


class ValidateVray(pyblish.api.InstancePlugin, OptionalPyblishPluginMixin):
    """Validate general Vray setup."""

    order = pyblish.api.ValidatorOrder
    label = 'VRay'
    hosts = ["maya"]
    families = ["vrayproxy"]

    def process(self, instance):
        # Validate vray plugin is loaded.
        if not cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            raise PublishValidationError("Vray plugin is not loaded.")
