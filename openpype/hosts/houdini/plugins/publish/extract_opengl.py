import pyblish.api

from openpype.pipeline import publish


class ExtractOpenGL(publish.Extractor):
    """Add additional data into the OpenGL representation.

    The actual render happens via `ExtractROPs`.
    """

    order = pyblish.api.ExtractorOrder + 0.001
    label = "Extract OpenGL"
    families = ["review"]
    hosts = ["houdini"]

    def process(self, instance):

        assert instance.data["representations"]

        tags = ["review"]
        if not instance.data.get("keepImages"):
            tags.append("delete")

        representation = instance.data["representations"][0]
        representation.update({
            "frameStart": instance.data["frameStartHandle"],
            "frameEnd": instance.data["frameEndHandle"],
            "tags": tags,
            "preview": True,
            "camera_name": instance.data.get("review_camera")
        })
