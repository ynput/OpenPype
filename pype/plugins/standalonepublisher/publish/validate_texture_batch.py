import pyblish.api
import pype.api


class ValidateTextureBatch(pyblish.api.ContextPlugin):
    """Validates that some texture files are present."""

    label = "Validate Texture Batch"
    hosts = ["standalonepublisher"]
    order = pype.api.ValidateContentsOrder
    families = ["workfile", "textures"]
    optional = False

    def process(self, context):
        present = False
        for instance in context:
            if instance.data["family"] == "textures":
                self.log.info("Some textures present.")

                return

        assert present, "No textures found in published batch!"
