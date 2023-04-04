import bpy

import pyblish.api


class CollectReview(pyblish.api.InstancePlugin):
    """Collect Review data

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Collect Review Data"
    families = ["review"]

    def process(self, instance):

        self.log.debug(f"instance: {instance}")

        # get cameras
        cameras = [
            obj
            for obj in instance
            if isinstance(obj, bpy.types.Object) and obj.type == "CAMERA"
        ]

        assert len(cameras) == 1, (
            f"Not a single camera found in extraction: {cameras}"
        )
        camera = cameras[0].name
        self.log.debug(f"camera: {camera}")

        # get isolate objects list from meshes instance members .
        isolate_objects = [
            obj
            for obj in instance
            if isinstance(obj, bpy.types.Object) and obj.type == "MESH"
        ]

        if not instance.data.get("remove"):

            task = instance.context.data["task"]

            instance.data.update({
                "subset": f"{task}Review",
                "review_camera": camera,
                "frameStart": instance.context.data["frameStart"],
                "frameEnd": instance.context.data["frameEnd"],
                "fps": instance.context.data["fps"],
                "isolate": isolate_objects,
            })

            self.log.debug(f"instance data: {instance.data}")

            # TODO : Collect audio
            audio_tracks = []
            instance.data["audio"] = []
            for track in audio_tracks:
                instance.data["audio"].append(
                    {
                        "offset": track.offset.get(),
                        "filename": track.filename.get(),
                    }
                )
