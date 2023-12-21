# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
import hou


class ValidateHoudiniNotApprenticeLicense(pyblish.api.InstancePlugin):
    """Validate the Houdini instance runs a non Apprentice license.

    USD ROPs:
        When extracting USD files from an apprentice Houdini license,
        the resulting files will get "scrambled" with a license protection
        and get a special .usdnc suffix.

        This currently breaks the Subset/representation pipeline so we disallow
        any publish with apprentice license.

    Alembic ROPs:
        Houdini Apprentice does not export Alembic.
    """

    order = pyblish.api.ValidatorOrder
    families = ["usd", "abc", "fbx", "camera"]
    hosts = ["houdini"]
    label = "Houdini Apprentice License"

    def process(self, instance):

        if hou.isApprentice():
            # Find which family was matched with the plug-in
            families = {instance.data["family"]}
            families.update(instance.data.get("families", []))
            disallowed_families = families.intersection(self.families)
            families = " ".join(sorted(disallowed_families)).title()

            raise PublishValidationError(
                "{} publishing requires a non apprentice license."
                .format(families),
                title=self.label)
