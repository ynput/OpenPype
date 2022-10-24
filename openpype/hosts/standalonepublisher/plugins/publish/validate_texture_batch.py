import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
)


class ValidateTextureBatch(pyblish.api.InstancePlugin):
    """Validates that some texture files are present."""

    label = "Validate Texture Presence"
    hosts = ["standalonepublisher"]
    order = ValidateContentsOrder
    families = ["texture_batch_workfile"]
    optional = False

    def process(self, instance):
        present = False
        for instance in instance.context:
            if instance.data["family"] == "textures":
                self.log.info("At least some textures present.")

                return

        msg = "No textures found in published batch!"
        if not present:
            raise PublishXmlValidationError(self, msg)
