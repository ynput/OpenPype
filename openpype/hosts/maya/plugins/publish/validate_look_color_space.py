from maya import cmds

import pyblish.api
from openpype.pipeline.publish import ValidateContentsOrder
from openpype.pipeline import PublishValidationError


class ValidateMayaColorSpace(pyblish.api.InstancePlugin):
    """
        Check if the OCIO Color Management and maketx options
        enabled at the same time
    """

    order = ValidateContentsOrder
    families = ['look']
    hosts = ['maya']
    label = 'Color Management with maketx'

    def process(self, instance):
        ocio_maya = cmds.colorManagementPrefs(q=True,
                                              cmConfigFileEnabled=True,
                                              cmEnabled=True)
        maketx = instance.data["maketx"]

        if ocio_maya and maketx:
            raise PublishValidationError("Maya is color managed and maketx option is on. OpenPype doesn't support this combination yet.") # noqa
