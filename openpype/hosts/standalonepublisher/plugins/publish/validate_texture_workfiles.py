import pyblish.api
import openpype.api


class ValidateTextureBatchWorkfiles(pyblish.api.InstancePlugin):
    """Validates that textures workfile has collected resources (optional).

        Collected recourses means secondary workfiles (in most cases).
    """

    label = "Validate Texture Workfile"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["workfile"]
    optional = True

    def process(self, instance):
        if instance.data["family"] == "workfile":
            if not instance.data.get("resources"):
                msg = "No resources for workfile {}".\
                    format(instance.data["name"])
                self.log.warning(msg)
