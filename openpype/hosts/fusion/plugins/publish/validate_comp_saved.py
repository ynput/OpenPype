import os

import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateFusionCompSaved(pyblish.api.ContextPlugin):
    """Ensure current comp is saved"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Comp Saved"
    families = ["render", "image"]
    hosts = ["fusion"]

    def process(self, context):

        comp = context.data.get("currentComp")
        assert comp, "Must have Comp object"
        attrs = comp.GetAttrs()

        filename = attrs["COMPS_FileName"]
        if not filename:
            raise PublishValidationError("Comp is not saved.",
                                         title=self.label)

        if not os.path.exists(filename):
            raise PublishValidationError(
                "Comp file does not exist: %s" % filename, title=self.label)

        if attrs["COMPB_Modified"]:
            self.log.warning("Comp is modified. Save your comp to ensure your "
                             "changes propagate correctly.")
