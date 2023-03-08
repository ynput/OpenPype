from itertools import chain
import bpy

import pyblish.api
from openpype.hosts.blender.api.utils import (
    BL_OUTLINER_TYPES,
    get_all_outliner_children,
)
from openpype.pipeline import legacy_io


class CollectReview(pyblish.api.InstancePlugin):
    """Collect Review data"""

    order = pyblish.api.CollectorOrder + 0.3
    label = "Collect Review Data"
    families = ["review"]

    def process(self, instance):

        self.log.debug(f"instance: {instance}")

        # get cameras
        # TODO could be substituted by _get_camera_from_datablocks
        # in openpype/hosts/blender/plugins/create/create_camera.py
        outliner_children = set(
            chain.from_iterable(
                get_all_outliner_children(d)
                for d in instance
                if isinstance(d, tuple(BL_OUTLINER_TYPES))
            )
        )
        cameras = [
            c
            for c in outliner_children | set(instance)
            if isinstance(c, bpy.types.Object) and c.type == "CAMERA"
        ]

        assert cameras, "No camera found in review collection"

        # TODO (kaamaurice): manage multiple cameras.

        camera = cameras[0].name
        self.log.debug(f"camera: {camera}")

        # Collect audio tracks
        audio_tracks = [
            {
                "offset": sequence.frame_start + sequence.frame_offset_start,
                "filename": sequence.sound.filepath,
            }
            for sequence in bpy.context.scene.sequence_editor.sequences
            if sequence.type == "SOUND" and sequence.volume > 0
        ]
        self.log.debug(f"audio: {audio_tracks}")

        # get isolate objects list from meshes instance members .
        isolate_objects = [
            obj
            for obj in instance
            if isinstance(obj, bpy.types.Object)
            and obj.type in ("MESH", "CURVE", "SURFACE")
        ]

        instance.data.update(
            {
                "subset": instance.data.get("subset"),
                "review_camera": camera,
                "frameStart": instance.context.data["frameStart"],
                "frameEnd": instance.context.data["frameEnd"],
                "fps": instance.context.data["fps"],
                "isolate": isolate_objects,
                "audio": audio_tracks,
            }
        )
        self.log.debug(f"instance data: {instance.data}")
