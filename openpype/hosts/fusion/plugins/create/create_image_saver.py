from openpype.lib import NumberDef

from openpype.hosts.fusion.api.plugin import GenericCreateSaver
from openpype.hosts.fusion.api import get_current_comp


class CreateImageSaver(GenericCreateSaver):
    """Fusion Saver to generate single image.

     Created to explicitly separate single ('image') or
        multi frame('render) outputs.

    This might be temporary creator until 'alias' functionality will be
    implemented to limit creation of additional product types with similar, but
    not the same workflows.
    """
    identifier = "io.openpype.creators.fusion.imagesaver"
    label = "Image (saver)"
    name = "image"
    family = "image"
    description = "Fusion Saver to generate image"

    default_frame = 0

    def get_detail_description(self):
        return """Fusion Saver to generate single image.

        This creator is expected for publishing of single frame `image` product
        type.

        Artist should provide frame number (integer) to specify which frame
        should be published. It must be inside of global timeline frame range.

        Supports local and deadline rendering.

        Supports selection from predefined set of output file extensions:
        - exr
        - tga
        - png
        - tif
        - jpg

        Created to explicitly separate single frame ('image') or
        multi frame ('render') outputs.
        """

    def get_pre_create_attr_defs(self):
        """Settings for create page"""
        attr_defs = [
            self._get_render_target_enum(),
            self._get_reviewable_bool(),
            self._get_frame_int(),
            self._get_image_format_enum(),
        ]
        return attr_defs

    def _get_frame_int(self):
        return NumberDef(
            "frame",
            default=self.default_frame,
            label="Frame",
            tooltip="Set frame to be rendered, must be inside of global "
                    "timeline range"
        )
