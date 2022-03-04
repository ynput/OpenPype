import pyblish.api

import openpype.api
from openpype.pipeline import PublishXmlValidationError


class ValidateTextureBatchWorkfiles(pyblish.api.InstancePlugin):
    """Validates that textures workfile has collected resources (optional).

        Collected resources means secondary workfiles (in most cases).
    """

    label = "Validate Texture Workfile Has Resources"
    hosts = ["standalonepublisher"]
    order = openpype.api.ValidateContentsOrder
    families = ["texture_batch_workfile"]
    optional = True

    # from presets
    main_workfile_extensions = ['mra']

    def process(self, instance):
        if instance.data["family"] == "workfile":
            ext = instance.data["representations"][0]["ext"]
            if ext not in self.main_workfile_extensions:
                self.log.warning("Only secondary workfile present!")
                return

            if not instance.data.get("resources"):
                msg = "No secondary workfile present for workfile '{}'". \
                    format(instance.data["name"])
                ext = self.main_workfile_extensions[0]
                formatting_data = {"file_name": instance.data["name"],
                                   "extension": ext}

                raise PublishXmlValidationError(self, msg,
                                                formatting_data=formatting_data
                                                )
