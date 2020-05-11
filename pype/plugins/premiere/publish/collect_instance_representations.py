import os
import pyblish.api


class CollectClipRepresentations(pyblish.api.InstancePlugin):
    """
    Collecting frameranges needed for ftrack integration

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Clip Representations"
    order = pyblish.api.CollectorOrder
    families = ['clip']

    def process(self, instance):
        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        ins_d = instance.data
        staging_dir = ins_d["stagingDir"]
        frame_start = ins_d["frameStart"]
        frame_end = ins_d["frameEnd"]
        handle_start = ins_d["handleStart"]
        handle_end = ins_d["handleEnd"]
        fps = ins_d["fps"]
        files_list = ins_d.get("files")

        if not files_list:
            return

        json_repr_ext = ins_d["jsonReprExt"]
        json_repr_subset = ins_d["jsonReprSubset"]

        if files_list:
            file = next((f for f in files_list
                         if json_repr_subset in f), None)
        else:
            return

        if json_repr_ext in ["mov", "mp4"]:
            representation = {
                "files": file,
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartFtrack": frame_start - handle_start,
                "frameEndFtrack": frame_end - handle_end,
                "step": 1,
                "fps": fps,
                "name": json_repr_subset,
                "ext": json_repr_ext,
                "tags": ["review", "delete"]
            }
        else:
            representation = {
                "files": file,
                "stagingDir": staging_dir,
                "step": 1,
                "fps": fps,
                "name": json_repr_subset,
                "ext": json_repr_ext,
                "tags": ["review"]
            }
        self.log.debug("representation: {}".format(representation))
        instance.data["representations"].append(representation)

        thumb = next((f for f in files_list
                      if "thumbnail" in f), None)
        if thumb:
            thumb_representation = {
                'files': thumb,
                'stagingDir': staging_dir,
                'name': "thumbnail",
                'thumbnail': True,
                'ext': os.path.splitext(thumb)[-1].replace(".", "")
            }
            self.log.debug("representation: {}".format(thumb_representation))
            instance.data["representations"].append(
                thumb_representation)
