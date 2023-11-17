import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateTyCacheSplinesData(pyblish.api.InstancePlugin,
                                 OptionalPyblishPluginMixin):
    """Validate TyCache Splines data when the export
    mode is Tycache(Splines)"""

    order = pyblish.api.ValidatorOrder + 0.01
    families = ["tycache"]
    hosts = ["max"]
    label = "TyCache Splines Data"
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        if instance.data["exportMode"] != 6:
            self.log.debug("The Export Mode is not tyCache(Splines). "
                           "Skipping Validate TyFlow Splines Data")
            return

        invalid = self.get_invalid(instance)
        if invalid:
            bullet_point_invalid_statement = "\n".join(
                "- {}".format(err) for err
                in invalid
            )
            report = (
                "Required TyCache Splines Data has invalid value.\n\n"
                f"{bullet_point_invalid_statement}\n\n"
            )
            raise PublishValidationError(
                report,
                title="Invalid Value for Required TyCache Splines Data")

    @classmethod
    def get_invalid(cls, instance):
        invalid = []
        members = instance.data["members"]
        tyc_attrs = instance.data.get("tyc_attrs", {})
        if not tyc_attrs:
            invalid.append(f"No tyCache attributes found in {members}")

        if "tycacheSplines" not in tyc_attrs.keys():
            invalid.append("Mandatory tyCache Attributes 'tycacheSplines' "
                           f"is not included in {members}")
        return invalid
