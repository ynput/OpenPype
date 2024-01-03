import os

import pyblish.api

from openpype.pipeline import publish, registered_host
from openpype.hosts.houdini.api import lib
from openpype.hosts.houdini.api.pipeline import IS_HEADLESS

import hou


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
        self.log.debug(thumbnail)
        if not thumbnail:
            view_thumbnail = self.get_view_thumbnail(instance)
            if not view_thumbnail:
                return

            self.log.debug("Setting instance thumbnail path to: {}".format(
                view_thumbnail
            ))
            instance.data["thumbnailPath"] = view_thumbnail

    def get_view_thumbnail(self, instance):

        host = registered_host()
        current_filepath = host.get_current_workfile()
        if not current_filepath:
            self.log.error("No current workfile path. Thumbnail generation skipped")
            return

        thumbnail_path = "{}_thumbnail.jpg".format(
            current_filepath.rsplit('.', 1)[0])
        sceneview = lib.get_scene_viewer()
        lib.sceneview_snapshot(sceneview, thumbnail_path)

        return thumbnail_path
