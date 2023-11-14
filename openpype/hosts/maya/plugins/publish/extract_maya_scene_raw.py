# -*- coding: utf-8 -*-
"""Extract data as Maya scene (raw)."""
import os
import contextlib

from maya import cmds

from openpype.hosts.maya.api.lib import maintained_selection
from openpype.pipeline import AVALON_CONTAINER_ID, publish


def offset_node(node, offset):
    if cmds.nodeType(node).startswith("animCurve"):
        cmds.keyframe(node, edit=True, relative=True, timeChange=offset)

    if cmds.nodeType(node) == "imagePlane":
        node_attr = node + ".frameOffset"
        cmds.setAttr(node_attr, cmds.getAttr(node_attr) + (-offset))

    if cmds.nodeType(node) == "timeSliderBookmark":
        for attr in ["timeRangeStart", "timeRangeStop"]:
            node_attr = "{}.{}".format(node, attr)
            cmds.setAttr(node_attr, cmds.getAttr(node_attr) + offset)


@contextlib.contextmanager
def offset_scene(offset):
    # Exit early for easier stacking of context managers.
    if offset is None:
        yield

    nodes = cmds.ls(type="animCurve")
    nodes += cmds.ls(type="imagePlane")
    nodes += cmds.ls(type="timeSliderBookmark")
    changed_nodes = []
    try:
        for node in nodes:
            offset_node(node, offset)
            changed_nodes.append(node)
        yield
    finally:
        for node in changed_nodes:
            offset_node(node, -offset)


@contextlib.contextmanager
def maintain_timeline(frame_start, frame_end, handle_start, handle_end):
    # Exit early for easier stacking of context managers.
    if None in [frame_start, frame_end, handle_start, handle_end]:
        yield

    data = {
        "minTime": None,
        "maxTime": None,
        "animationStartTime": None,
        "animationEndTime": None
    }
    for key in data.keys():
        kwargs = {key: True, "query": True}
        data[key] = cmds.playbackOptions(**kwargs)

    current_time = cmds.currentTime(query=True)
    render_start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
    render_end_frame = cmds.getAttr("defaultRenderGlobals.endFrame")

    try:
        animation_start_time = frame_start - handle_start
        animation_end_time = frame_end + handle_start

        cmds.playbackOptions(
            minTime=frame_start,
            maxTime=frame_end,
            animationStartTime=animation_start_time,
            animationEndTime=animation_end_time
        )

        cmds.setAttr(
            "sceneConfigurationScriptNode.before",
            "playbackOptions -min {} -max {} -ast {} -aet {}".format(
                frame_start,
                frame_end,
                animation_start_time,
                animation_end_time
            ),
            type="string"
        )

        cmds.currentTime(frame_start)

        cmds.setAttr("defaultRenderGlobals.startFrame", frame_start)
        cmds.setAttr("defaultRenderGlobals.endFrame", frame_end)

        yield
    finally:
        cmds.playbackOptions(**data)

        cmds.setAttr(
            "sceneConfigurationScriptNode.before",
            "playbackOptions -min {} -max {} -ast {} -aet {}".format(
                data["minTime"],
                data["maxTime"],
                data["animationStartTime"],
                data["animationEndTime"]
            ),
            type="string"
        )

        cmds.currentTime(current_time, edit=True)

        cmds.setAttr("defaultRenderGlobals.startFrame", render_start_frame)
        cmds.setAttr("defaultRenderGlobals.endFrame", render_end_frame)


class ExtractMayaSceneRaw(publish.Extractor):
    """Extract as Maya Scene (raw).

    This will preserve all references, construction history, etc.
    """

    label = "Maya Scene (Raw)"
    hosts = ["maya"]
    families = ["mayaAscii",
                "mayaScene",
                "setdress",
                "layout",
                "camerarig",
                "shot"]
    scene_type = "ma"

    def process(self, instance):
        """Plugin entry point."""
        ext_mapping = (
            instance.context.data["project_settings"]["maya"]["ext_mapping"]
        )
        if ext_mapping:
            self.log.debug("Looking in settings for scene type ...")
            # use extension mapping for first family found
            for family in self.families:
                try:
                    self.scene_type = ext_mapping[family]
                    self.log.debug(
                        "Using {} as scene type".format(self.scene_type))
                    break
                except KeyError:
                    # no preset found
                    pass
        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # Whether to include all nodes in the instance (including those from
        # history) or only use the exact set members
        members_only = instance.data.get("exactSetMembersOnly", False)
        if members_only:
            members = instance.data.get("setMembers", list())
            if not members:
                raise RuntimeError("Can't export 'exact set members only' "
                                   "when set is empty.")
        else:
            members = instance[:]

        selection = members
        if set(self.add_for_families).intersection(
                set(instance.data.get("families", []))) or \
                instance.data.get("family") in self.add_for_families:
            selection += self._get_loaded_containers(members)

        # Perform extraction
        self.log.debug("Performing extraction ...")

        frame_offset = instance.data.get("frameOffset")
        self.log.debug("frameOffset: {}".format(frame_offset))

        frame_range = [None, None, None, None]
        if instance.data.get("update_timeline", False):
            frame_range = [
                instance.data["frameStart"],
                instance.data["frameEnd"],
                instance.data["handleStart"],
                instance.data["handleEnd"]
            ]
            self.log.debug("Updating timeline to {}.".format(frame_range))

        export_all = instance.data.get("exportAll", False)
        kwargs = {
            "force": True,
            "typ": "mayaAscii" if self.scene_type == "ma" else "mayaBinary",
            "exportSelected": not export_all,
            "exportAll": export_all,
            "preserveReferences": True,
            "constructionHistory": True,
            "shader": True,
            "constraints": True,
            "expressions": True
        }
        self.log.debug("Exporting with:\n{}".format(kwargs))
        with (maintained_selection(),
              offset_scene(frame_offset),
              maintain_timeline(*frame_range)
              ):
            cmds.select(selection, noExpand=True)
            cmds.file(path, **kwargs)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": dir_path
        }
        instance.data["representations"].append(representation)

        self.log.debug("Extracted instance '%s' to: %s" % (instance.name,
                                                           path))

    @staticmethod
    def _get_loaded_containers(members):
        # type: (list) -> list
        refs_to_include = {
            cmds.referenceQuery(node, referenceNode=True)
            for node in members
            if cmds.referenceQuery(node, isNodeReferenced=True)
        }

        members_with_refs = refs_to_include.union(members)

        obj_sets = cmds.ls("*.id", long=True, type="objectSet", recursive=True,
                           objectsOnly=True)

        loaded_containers = []
        for obj_set in obj_sets:

            if not cmds.attributeQuery("id", node=obj_set, exists=True):
                continue

            id_attr = "{}.id".format(obj_set)
            if cmds.getAttr(id_attr) != AVALON_CONTAINER_ID:
                continue

            set_content = set(cmds.sets(obj_set, query=True))
            if set_content.intersection(members_with_refs):
                loaded_containers.append(obj_set)

        return loaded_containers
