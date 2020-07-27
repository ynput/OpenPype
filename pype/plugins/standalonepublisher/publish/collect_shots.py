import os

import opentimelineio as otio
from bson import json_util

import pyblish.api
from pype import lib
from avalon import io


class OTIO_View(pyblish.api.Action):
    """Currently disabled because OTIO requires PySide2. Issue on Qt.py:
    https://github.com/PixarAnimationStudios/OpenTimelineIO/issues/289
    """

    label = "OTIO View"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        instance = context[0]
        representation = instance.data["representations"][0]
        file_path = os.path.join(
            representation["stagingDir"], representation["files"]
        )
        lib._subprocess(["otioview", file_path])


class CollectShots(pyblish.api.InstancePlugin):
    """Collect Anatomy object into Context"""

    order = pyblish.api.CollectorOrder
    label = "Collect Shots"
    hosts = ["standalonepublisher"]
    families = ["editorial"]
    actions = []

    def process(self, instance):
        representation = instance.data["representations"][0]
        file_path = os.path.join(
            representation["stagingDir"], representation["files"]
        )
        instance.context.data["editorialPath"] = file_path

        extension = os.path.splitext(file_path)[1][1:]
        kwargs = {}
        if extension == "edl":
            # EDL has no frame rate embedded so needs explicit frame rate else
            # 24 is asssumed.
            kwargs["rate"] = lib.get_asset()["data"]["fps"]

        timeline = otio.adapters.read_from_file(file_path, **kwargs)
        tracks = timeline.each_child(
            descended_from_type=otio.schema.track.Track
        )
        asset_entity = instance.context.data["assetEntity"]
        asset_name = asset_entity["name"]

        # Ask user for sequence start. Usually 10:00:00:00.
        sequence_start_frame = 900000

        # Project specific prefix naming. This needs to be replaced with some
        # options to be more flexible.
        asset_name = asset_name.split("_")[0]

        instances = []
        for track in tracks:
            track_start_frame = (
                abs(track.source_range.start_time.value) - sequence_start_frame
            )
            for child in track.each_child():

                # Transitions are ignored, because Clips have the full frame
                # range.
                if isinstance(child, otio.schema.transition.Transition):
                    continue

                if child.name is None:
                    continue

                # Hardcoded to expect a shot name of "[name].[extension]"
                child_name = os.path.splitext(child.name)[0].lower()
                name = f"{asset_name}_{child_name}"

                frame_start = track_start_frame
                frame_start += child.range_in_parent().start_time.value
                frame_end = track_start_frame
                frame_end += child.range_in_parent().end_time_inclusive().value

                label = f"{name} (framerange: {frame_start}-{frame_end})"
                instances.append(
                    instance.context.create_instance(**{
                        "name": name,
                        "label": label,
                        "frameStart": frame_start,
                        "frameEnd": frame_end,
                        "family": "shot",
                        "families": ["review", "ftrack"],
                        "ftrackFamily": "review",
                        "asset": name,
                        "subset": "shotMain",
                        "representations": [],
                        "source": file_path
                    })
                )

        visual_hierarchy = [asset_entity]
        while True:
            visual_parent = io.find_one(
                {"_id": visual_hierarchy[-1]["data"]["visualParent"]}
            )
            if visual_parent:
                visual_hierarchy.append(visual_parent)
            else:
                visual_hierarchy.append(instance.context.data["projectEntity"])
                break

        context_hierarchy = None
        for entity in visual_hierarchy:
            childs = {}
            if context_hierarchy:
                name = context_hierarchy.pop("name")
                childs = {name: context_hierarchy}
            else:
                for instance in instances:
                    childs[instance.data["name"]] = {
                        "childs": {},
                        "entity_type": "Shot",
                        "custom_attributes": {
                            "frameStart": instance.data["frameStart"],
                            "frameEnd": instance.data["frameEnd"]
                        }
                    }

            context_hierarchy = {
                "entity_type": entity["data"]["entityType"],
                "childs": childs,
                "name": entity["name"]
            }

        name = context_hierarchy.pop("name")
        context_hierarchy = {name: context_hierarchy}
        instance.context.data["hierarchyContext"] = context_hierarchy
        self.log.info(
            "Hierarchy:\n" +
            json_util.dumps(context_hierarchy, sort_keys=True, indent=4)
        )
