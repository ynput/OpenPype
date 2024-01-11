from openpype.lib import EnumDef

from openpype.hosts.fusion.api.plugin import GenericCreateSaver


class CreateSaver(GenericCreateSaver):
    """Fusion Saver to generate image sequence of 'render' product type.

     Original Saver creator targeted for 'render' product type. It uses
     original not to descriptive name because of values in Settings.
    """
    identifier = "io.openpype.creators.fusion.saver"
    label = "Render (saver)"
    name = "render"
    family = "render"
    description = "Fusion Saver to generate image sequence"

    default_frame_range_option = "asset_db"

    def get_detail_description(self):
        return """Fusion Saver to generate image sequence.

        This creator is expected for publishing of image sequences for 'render'
        product type. (But can publish even single frame 'render'.)

        Select what should be source of render range:
        - "Current asset context" - values set on Asset in DB (Ftrack)
        - "From render in/out" - from node itself
        - "From composition timeline" - from timeline

        Supports local and farm rendering.

        Supports selection from predefined set of output file extensions:
        - exr
        - tga
        - png
        - tif
        - jpg
        """

    def get_pre_create_attr_defs(self):
        """Settings for create page"""
        attr_defs = [
            self._get_render_target_enum(),
            self._get_reviewable_bool(),
            self._get_frame_range_enum(),
            self._get_image_format_enum(),
        ]
        return attr_defs

    def _get_frame_range_enum(self):
        frame_range_options = {
            "asset_db": "Current asset context",
            "render_range": "From render in/out",
            "comp_range": "From composition timeline",
        }

        return EnumDef(
            "frame_range_source",
            items=frame_range_options,
            label="Frame range source",
            default=self.default_frame_range_option
        )
