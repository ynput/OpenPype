import json

from maya import cmds, mel

import pyblish.api

from openpype.client import get_asset_by_id
from openpype.hosts.maya.api.lib import lsattr, get_highest_in_hierarchy


def get_parents(project_name, asset_entity, parents=[]):
    visual_parent = asset_entity["data"]["visualParent"]
    if visual_parent is None:
        return []

    parent = get_asset_by_id(
        project_name,
        str(asset_entity["data"]["visualParent"]),
        fields=["name", "type", "data.visualParent"]
    )
    parents.append(parent)

    for grand_parent in get_parents(project_name, parent):
        if grand_parent not in parents:
            parents.append(grand_parent)

    return parents


class CollectShotData(pyblish.api.InstancePlugin):
    """Collect shot data."""

    # Offset to before CollectHierarchy
    order = pyblish.api.CollectorOrder - 0.077
    label = "Collect Shot Data"
    families = ["shot"]

    def process(self, instance):
        node = cmds.sets(instance.data["instance_node"], query=True)[0]
        frame_start = cmds.getAttr(node + ".timeRangeStart")
        frame_end = cmds.getAttr(node + ".timeRangeStop") - 1
        asset_entity = instance.context.data["assetEntity"]
        project_entity = instance.context.data["projectEntity"]
        width_key = "resolutionWidth"
        height_key = "resolutionHeight"
        pixelAspect_key = "pixelAspect"
        instance.data.update(
            {
                "range": [frame_start, frame_end],
                "heroTrack": True,  # Requirement for CollectHierarchy
                "handleStart": 0,
                "handleEnd": 0,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "clipIn": frame_start,
                "clipOut": frame_end,
                "fps": mel.eval("currentTimeUnitToFPS()"),
                "resolutionWidth": asset_entity.get(
                    width_key, project_entity.get(width_key, 1920)
                ),
                "resolutionHeight": asset_entity.get(
                    height_key, project_entity.get(height_key, 1080)
                ),
                "pixelAspect": asset_entity.get(
                    pixelAspect_key, project_entity.get(pixelAspect_key, 1)
                ),
                "asset": instance.data["name"],
                # Disabling task fetching in collect_anatomy_instance_data
                "task": None,
                # For extract_maya_scene_raw.
                "exactSetMembersOnly": False
            }
        )

        # Set hierarchy parents.
        instance.data["parents"] = []
        context_parents = instance.context.data.get("parents")
        if context_parents is None:
            parents = get_parents(project_entity["name"], asset_entity)
            for parent in reversed(parents):
                instance.data["parents"].append(
                    {
                        "entity_name": parent["name"],
                        "entity_type": parent["type"]
                    }
                )
            instance.data["parents"].append(
                {
                    "entity_name": asset_entity["name"],
                    "entity_type": asset_entity["type"]
                }
            )
            instance.context.data["parents"] = instance.data["parents"]
        else:
            instance.data["parents"] = instance.context.data["parents"]

        self.log.debug(
            json.dumps(instance.data["parents"], indent=4, sort_keys=True)
        )

        # Set frame ranges.
        attributes = instance.data["creator_attributes"]
        if attributes["use_start_frame"]:
            instance.data["frameOffset"] = (
                attributes["start_frame"] - frame_start
            )
            instance.data["frameStart"] = attributes["start_frame"]
            instance.data["frameEnd"] = (
                (frame_end - frame_start) + attributes["start_frame"]
            )

        if attributes["use_handles"]:
            instance.data["handleStart"] = attributes["handle_start"]
            instance.data["handleEnd"] = attributes["handle_end"]

        instance.data["update_timeline"] = attributes["update_timeline"]


class CollectShotsData(pyblish.api.ContextPlugin):
    """Collect shots data."""

    order = CollectShotData.order + 0.01
    label = "Collect Shots Data"
    families = ["shot"]

    def process(self, context):
        # Collect everything from the scene to export, except shot instances.
        nodes_to_export = get_highest_in_hierarchy(cmds.ls(dagObjects=True))
        for node in lsattr("id", "pyblish.avalon.instance"):
            if cmds.getAttr(node + ".family") == "shot":
                continue

            nodes_to_export.append(node)

        # Collect playback range to each shot instance.
        time_ranges = [
            cmds.playbackOptions(minTime=True, query=True) - 1,
            cmds.playbackOptions(maxTime=True, query=True)
        ]
        for instance in context:
            families = instance.data["families"] + [instance.data["family"]]
            if "shot" not in families:
                continue

            time_ranges.extend(instance.data["range"])
            instance.extend(nodes_to_export)

        context.data["shotsTimeRanges"] = time_ranges
