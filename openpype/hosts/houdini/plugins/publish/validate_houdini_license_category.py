# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
import hou


class ValidateHoudiniNotApprenticeLicense(pyblish.api.InstancePlugin):
    """Validate the Houdini instance runs a non Apprentice license.

    When extracting USD files from an apprentice Houdini license,
    the resulting files will get "scrambled" with a license protection
    and get a special .usdnc suffix.

    This currently breaks the Subset/representation pipeline so we disallow
    any publish with apprentice license.

    """

    order = pyblish.api.ValidatorOrder
    families = ["usd", "abc"]
    hosts = ["houdini"]
    label = "Houdini Apprentice License"

    def process(self, instance):

        if hou.isApprentice():
            families = [instance.data["family"]]
            families += instance.data.get("families", [])
            families = " ".join(families).title()

            raise PublishValidationError(
                "{} Publishing requires a non apprentice license."
                .format(families),
                title=self.label)
