# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateHoudiniNotApprenticeLicense(pyblish.api.InstancePlugin):
    """Validate the Houdini instance runs a non Apprentice license.

    When extracting USD files from an apprentice Houdini license,
    the resulting files will get "scrambled" with a license protection
    and get a special .usdnc or .usdlc suffix.

    This currently breaks the Subset/representation pipeline so we disallow
    any publish with apprentice license.

    """

    order = pyblish.api.ValidatorOrder
    families = ["usd"]
    hosts = ["houdini"]
    label = "Houdini Apprentice License"

    def process(self, instance):

        import hou

        if hou.isApprentice():
            raise PublishValidationError(
                ("USD Publishing requires a non apprentice "
                 "license."),
                title=self.label)
