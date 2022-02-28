import pyblish.api
from openpype.pipeline import PublishValidationError


class ValidateContainers(pyblish.api.InstancePlugin):
    """Validate existence of asset asset documents on instances.

    Without asset document it is not possible to publish the instance.

    If context has set asset document the validation is skipped.

    Plugin was added because there are cases when context asset is not defined
    e.g. in tray publisher.
    """

    label = "Validate Asset docs"
    order = pyblish.api.ValidatorOrder

    def process(self, instance):
        context_asset_doc = instance.context.data.get("assetEntity")
        if context_asset_doc:
            return

        if instance.data.get("assetEntity"):
            self.log.info("Instance have set asset document in it's data.")

        else:
            raise PublishValidationError((
                "Instance \"{}\" don't have set asset"
                " document which is needed for publishing."
            ).format(instance.data["name"]))
