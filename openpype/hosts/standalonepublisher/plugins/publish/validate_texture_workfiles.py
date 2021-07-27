import pyblish.api
import openpype.api


class ValidateTextureBatchWorkfiles(pyblish.api.InstancePlugin):
    """Validates that textures workfile has collected resources (optional).

        Collected recourses means secondary workfiles (in most cases).
    """

    label = "Validate Texture Workfile Has Resources"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["workfile"]
    optional = True

    # from presets
    main_workfile_extensions = ['mra']

    def process(self, instance):
        if instance.data["family"] == "workfile":
            ext = instance.data["representations"][0]["ext"]
            if ext not in self.main_workfile_extensions:
                self.log.warning("Only secondary workfile present!")
                return

            msg = "No secondary workfiles present for workfile {}".\
                format(instance.data["name"])
            assert instance.data.get("resources"), msg
