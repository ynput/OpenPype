# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateHoudiniCommercialLicense(pyblish.api.InstancePlugin):
    """Validate the Houdini instance runs a Commercial license.

    When extracting USD files from a non-commercial Houdini license, even with
    Houdini Indie license, the resulting files will get "scrambled" with
    a license protection and get a special .usdnc or .usdlc suffix.

    This currently breaks the Subset/representation pipeline so we disallow
    any publish with those licenses. Only the commercial license is valid.

    """

    order = pyblish.api.ValidatorOrder
    families = ["usd"]
    hosts = ["houdini"]
    label = "Houdini Commercial License"

    def process(self, instance):

        import hou

        license = hou.licenseCategory()
        if license != hou.licenseCategoryType.Commercial:
            raise PublishValidationError(
                ("USD Publishing requires a full Commercial "
                 "license. You are on: {}").format(license),
                title=self.label)
