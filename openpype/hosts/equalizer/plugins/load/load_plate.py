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
import os
import openpype.pipeline.load as load
from openpype.client import get_version_by_id
from openpype.hosts.equalizer.api import Container, EqualizerHost
from openpype.lib.transcoding import IMAGE_EXTENSIONS
from openpype.pipeline import (
    get_current_project_name,
    get_representation_context,
)
import xml.etree.ElementTree as et


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
    icon = "image"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        representation = context["representation"]
        project_name = get_current_project_name()
        version = get_version_by_id(project_name, representation["parent"])

        file_path = self.filepath_from_context(context)
        tde4.setProjectNotes("Loading: %s into %s"%(file_path, name))
        tde4.updateGUI()

        camera_id = tde4.getCurrentCamera()
        lens_id = tde4.getCameraLens(camera_id)

        image_dir, image_path = os.path.split(file_path)
        image_name, id, image_format = image_path.split(".")
        pattern = ".".join([image_name, len(id)*"#", image_format])
        pattern_path = os.path.join(image_dir, pattern)


        start_frame, end_frame = int(version["data"].get("frameStart")),  int(version["data"].get("frameEnd"))
        len_frames = end_frame - start_frame + 1

        # # set the sequence attributes star/end/step
        tde4.setCameraSequenceAttr(camera_id, start_frame, end_frame, 1)
        tde4.setCameraName(camera_id, name)
        tde4.setCameraPath(camera_id, pattern_path)
        tde4.setCameraFrameOffset(camera_id, start_frame)
        tde4.setCamera8BitColorGamma(camera_id, 2.2 if image_format == 'exr' else 1)
        tde4.setCameraPlaybackRange(camera_id,1,len_frames)
        # Set lens distortion model
        film_aspect = float(tde4.getLensFilmAspect(lens_id))
        if film_aspect > 2:
            tde4.setLensLDModel(lens_id, "3DE4 Anamorphic - Standard, Degree 4")

        # Assign the MetaData of the current frame into project
        if image_format == "exr":
            self._assignMetaData(camera_id, lens_id)


        container = Container(
            name=name,
            namespace=name,
            loader=self.__class__.__name__,
            representation=str(representation["_id"]),
        )
        EqualizerHost.get_host().add_container(container)


    def _assignMetaData(self, camera_id, lens_id):
        frame = tde4.getCurrentFrame(camera_id)
        frame_path = tde4.getCameraFrameFilepath(camera_id, frame)
        try:
            xml = tde4.convertOpenEXRMetaDataToXML(frame_path)
        except:
            print("File '" + frame_path + "' doesn't seem to be an EXR file.")
            return

        root = et.fromstring(xml)
        metadata_attrs = dict()
        for a in root.findall("attribute"):
            name = a.find("name").text
            value = a.find("value").text
            if name and value: metadata_attrs[name] = value

        # Assign the metadata attributes into Camera
        if 'camera_fps' in metadata_attrs:
            tde4.setCameraFPS(camera_id, float(metadata_attrs['camera_fps']))

        # Assign the metadata attributes into Lens
        if 'camera_focal' in metadata_attrs:
            camera_focal = metadata_attrs['camera_focal'].split()
            if camera_focal[1] == 'mm':
                tde4.setLensFocalLength(lens_id, float(camera_focal[0])/10)
            else:
                tde4.setLensFocalLength(lens_id, float(camera_focal[0]))


    def update(self, container, representation):
        camera_list = tde4.getCameraList()
        try:
            camera = [
                c for c in camera_list if
                tde4.getCameraName(c) == container["namespace"]
            ][0]
        except IndexError:
            self.log.error('Cannot find camera {}'.format(container["namespace"]))
            print('Cannot find camera {}'.format(container["namespace"]))
            return

        context = get_representation_context(representation)
        file_path = self.file_path(representation, context)

        image_dir, image_path = os.path.split(file_path)
        image_name, id, image_format = image_path.split(".")
        pattern = ".".join([image_name, len(id)*"#", image_format])
        pattern_path = os.path.join(image_dir, pattern)

        # set the sequence attributes star/end/step
        tde4.setCameraSequenceAttr(
            camera, int(version["data"].get("frameStart")),
            int(version["data"].get("frameEnd")), 1)

        # set the path to sequence on the camera
        tde4.setCameraPath(camera, pattern_path)

        version = get_version_by_id(
            get_current_project_name(), representation["parent"])

        print(container)
        EqualizerHost.get_host().add_container(container)

    def switch(self, container, representation):
        self.update(container, representation)

    # def file_path(self, representation, context):
    #     is_sequence = len(representation["files"]) > 1
    #     print("is sequence %is_sequence"%is_sequence)
    #     if is_sequence:
    #         frame = representation["context"]["frame"]
    #         hashes = "#" * len(str(frame))
    #         if (
    #                 "{originalBasename}" in representation["data"]["template"]
    #         ):
    #             origin_basename = context["originalBasename"]
    #             context["originalBasename"] = origin_basename.replace(
    #                 frame, hashes
    #             )

    #         # Replace the frame with the hash in the frame
    #         representation["context"]["frame"] = hashes

    #     return self.filepath_from_context(context)
