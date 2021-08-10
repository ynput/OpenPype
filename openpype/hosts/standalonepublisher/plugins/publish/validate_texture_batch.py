import pyblish.api
import openpype.api


class ValidateTextureBatch(pyblish.api.InstancePlugin):
    """Validates that some texture files are present."""

    label = "Validate Texture Presence"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["texture_batch_workfile"]
    optional = False

    def process(self, instance):
        present = False
        for instance in instance.context:
            if instance.data["family"] == "textures":
                self.log.info("Some textures present.")

                return

        assert present, "No textures found in published batch!"
