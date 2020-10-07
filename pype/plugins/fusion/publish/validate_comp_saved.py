import os

import pyblish.api


class ValidateFusionCompSaved(pyblish.api.ContextPlugin):
    """Ensure current comp is saved"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Comp Saved"
    families = ["render"]
    hosts = ["fusion"]

    def process(self, context):

        comp = context.data.get("currentComp")
        assert comp, "Must have Comp object"
        attrs = comp.GetAttrs()

        filename = attrs["COMPS_FileName"]
        if not filename:
            raise RuntimeError("Comp is not saved.")

        if not os.path.exists(filename):
            raise RuntimeError("Comp file does not exist: %s" % filename)

        if attrs["COMPB_Modified"]:
            self.log.warning("Comp is modified. Save your comp to ensure your "
                             "changes propagate correctly.")
