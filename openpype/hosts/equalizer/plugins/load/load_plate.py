"""Loader for image sequences.

This loads published sequence to the current camera
because this workflow is the most common in production.

If current camera is not defined, it will try to use first camera and
if there is no camera at all, it will create new one.

TODO:
    * Support for setting handles, calculation frame ranges, EXR
      options, etc.
    * Add support for color management - at least put correct gamma
      to image corrections.

"""
import tde4

import openpype.pipeline.load as load
from openpype.client import get_version_by_id
from openpype.lib.transcoding import IMAGE_EXTENSIONS
from openpype.pipeline import get_current_project_name


class LoadPlate(load.LoaderPlugin):
    families = [
        "imagesequence",
        "review",
        "render",
        "plate",
        "image",
        "online",
    ]

    representations = ["*"]
    extensions = {ext.lstrip(".") for ext in IMAGE_EXTENSIONS}

    label = "Load sequence"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        representation = context["representation"]

        project_name = get_current_project_name()
        version = get_version_by_id(project_name, representation["parent"])

        is_sequence = len(representation["files"]) > 1
        if is_sequence:
            frame = context["frame"]
            hashes = "#" * len(str(frame))
            if (
                    "{originalBasename}" in representation["data"]["template"]
            ):
                origin_basename = context["originalBasename"]
                context["originalBasename"] = origin_basename.replace(
                    frame, hashes
                )

            # Replace the frame with the hash in the frame
            representation["context"]["frame"] = hashes

        file_path = self.filepath_from_context(context)

        # Try to get current camera. If not found, use first that can
        # be found in. If even that camera can't be found, create new one.
        camera = tde4.getCurrentCamera() or tde4.getFirstCamera() or tde4.createCamera("SEQUENCE")  # noqa: E501

        self.log.info(
            f"Loading: {file_path} into {tde4.getCameraName(camera)}")

        # set the path to sequence on the camera
        tde4.setCameraPath(file_path)

        # set the sequence attributes star/end/step
        tde4.setCameraSequenceAttr(
            camera, version["data"].get("frameStart"),
            version["data"].get("frameEnd"), 1)
