import pyblish.api
import pype.api


class ValidateTextureBatchWorkfiles(pyblish.api.ContextPlugin):
    """Validates that textures workfile has collected resources (optional)."""

    label = "Validate Texture Batch"
    hosts = ["standalonepublisher"]
    order = pype.api.ValidateContentsOrder
    families = ["workfile", "textures"]
    optional = True

    def process(self, context):

        workfiles = []
        for instance in context:
            if instance.data["family"] == "workfile":
                workfiles.append(instance.data["representations"][0]["files"])

                if not instance.data.get("resources"):
                    msg = "No resources for workfile {}".\
                           format(instance.data["name"])
                    self.log.warning(msg)
