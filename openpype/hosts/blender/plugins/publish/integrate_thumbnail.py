import pyblish.api
from openpype.plugins.publish import integrate_thumbnail


class IntegrateThumbnails(integrate_thumbnail.IntegrateThumbnails):
    """Integrate Thumbnails."""

    label = "Integrate Thumbnails"
    order = pyblish.api.IntegratorOrder + 0.01
    families = ["review", "model", "rig"]
