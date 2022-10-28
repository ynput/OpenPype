import bpy

import pyblish.api
from openpype.pipeline import legacy_io


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

        assert cameras, "No camera found in review collection"

        # TODO (kaamaurice): manage multiple cameras.

        camera = cameras[0].name
        self.log.debug(f"camera: {camera}")

        # get isolate objects list from meshes instance members .
        isolate_objects = [
            obj
            for obj in instance
            if isinstance(obj, bpy.types.Object)
            and obj.type in ("MESH", "CURVE", "SURFACE")
        ]

        reviewable_instances = [
            context_instance
            for context_instance in instance.context
            if context_instance.data.get("family") not in (
                "review", "camera", "workfile"
            )
        ]

        if reviewable_instances:
            if len(reviewable_instances) > 1:
                self.log.warning(
                    f"Multiple subsets for review {reviewable_instances}"
                )

            reviewable_instance = reviewable_instances[0]
            self.log.debug(f"Subset for review: {reviewable_instance}")

            if not isinstance(reviewable_instance.data.get("families"), list):
                reviewable_instance.data["families"] = []
            reviewable_instance.data["families"].append("review")

            reviewable_instance.data.update({
                "review_camera": camera,
                "frameStart": instance.context.data["frameStart"],
                "frameEnd": instance.context.data["frameEnd"],
                "fps": instance.context.data["fps"],
                "isolate": isolate_objects,
            })
            instance.data["remove"] = True

        if not instance.data.get("remove"):

            task = legacy_io.Session.get("AVALON_TASK")

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
