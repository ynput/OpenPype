# -*- coding: utf-8 -*-
"""Library of functions useful for 3dsmax pipeline."""
import contextlib
import logging
import json
from typing import Any, Dict, Union

import six
from openpype.pipeline import get_current_project_name, colorspace
from openpype.settings import get_project_settings
from openpype.pipeline.context_tools import (
    get_current_project, get_current_project_asset)
from openpype.style import load_stylesheet
from pymxs import runtime as rt


JSON_PREFIX = "JSON::"
log = logging.getLogger("openpype.hosts.max")


def get_main_window():
    """Acquire Max's main window"""
    from qtpy import QtWidgets
    top_widgets = QtWidgets.QApplication.topLevelWidgets()
    name = "QmaxApplicationWindow"
    for widget in top_widgets:
        if (
            widget.inherits("QMainWindow")
            and widget.metaObject().className() == name
        ):
            return widget
    raise RuntimeError('Count not find 3dsMax main window.')


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

        # default value behavior
        # convert maxscript boolean values
        if value == "true":
            value = True
        elif value == "false":
            value = False

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


def get_frame_range(asset_doc=None) -> Union[Dict[str, Any], None]:
    """Get the current assets frame range and handles.

    Args:
        asset_doc (dict): Asset Entity Data

    Returns:
        dict: with frame start, frame end, handle start, handle end.
    """
    # Set frame start/end
    if asset_doc is None:
        asset_doc = get_current_project_asset()

    data = asset_doc["data"]
    frame_start = data.get("frameStart")
    frame_end = data.get("frameEnd")

    if frame_start is None or frame_end is None:
        return {}

    frame_start = int(frame_start)
    frame_end = int(frame_end)
    handle_start = int(data.get("handleStart", 0))
    handle_end = int(data.get("handleEnd", 0))
    frame_start_handle = frame_start - handle_start
    frame_end_handle = frame_end + handle_end

    return {
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end,
        "frameStartHandle": frame_start_handle,
        "frameEndHandle": frame_end_handle,
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

    set_timeline(
        frame_range["frameStartHandle"], frame_range["frameEndHandle"])
    set_render_frame_range(
        frame_range["frameStartHandle"], frame_range["frameEndHandle"])


def reset_unit_scale():
    """Apply the unit scale setting to 3dsMax
    """
    project_name = get_current_project_name()
    settings = get_project_settings(project_name).get("max")
    scene_scale = settings.get("unit_scale_settings",
                               {}).get("scene_unit_scale")
    if scene_scale:
        rt.units.DisplayType = rt.Name("Metric")
        rt.units.MetricType = rt.Name(scene_scale)
    else:
        rt.units.DisplayType = rt.Name("Generic")


def convert_unit_scale():
    """Convert system unit scale in 3dsMax
    for fbx export

    Returns:
        str: unit scale
    """
    unit_scale_dict = {
        "millimeters": "mm",
        "centimeters": "cm",
        "meters": "m",
        "kilometers": "km"
    }
    current_unit_scale = rt.Execute("units.MetricType as string")
    return unit_scale_dict[current_unit_scale]


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
    reset_colorspace()
    reset_unit_scale()


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


def is_headless():
    """Check if 3dsMax runs in batch mode.
    If it returns True, it runs in 3dsbatch.exe
    If it returns False, it runs in 3dsmax.exe
    """
    return rt.maxops.isInNonInteractiveMode()


def set_timeline(frameStart, frameEnd):
    """Set frame range for timeline editor in Max
    """
    rt.animationRange = rt.interval(frameStart, frameEnd)
    return rt.animationRange


def reset_colorspace():
    """OCIO Configuration
    Supports in 3dsMax 2024+

    """
    if int(get_max_version()) < 2024:
        return
    project_name = get_current_project_name()
    colorspace_mgr = rt.ColorPipelineMgr
    project_settings = get_project_settings(project_name)

    max_config_data = colorspace.get_imageio_config(
        project_name, "max", project_settings)
    if max_config_data:
        ocio_config_path = max_config_data["path"]
        colorspace_mgr = rt.ColorPipelineMgr
        colorspace_mgr.Mode = rt.Name("OCIO_Custom")
        colorspace_mgr.OCIOConfigPath = ocio_config_path


def check_colorspace():
    parent = get_main_window()
    if parent is None:
        log.info("Skipping outdated pop-up "
                 "because Max main window can't be found.")
    if int(get_max_version()) >= 2024:
        color_mgr = rt.ColorPipelineMgr
        project_name = get_current_project_name()
        project_settings = get_project_settings(project_name)
        max_config_data = colorspace.get_imageio_config(
            project_name, "max", project_settings)
        if max_config_data and color_mgr.Mode != rt.Name("OCIO_Custom"):
            if not is_headless():
                from openpype.widgets import popup
                dialog = popup.Popup(parent=parent)
                dialog.setWindowTitle("Warning: Wrong OCIO Mode")
                dialog.setMessage("This scene has wrong OCIO "
                                  "Mode setting.")
                dialog.setButtonText("Fix")
                dialog.setStyleSheet(load_stylesheet())
                dialog.on_clicked.connect(reset_colorspace)
                dialog.show()

def unique_namespace(namespace, format="%02d",
                     prefix="", suffix="", con_suffix="CON"):
    """Return unique namespace

    Arguments:
        namespace (str): Name of namespace to consider
        format (str, optional): Formatting of the given iteration number
        suffix (str, optional): Only consider namespaces with this suffix.
        con_suffix: max only, for finding the name of the master container

    >>> unique_namespace("bar")
    # bar01
    >>> unique_namespace(":hello")
    # :hello01
    >>> unique_namespace("bar:", suffix="_NS")
    # bar01_NS:

    """

    def current_namespace():
        current = namespace
        # When inside a namespace Max adds no trailing :
        if not current.endswith(":"):
            current += ":"
        return current

    # Always check against the absolute namespace root
    # There's no clash with :x if we're defining namespace :a:x
    ROOT = ":" if namespace.startswith(":") else current_namespace()

    # Strip trailing `:` tokens since we might want to add a suffix
    start = ":" if namespace.startswith(":") else ""
    end = ":" if namespace.endswith(":") else ""
    namespace = namespace.strip(":")
    if ":" in namespace:
        # Split off any nesting that we don't uniqify anyway.
        parents, namespace = namespace.rsplit(":", 1)
        start += parents + ":"
        ROOT += start

    iteration = 1
    increment_version = True
    while increment_version:
        nr_namespace = namespace + format % iteration
        unique = prefix + nr_namespace + suffix
        container_name = f"{unique}:{namespace}{con_suffix}"
        if not rt.getNodeByName(container_name):
            name_space = start + unique + end
            increment_version = False
            return name_space
        else:
            increment_version = True
        iteration += 1


def get_namespace(container_name):
    """Get the namespace and name of the sub-container

    Args:
        container_name (str): the name of master container

    Raises:
        RuntimeError: when there is no master container found

    Returns:
        namespace (str): namespace of the sub-container
        name (str): name of the sub-container
    """
    node = rt.getNodeByName(container_name)
    if not node:
        raise RuntimeError("Master Container Not Found..")
    name = rt.getUserProp(node, "name")
    namespace = rt.getUserProp(node, "namespace")
    return namespace, name


def object_transform_set(container_children):
    """A function which allows to store the transform of
    previous loaded object(s)
    Args:
        container_children(list): A list of nodes

    Returns:
        transform_set (dict): A dict with all transform data of
        the previous loaded object(s)
    """
    transform_set = {}
    for node in container_children:
        name = f"{node.name}.transform"
        transform_set[name] = node.pos
        name = f"{node.name}.scale"
        transform_set[name] = node.scale
    return transform_set


def get_plugins() -> list:
    """Get all loaded plugins in 3dsMax

    Returns:
        plugin_info_list: a list of loaded plugins
    """
    manager = rt.PluginManager
    count = manager.pluginDllCount
    plugin_info_list = []
    for p in range(1, count + 1):
        plugin_info = manager.pluginDllName(p)
        plugin_info_list.append(plugin_info)

    return plugin_info_list


@contextlib.contextmanager
def render_resolution(width, height):
    """Set render resolution option during context

    Args:
        width (int): render width
        height (int): render height
    """
    current_renderWidth = rt.renderWidth
    current_renderHeight = rt.renderHeight
    try:
        rt.renderWidth = width
        rt.renderHeight = height
        yield
    finally:
        rt.renderWidth = current_renderWidth
        rt.renderHeight = current_renderHeight


@contextlib.contextmanager
def suspended_refresh():
    """Suspended refresh for scene and modify panel redraw.
    """
    if is_headless():
        yield
        return
    rt.disableSceneRedraw()
    rt.suspendEditing()
    try:
        yield

    finally:
        rt.enableSceneRedraw()
        rt.resumeEditing()
