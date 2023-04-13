import os
from pprint import pformat
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.openrv.api.review import get_path_annotated_frame, extract_annotated_frame

import rv

class ExtractOpenRVAnnotatedFrames(publish.Extractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Annotations from Session"
    hosts = ["openrv"]
    families = ["annotation"]

    def process(self, instance):

        self.log.info("instance.data: `{}`".format(
            pformat(instance.data)))
        #self.log.info("workfile", str(instance.data['asset_folder']))
        asset_folder = instance.data['asset_folder_path']
        asset = instance.data['asset']
        annotated_frame = instance.data['annotated_frame']

        annotated_frame_path = get_path_annotated_frame(frame=annotated_frame,
                                                   asset_folder=asset_folder)
        print(annotated_frame_path)
        annotated_frame_folder, file = os.path.split(annotated_frame_path)

        if not os.path.isdir(annotated_frame_folder):
            os.makedirs(annotated_frame_folder)
        #
        # # save the frame
        #
        # #extract_annotated_frame(filepath=annotated_frame)
        #
        # assert os.path.isfile(annotated_frame)
        #
        # folder, file = os.path.split(annotated_frame)
        # filename, ext = os.path.splitext(file)
        #
        # representation = {
        #     "name": ext.lstrip("."),
        #     "ext": ext.lstrip("."),
        #     "files": file,
        #     "stagingDir": folder,
        # }
        #
        # if "representations" not in instance.data:
        #     instance.data["representations"] = []
        #
        # instance.data["representations"].append(representation)