import os

from openpype.lib.attribute_definitions import FileDef
from openpype.pipeline import (
    CreatedInstance,
    CreatorError
)
from openpype.hosts.traypublisher.api.plugin import TrayPublishCreator


class AudioCreator(TrayPublishCreator):
    """Creates audio instance on asset."""

    identifier = "io.openpype.creators.traypublisher.audio"
    label = "Audio"
    family = "audio"
    description = "Publish audio files."
    extensions = [".wav"]

    def get_detail_description(self):
        return """# Publish audio files."""

    def get_icon(self):
        return "volume"

    def create(self, subset_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("representation_file")
        if not repr_file:
            raise CreatorError("No files specified")

        instance_data["path"] = os.path.join(
            repr_file["directory"], repr_file["filenames"][0]
        )

        # Create new instance
        new_instance = CreatedInstance(
            self.family, subset_name, instance_data, self
        )
        self._store_new_instance(new_instance)

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "representation_file",
                folders=False,
                extensions=self.extensions,
                allow_sequences=True,
                single_item=True,
                label="Representation",
            )
        ]
