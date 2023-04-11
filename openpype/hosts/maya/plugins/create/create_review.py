import os
from collections import OrderedDict
import json

from openpype.hosts.maya.api import (
    lib,
    plugin
)
from openpype.settings import get_project_settings
from openpype.pipeline import get_current_project_name, get_current_task_name
from openpype.lib.profiles_filtering import filter_profiles
from openpype.client import get_asset_by_name


class CreateReview(plugin.Creator):
    """Single baked camera"""

    name = "reviewDefault"
    label = "Review"
    family = "review"
    icon = "video-camera"
    keepImages = False
    isolate = False
    imagePlane = True
    Width = 0
    Height = 0
    transparency = [
        "preset",
        "simple",
        "object sorting",
        "weighted average",
        "depth peeling",
        "alpha cut"
    ]
    useMayaTimeline = True
    panZoom = False

    def __init__(self, *args, **kwargs):
        super(CreateReview, self).__init__(*args, **kwargs)
        data = OrderedDict(**self.data)

        project_name = get_current_project_name()
        profiles = get_project_settings(
            project_name
        )["maya"]["publish"]["ExtractPlayblast"].get("profiles")

        preset = None
        if profiles:
            asset_doc = get_asset_by_name(project_name, data["asset"])
            task_name = get_current_task_name()
            task_type = asset_doc["data"]["tasks"][task_name]["type"]

            filtering_criteria = {
                "hosts": "maya",
                "families": "review",
                "task_names": task_name,
                "task_types": task_type,
                "subset": data["subset"]
            }
            profile = filter_profiles(
                profiles, filtering_criteria, logger=self.log
            )
            preset = profile["capture_preset"] if profile else None
        else:
            self.log.warning("No profiles present for extract playblast.")

        # Option for using Maya or asset frame range in settings.
        frame_range = lib.get_frame_range()
        if self.useMayaTimeline:
            frame_range = lib.collect_animation_data(fps=True)
        for key, value in frame_range.items():
            data[key] = value

        data["fps"] = lib.collect_animation_data(fps=True)["fps"]

        data["review_width"] = self.Width
        data["review_height"] = self.Height
        data["isolate"] = self.isolate
        data["keepImages"] = self.keepImages
        data["imagePlane"] = self.imagePlane
        data["transparency"] = self.transparency
        data["panZoom"] = self.panZoom

        if preset:
            if os.environ.get("OPENPYPE_DEBUG") == "1":
                self.log.debug(
                    "Using preset: {}".format(
                        json.dumps(preset, indent=4, sort_keys=True)
                    )
                )
            data["review_width"] = preset["Resolution"]["width"]
            data["review_height"] = preset["Resolution"]["height"]
            data["isolate"] = preset["Generic"]["isolate_view"]
            data["imagePlane"] = preset["Viewport Options"]["imagePlane"]
            data["panZoom"] = preset["Generic"]["pan_zoom"]

        self.data = data
