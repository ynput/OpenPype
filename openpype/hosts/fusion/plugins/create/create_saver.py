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
