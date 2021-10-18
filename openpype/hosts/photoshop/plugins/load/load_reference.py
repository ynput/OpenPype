import re

from avalon import api, photoshop

from openpype.hosts.photoshop.plugins.lib import get_unique_layer_name
from openpype.hosts.photoshop.plugins.load.load_image import ImageLoader

stub = photoshop.stub()


class ReferenceLoader(ImageLoader):
    """Load reference images

    Stores the imported asset in a container named after the asset.
    """

    families = ["image", "render"]
    representations = ["*"]

    def import_layer(self, file_name, layer_name):
        return stub.import_smart_object(file_name, layer_name,
                                        as_reference=True)
