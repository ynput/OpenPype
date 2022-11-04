import os
import pyblish.api

from openpype.settings import get_project_settings
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
)


class ValidateTextureBatchWorkfiles(pyblish.api.InstancePlugin):
    """Validates that textures workfile has collected resources (optional).

        Collected resources means secondary workfiles (in most cases).
    """

    label = "Validate Texture Workfile Has Resources"
    hosts = ["standalonepublisher"]
    order = ValidateContentsOrder
    families = ["texture_batch_workfile"]
    optional = True

    #TODO(2-rec): remove/change comment
    # from presets
    main_workfile_extensions = ['mra']

    def process(self, instance):
        if instance.data["family"] == "workfile":
            ext = instance.data["representations"][0]["ext"]
            main_workfile_extensions = self.get_main_workfile_extensions()
            if ext not in main_workfile_extensions:
                self.log.warning("Only secondary workfile present!")
                return

            if not instance.data.get("resources"):
                msg = "No secondary workfile present for workfile '{}'". \
                    format(instance.data["name"])
                ext = main_workfile_extensions[0]
                formatting_data = {"file_name": instance.data["name"],
                                   "extension": ext}

                raise PublishXmlValidationError(self, msg,
                                                formatting_data=formatting_data
                                                )

    @classmethod
    def get_main_workfile_extensions(cls):
        project_settings = get_project_settings(os.environ["AVALON_PROJECT"])

        #TODO: find better way? (depends on other plugin)
        try:
            extensions = (project_settings["standalonepublisher"]
                                          ["publish"]
                                          ["CollectTextures"]
                                          ["main_workfile_extensions"])
        except KeyError:
            extensions = cls.main_workfile_extensions

        return extensions
