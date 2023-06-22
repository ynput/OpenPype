# -*- coding: utf-8 -*-
"""Library of functions useful for 3dsmax pipeline."""
import contextlib
import json
from typing import Any, Dict, Union

import six
from openpype.pipeline.context_tools import (
    get_current_project, get_current_project_asset,)
from pymxs import runtime as rt

JSON_PREFIX = "JSON::"


def imprint(node_name: str, data: dict) -> bool:
    node = rt.GetNodeByName(node_name)
    if not node:
        return False

    for k, v in data.items():
        if isinstance(v, (dict, list)):
            rt.SetUserProp(node, k, f"{JSON_PREFIX}{json.dumps(v)}")
        else:
            rt.SetUserProp(node, k, v)

    return True


def lsattr(
        attr: str,
        value: Union[str, None] = None,
        root: Union[str, None] = None) -> list:
    """List nodes having attribute with specified value.

    Args:
        attr (str): Attribute name to match.
        value (str, Optional): Value to match, of omitted, all nodes
            with specified attribute are returned no matter of value.
        root (str, Optional): Root node name. If omitted, scene root is used.

    Returns:
        list of nodes.
    """
    root = rt.RootNode if root is None else rt.GetNodeByName(root)

    def output_node(node, nodes):
        nodes.append(node)
        for child in node.Children:
            output_node(child, nodes)

    nodes = []
    output_node(root, nodes)
    return [
        n for n in nodes
        if rt.GetUserProp(n, attr) == value
    ] if value else [
        n for n in nodes
        if rt.GetUserProp(n, attr)
    ]


def read(container) -> dict:
    data = {}
    props = rt.GetUserPropBuffer(container)
    # this shouldn't happen but let's guard against it anyway
    if not props:
        return data

    for line in props.split("\r\n"):
        try:
            key, value = line.split("=")
        except ValueError:
            # if the line cannot be split we can't really parse it
            continue

        value = value.strip()
        if isinstance(value.strip(), six.string_types) and \
                value.startswith(JSON_PREFIX):
            with contextlib.suppress(json.JSONDecodeError):
                value = json.loads(value[len(JSON_PREFIX):])
        data[key.strip()] = value

    data["instance_node"] = container.Name

    return data


@contextlib.contextmanager
def maintained_selection():
    previous_selection = rt.GetCurrentSelection()
    try:
        yield
    finally:
        if previous_selection:
            rt.Select(previous_selection)
        else:
            rt.Select()


def get_all_children(parent, node_type=None):
    """Handy function to get all the children of a given node

    Args:
        parent (3dsmax Node1): Node to get all children of.
        node_type (None, runtime.class): give class to check for
            e.g. rt.FFDBox/rt.GeometryClass etc.

    Returns:
        list: list of all children of the parent node
    """
    def list_children(node):
        children = []
        for c in node.Children:
            children.append(c)
            children = children + list_children(c)
        return children
    child_list = list_children(parent)

    return ([x for x in child_list if rt.SuperClassOf(x) == node_type]
            if node_type else child_list)


def get_current_renderer():
    """
    Notes:
        Get current renderer for Max

    Returns:
        "{Current Renderer}:{Current Renderer}"
        e.g. "Redshift_Renderer:Redshift_Renderer"
    """
    return rt.renderers.production


def get_default_render_folder(project_setting=None):
    return (project_setting["max"]
                           ["RenderSettings"]
                           ["default_render_image_folder"])


def set_render_frame_range(start_frame, end_frame):
    """
    Note:
        Frame range can be specified in different types. Possible values are:
        * `1` - Single frame.
        * `2` - Active time segment ( animationRange ).
        * `3` - User specified Range.
        * `4` - User specified Frame pickup string (for example `1,3,5-12`).

    Todo:
        Current type is hard-coded, there should be a custom setting for this.
    """
    rt.rendTimeType = 3
    if start_frame is not None and end_frame is not None:
        rt.rendStart = int(start_frame)
        rt.rendEnd = int(end_frame)


def get_multipass_setting(project_setting=None):
    return (project_setting["max"]
                           ["RenderSettings"]
                           ["multipass"])


def set_scene_resolution(width: int, height: int):
    """Set the render resolution

    Args:
        width(int): value of the width
        height(int): value of the height

    Returns:
        None

    """
    # make sure the render dialog is closed
    # for the update of resolution
    # Changing the Render Setup dialog settings should be done
    # with the actual Render Setup dialog in a closed state.
    if rt.renderSceneDialog.isOpen():
        rt.renderSceneDialog.close()

    rt.renderWidth = width
    rt.renderHeight = height


def reset_scene_resolution():
    """Apply the scene resolution from the project definition

    scene resolution can be overwritten by an asset if the asset.data contains
    any information regarding scene resolution .
    Returns:
        None
    """
    data = ["data.resolutionWidth", "data.resolutionHeight"]
    project_resolution = get_current_project(fields=data)
    project_resolution_data = project_resolution["data"]
    asset_resolution = get_current_project_asset(fields=data)
    asset_resolution_data = asset_resolution["data"]
    # Set project resolution
    project_width = int(project_resolution_data.get("resolutionWidth", 1920))
    project_height = int(project_resolution_data.get("resolutionHeight", 1080))
    width = int(asset_resolution_data.get("resolutionWidth", project_width))
    height = int(asset_resolution_data.get("resolutionHeight", project_height))

    set_scene_resolution(width, height)


def get_frame_range() -> Union[Dict[str, Any], None]:
    """Get the current assets frame range and handles.

    Returns:
        dict: with frame start, frame end, handle start, handle end.
    """
    # Set frame start/end
    asset = get_current_project_asset()
    frame_start = asset["data"].get("frameStart")
    frame_end = asset["data"].get("frameEnd")

    if frame_start is None or frame_end is None:
        return

    handle_start = asset["data"].get("handleStart", 0)
    handle_end = asset["data"].get("handleEnd", 0)
    return {
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end
    }


def reset_frame_range(fps: bool = True):
    """Set frame range to current asset.
    This is part of 3dsmax documentation:

    animationRange: A System Global variable which lets you get and
        set an Interval value that defines the start and end frames
        of the Active Time Segment.
    frameRate: A System Global variable which lets you get
            and set an Integer value that defines the current
            scene frame rate in frames-per-second.
    """
    if fps:
        data_fps = get_current_project(fields=["data.fps"])
        fps_number = float(data_fps["data"]["fps"])
        rt.frameRate = fps_number
    frame_range = get_frame_range()
    frame_start_handle = frame_range["frameStart"] - int(
        frame_range["handleStart"]
    )
    frame_end_handle = frame_range["frameEnd"] + int(frame_range["handleEnd"])
    rt.interval(frame_start_handle, frame_end_handle)
    set_render_frame_range(frame_start_handle, frame_end_handle)


def set_context_setting():
    """Apply the project settings from the project definition

    Settings can be overwritten by an asset if the asset.data contains
    any information regarding those settings.

    Examples of settings:
        frame range
        resolution

    Returns:
        None
    """
    reset_scene_resolution()
    reset_frame_range()


def get_max_version():
    """
    Args:
    get max version date for deadline

    Returns:
        #(25000, 62, 0, 25, 0, 0, 997, 2023, "")
        max_info[7] = max version date
    """
    max_info = rt.MaxVersion()
    return max_info[7]


@contextlib.contextmanager
def viewport_camera(camera):
    original = rt.viewport.getCamera()
    review_camera = rt.getNodeByName(camera)
    try:
        rt.viewport.setCamera(review_camera)
        yield
    finally:
        rt.viewport.setCamera(original)
