import attr
import hou
from openpype.hosts.houdini.api.lib import get_color_management_preferences


@attr.s
class LayerMetadata(object):
    """Data class for Render Layer metadata."""
    frameStart = attr.ib()
    frameEnd = attr.ib()


@attr.s
class RenderProduct(object):
    """Getting Colorspace as
    Specific Render Product Parameter for submitting
    publish job.

    """
    colorspace = attr.ib()                      # colorspace
    view = attr.ib()
    productName = attr.ib(default=None)


class ARenderProduct(object):

    def __init__(self):
        """Constructor."""
        # Initialize
        self.layer_data = self._get_layer_data()
        self.layer_data.products = self.get_colorspace_data()

    def _get_layer_data(self):
        return LayerMetadata(
            frameStart=int(hou.playbar.frameRange()[0]),
            frameEnd=int(hou.playbar.frameRange()[1]),
        )

    def get_colorspace_data(self):
        """To be implemented by renderer class.

        This should return a list of RenderProducts.

        Returns:
            list: List of RenderProduct

        """
        data = get_color_management_preferences()
        colorspace_data = [
            RenderProduct(
                colorspace=data["display"],
                view=data["view"],
                productName=""
            )
        ]
        return colorspace_data
