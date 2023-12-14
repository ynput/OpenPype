from openpype.hosts.fusion.lib import GenericCreateSaver


class CreateImageSaver(GenericCreateSaver):
    """Fusion Saver to generate single image.

     Created to explicitly separate single ('image') or
        multi frame('render) outputs.
    """
    identifier = "io.openpype.creators.fusion.imagesaver"
    label = "Image (saver)"
    name = "image"
    family = "image"
    description = "Fusion Saver to generate image"

    def get_detail_description(self):
        return """Fusion Saver to generate single image.

        This creator is expected for publishing of image sequences for 'render'
        product type. (But can publish even single frame 'render'.

        Select what should be source of rendered image:
        (select only single frame):
        - "Current asset context" - values set on Asset in DB (Ftrack)
        - "From render in/out" - from node itself
        - "From composition timeline" - from timeline

        Supports local and deadline rendering.

        Supports selection from predefined set of output file extensions:
        - exr
        - tga
        - png
        - tif
        - jpg

        Created to explicitly separate single ('image') or
        multi frame('render) outputs.
        """
