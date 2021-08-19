import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateInstanceAssetRepair(pyblish.api.Action):
    """Repair the instance asset."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        pass


class ValidateInstanceAsset(pyblish.api.InstancePlugin):
    """Validate the instance asset is the current selected context asset.

        As it might happen that multiple worfiles are opened, switching
        between them would mess with selected context.
        In that case outputs might be output under wrong asset!

        Repair action will use Context asset value (from Workfiles or Launcher)
        Closing and reopening with Workfiles will refresh  Context value.
    """

    label = "Validate With Error"
    hosts = ["testhost"]
    actions = [ValidateInstanceAssetRepair]
    order = pyblish.api.ValidatorOrder

    def process(self, instance):
        raise PublishValidationError("Crashing")
