import pyblish.api

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

    def process(self, instance):
        if instance.data["family"] != "workfile":
            return

        ext = instance.data["representations"][0]["ext"]
        main_workfile_extensions = self.get_main_workfile_extensions(
            instance
        )
        if ext not in main_workfile_extensions:
            self.log.warning("Only secondary workfile present!")
            return

        if not instance.data.get("resources"):
            msg = "No secondary workfile present for workfile '{}'". \
                format(instance.data["name"])
            ext = main_workfile_extensions[0]
            formatting_data = {"file_name": instance.data["name"],
                               "extension": ext}

            raise PublishXmlValidationError(
                self, msg, formatting_data=formatting_data)

    @staticmethod
    def get_main_workfile_extensions(instance):
        project_settings = instance.context.data["project_settings"]

        try:
            extensions = (project_settings["standalonepublisher"]
                                          ["publish"]
                                          ["CollectTextures"]
                                          ["main_workfile_extensions"])
        except KeyError:
            raise Exception("Setting 'Main workfile extensions' not found."
                            " The setting must be set for the"
                            " 'Collect Texture' publish plugin of the"
                            " 'Standalone Publish' tool.")

        return extensions
