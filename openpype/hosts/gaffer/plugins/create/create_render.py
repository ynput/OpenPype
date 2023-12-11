from openpype.hosts.gaffer.api import plugin

import Gaffer
import GafferImage


class CreateGafferImage(plugin.GafferCreatorBase):
    identifier = "io.openpype.creators.gaffer.image"
    label = "Image"
    family = "image"
    description = "Image writer"
    icon = "fa5.eye"

    def _create_node(self,
                     subset_name: str,
                     pre_create_data: dict) -> Gaffer.Node:
        return GafferImage.ImageWriter(subset_name)
