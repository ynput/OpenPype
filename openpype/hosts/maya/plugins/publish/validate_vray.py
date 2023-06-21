from maya import cmds

import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateVray(pyblish.api.InstancePlugin):
    """Validate general Vray setup."""

    order = pyblish.api.ValidatorOrder
    label = 'VRay'
    hosts = ["maya"]
    families = ["vrayproxy"]

    def process(self, instance):
        # Validate vray plugin is loaded.
        if not cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            raise PublishValidationError("Vray plugin is not loaded.")
