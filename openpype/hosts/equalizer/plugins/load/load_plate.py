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
from openpype.hosts.equalizer.api import Container, EqualizerHost
from openpype.lib.transcoding import IMAGE_EXTENSIONS
from openpype.pipeline import (
    get_current_project_name,
    get_representation_context,
)


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

    def load(self, context, name=None, namespace=None, options=None):
        representation = context["representation"]
        project_name = get_current_project_name()
        version = get_version_by_id(project_name, representation["parent"])

        file_path = self.file_path(representation, context)

        camera = tde4.createCamera("SEQUENCE")
        tde4.setCameraName(camera, name)
        camera_name = tde4.getCameraName(camera)

        print(
            f"Loading: {file_path} into {camera_name}")

        # set the path to sequence on the camera
        tde4.setCameraPath(camera, file_path)

        # set the sequence attributes star/end/step
        tde4.setCameraSequenceAttr(
            camera, int(version["data"].get("frameStart")),
            int(version["data"].get("frameEnd")), 1)

        container = Container(
            name=name,
            namespace=camera_name,
            loader=self.__class__.__name__,
            representation=str(representation["_id"]),
        )
        print(container)
        EqualizerHost.get_host().add_container(container)

    def update(self, container, representation):
        camera_list = tde4.getCameraList()
        try:
            camera = [
                c for c in camera_list if
                tde4.getCameraName(c) == container["namespace"]
            ][0]
        except IndexError:
            self.log.error(f'Cannot find camera {container["namespace"]}')
            print(f'Cannot find camera {container["namespace"]}')
            return

        context = get_representation_context(representation)
        file_path = self.file_path(representation, context)

        # set the path to sequence on the camera
        tde4.setCameraPath(camera, file_path)

        version = get_version_by_id(
            get_current_project_name(), representation["parent"])

        # set the sequence attributes star/end/step
        tde4.setCameraSequenceAttr(
            camera, int(version["data"].get("frameStart")),
            int(version["data"].get("frameEnd")), 1)

        print(container)
        EqualizerHost.get_host().add_container(container)

    def switch(self, container, representation):
        self.update(container, representation)

    def file_path(self, representation, context):
        is_sequence = len(representation["files"]) > 1
        print(f"is sequence {is_sequence}")
        if is_sequence:
            frame = representation["context"]["frame"]
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

        return self.filepath_from_context(context)
