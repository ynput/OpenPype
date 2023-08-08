import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui

import pyblish.api
import tempfile


class ExtractActiveViewThumbnail(pyblish.api.InstancePlugin):
    """Set instance thumbnail to a screengrab of current active viewport.

    This makes it so that if an instance does not have a thumbnail set yet that
    it will get a thumbnail of the currently active view at the time of
    publishing as a fallback.

    """
    order = pyblish.api.ExtractorOrder + 0.49
    label = "Active View Thumbnail"
    families = ["workfile"]
    hosts = ["maya"]

    def process(self, instance):
        thumbnail = instance.data.get("thumbnailPath")
        if not thumbnail:
            view_thumbnail = self.get_view_thumbnail(instance)
            if not view_thumbnail:
                return

            self.log.debug("Setting instance thumbnail path to: {}".format(
                view_thumbnail
            ))
            instance.data["thumbnailPath"] = view_thumbnail

    def get_view_thumbnail(self, instance):
        cache_key = "__maya_view_thumbnail"
        context = instance.context

        if cache_key not in context.data:
            # Generate only a single thumbnail, even for multiple instances
            with tempfile.NamedTemporaryFile(suffix="_thumbnail.jpg",
                                             delete=False) as f:
                path = f.name

            view = omui.M3dView.active3dView()
            image = om.MImage()
            view.readColorBuffer(image, True)
            image.writeToFile(path, "jpg")
            self.log.debug("Generated thumbnail: {}".format(path))

            context.data[cache_key] = path
        return context.data[cache_key]

