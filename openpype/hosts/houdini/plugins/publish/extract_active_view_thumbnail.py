import pyblish.api
import tempfile
from openpype.pipeline import publish
from openpype.hosts.houdini.api import lib
from openpype.hosts.houdini.api.pipeline import IS_HEADLESS


class ExtractActiveViewThumbnail(publish.Extractor):
    """Set instance thumbnail to a screengrab of current active viewport.

    This makes it so that if an instance does not have a thumbnail set yet that
    it will get a thumbnail of the currently active view at the time of
    publishing as a fallback.

    """
    order = pyblish.api.ExtractorOrder + 0.49
    label = "Extract Active View Thumbnail"
    families = ["workfile"]
    hosts = ["houdini"]

    def process(self, instance):
        if IS_HEADLESS:
            self.log.debug(
                "Skip extraction of active view thumbnail, due to being in"
                "headless mode."
            )
            return

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

        with tempfile.NamedTemporaryFile("w", suffix=".jpg") as tmp:
            thumbnail_path = tmp.name

        instance.context.data["cleanupFullPaths"].append(thumbnail_path)

        sceneview = lib.get_scene_viewer()
        lib.sceneview_snapshot(sceneview, thumbnail_path)

        return thumbnail_path
