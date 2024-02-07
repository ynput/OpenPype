"""Standalone helper functions"""

import os
import copy
from pprint import pformat
import sys
import uuid
import re

import json
import logging
import contextlib
import capture
from .exitstack import ExitStack
from collections import OrderedDict, defaultdict
from math import ceil
from six import string_types

from maya import cmds, mel
from maya.api import OpenMaya

from openpype.client import (
    get_project,
    get_asset_by_name,
    get_subsets,
    get_last_versions,
    get_representation_by_name
)
from openpype.settings import get_project_settings
from openpype.pipeline import (
    get_current_project_name,
    get_current_asset_name,
    get_current_task_name,
    discover_loader_plugins,
    loaders_from_representation,
    get_representation_path,
    load_container,
    registered_host
)
from openpype.lib import NumberDef
from openpype.pipeline.context_tools import get_current_project_asset
from openpype.pipeline.create import CreateContext
from openpype.lib.profiles_filtering import filter_profiles


self = sys.modules[__name__]
self._parent = None

log = logging.getLogger(__name__)

IS_HEADLESS = not hasattr(cmds, "about") or cmds.about(batch=True)
ATTRIBUTE_DICT = {"int": {"attributeType": "long"},
                  "str": {"dataType": "string"},
                  "unicode": {"dataType": "string"},
                  "float": {"attributeType": "double"},
                  "bool": {"attributeType": "bool"}}

SHAPE_ATTRS = {"castsShadows",
               "receiveShadows",
               "motionBlur",
               "primaryVisibility",
               "smoothShading",
               "visibleInReflections",
               "visibleInRefractions",
               "doubleSided",
               "opposite"}


DEFAULT_MATRIX = [1.0, 0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0, 0.0,
                  0.0, 0.0, 1.0, 0.0,
                  0.0, 0.0, 0.0, 1.0]

# The maya alembic export types
_alembic_options = {
    "startFrame": float,
    "endFrame": float,
    "frameRange": str,  # "start end"; overrides startFrame & endFrame
    "eulerFilter": bool,
    "frameRelativeSample": float,
    "noNormals": bool,
    "renderableOnly": bool,
    "step": float,
    "stripNamespaces": bool,
    "uvWrite": bool,
    "wholeFrameGeo": bool,
    "worldSpace": bool,
    "writeVisibility": bool,
    "writeColorSets": bool,
    "writeFaceSets": bool,
    "writeCreases": bool,  # Maya 2015 Ext1+
    "writeUVSets": bool,   # Maya 2017+
    "dataFormat": str,
    "root": (list, tuple),
    "attr": (list, tuple),
    "attrPrefix": (list, tuple),
    "userAttr": (list, tuple),
    "melPerFrameCallback": str,
    "melPostJobCallback": str,
    "pythonPerFrameCallback": str,
    "pythonPostJobCallback": str,
    "selection": bool
}

INT_FPS = {15, 24, 25, 30, 48, 50, 60, 44100, 48000}
FLOAT_FPS = {23.98, 23.976, 29.97, 47.952, 59.94}


DISPLAY_LIGHTS_ENUM = [
    {"label": "Use Project Settings", "value": "project_settings"},
    {"label": "Default Lighting", "value": "default"},
    {"label": "All Lights", "value": "all"},
    {"label": "Selected Lights", "value": "selected"},
    {"label": "Flat Lighting", "value": "flat"},
    {"label": "No Lights", "value": "none"}
]


def get_main_window():
    """Acquire Maya's main window"""
    from qtpy import QtWidgets

    if self._parent is None:
        self._parent = {
            widget.objectName(): widget
            for widget in QtWidgets.QApplication.topLevelWidgets()
        }["MayaWindow"]
    return self._parent


@contextlib.contextmanager
def suspended_refresh(suspend=True):
    """Suspend viewport refreshes

    cmds.ogs(pause=True) is a toggle so we cant pass False.
    """
    if IS_HEADLESS:
        yield
        return

    original_state = cmds.ogs(query=True, pause=True)
    try:
        if suspend and not original_state:
            cmds.ogs(pause=True)
        yield
    finally:
        if suspend and not original_state:
            cmds.ogs(pause=True)


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context

    Example:
        >>> scene = cmds.file(new=True, force=True)
        >>> node = cmds.createNode("transform", name="Test")
        >>> cmds.select("persp")
        >>> with maintained_selection():
        ...     cmds.select("Test", replace=True)
        >>> "Test" in cmds.ls(selection=True)
        False

    """

    previous_selection = cmds.ls(selection=True)
    try:
        yield
    finally:
        if previous_selection:
            cmds.select(previous_selection,
                        replace=True,
                        noExpand=True)
        else:
            cmds.select(clear=True)


def reload_all_udim_tile_previews():
    """Regenerate all UDIM tile preview in texture file"""
    for texture_file in cmds.ls(type="file"):
        if cmds.getAttr("{}.uvTilingMode".format(texture_file)) > 0:
            cmds.ogs(regenerateUVTilePreview=texture_file)


@contextlib.contextmanager
def panel_camera(panel, camera):
    """Set modelPanel's camera during the context.

    Arguments:
        panel (str): modelPanel name.
        camera (str): camera name.

    """
    original_camera = cmds.modelPanel(panel, query=True, camera=True)
    try:
        cmds.modelPanel(panel, edit=True, camera=camera)
        yield
    finally:
        cmds.modelPanel(panel, edit=True, camera=original_camera)


def render_capture_preset(preset):
    """Capture playblast with a preset.

    To generate the preset use `generate_capture_preset`.

    Args:
        preset (dict): preset options

    Returns:
        str: Output path of `capture.capture`
    """

    # Force a refresh at the start of the timeline
    # TODO (Question): Why do we need to do this? What bug does it solve?
    #   Is this for simulations?
    cmds.refresh(force=True)
    refresh_frame_int = int(cmds.playbackOptions(query=True, minTime=True))
    cmds.currentTime(refresh_frame_int - 1, edit=True)
    cmds.currentTime(refresh_frame_int, edit=True)
    log.debug(
        "Using preset: {}".format(
            json.dumps(preset, indent=4, sort_keys=True)
        )
    )
    preset = copy.deepcopy(preset)
    # not supported by `capture` so we pop it off of the preset
    reload_textures = preset["viewport_options"].pop("loadTextures", False)
    panel = preset.pop("panel")
    with ExitStack() as stack:
        stack.enter_context(maintained_time())
        stack.enter_context(panel_camera(panel, preset["camera"]))
        stack.enter_context(viewport_default_options(panel, preset))
        if reload_textures:
            # Force immediate texture loading when to ensure
            # all textures have loaded before the playblast starts
            stack.enter_context(material_loading_mode(mode="immediate"))
            # Regenerate all UDIM tiles previews
            reload_all_udim_tile_previews()
        path = capture.capture(log=self.log, **preset)

    return path


def generate_capture_preset(instance, camera, path,
                            start=None, end=None, capture_preset=None):
    """Function for getting all the data of preset options for
    playblast capturing

    Args:
        instance (pyblish.api.Instance): instance
        camera (str): review camera
        path (str): filepath
        start (int): frameStart
        end (int): frameEnd
        capture_preset (dict): capture preset

    Returns:
        dict: Resulting preset
    """
    preset = load_capture_preset(data=capture_preset)

    preset["camera"] = camera
    preset["start_frame"] = start
    preset["end_frame"] = end
    preset["filename"] = path
    preset["overwrite"] = True
    preset["panel"] = instance.data["panel"]

    # Disable viewer since we use the rendering logic for publishing
    # We don't want to open the generated playblast in a viewer directly.
    preset["viewer"] = False

    # "isolate_view" will already have been applied at creation, so we'll
    # ignore it here.
    preset.pop("isolate_view")

    # Set resolution variables from capture presets
    width_preset = capture_preset["Resolution"]["width"]
    height_preset = capture_preset["Resolution"]["height"]

    # Set resolution variables from asset values
    asset_data = instance.data["assetEntity"]["data"]
    asset_width = asset_data.get("resolutionWidth")
    asset_height = asset_data.get("resolutionHeight")
    review_instance_width = instance.data.get("review_width")
    review_instance_height = instance.data.get("review_height")

    # Use resolution from instance if review width/height is set
    # Otherwise use the resolution from preset if it has non-zero values
    # Otherwise fall back to asset width x height
    # Else define no width, then `capture.capture` will use render resolution
    if review_instance_width and review_instance_height:
        preset["width"] = review_instance_width
        preset["height"] = review_instance_height
    elif width_preset and height_preset:
        preset["width"] = width_preset
        preset["height"] = height_preset
    elif asset_width and asset_height:
        preset["width"] = asset_width
        preset["height"] = asset_height

    # Isolate view is requested by having objects in the set besides a
    # camera. If there is only 1 member it'll be the camera because we
    # validate to have 1 camera only.
    if instance.data["isolate"] and len(instance.data["setMembers"]) > 1:
        preset["isolate"] = instance.data["setMembers"]

    # Override camera options
    # Enforce persisting camera depth of field
    camera_options = preset.setdefault("camera_options", {})
    camera_options["depthOfField"] = cmds.getAttr(
        "{0}.depthOfField".format(camera)
    )

    # Use Pan/Zoom from instance data instead of from preset
    preset.pop("pan_zoom", None)
    camera_options["panZoomEnabled"] = instance.data["panZoom"]

    # Override viewport options by instance data
    viewport_options = preset.setdefault("viewport_options", {})
    viewport_options["displayLights"] = instance.data["displayLights"]
    viewport_options["imagePlane"] = instance.data.get("imagePlane", True)

    # Override transparency if requested.
    transparency = instance.data.get("transparency", 0)
    if transparency != 0:
        preset["viewport2_options"]["transparencyAlgorithm"] = transparency

    # Update preset with current panel setting
    # if override_viewport_options is turned off
    if not capture_preset["Viewport Options"]["override_viewport_options"]:
        panel_preset = capture.parse_view(preset["panel"])
        panel_preset.pop("camera")
        preset.update(panel_preset)

    return preset


@contextlib.contextmanager
def viewport_default_options(panel, preset):
    """Context manager used by `render_capture_preset`.

    We need to explicitly enable some viewport changes so the viewport is
    refreshed ahead of playblasting.

    """
    # TODO: Clarify in the docstring WHY we need to set it ahead of
    #  playblasting. What issues does it solve?
    viewport_defaults = {}
    try:
        keys = [
            "useDefaultMaterial",
            "wireframeOnShaded",
            "xray",
            "jointXray",
            "backfaceCulling",
            "textures"
        ]
        for key in keys:
            viewport_defaults[key] = cmds.modelEditor(
                panel, query=True, **{key: True}
            )
            if preset["viewport_options"].get(key):
                cmds.modelEditor(
                    panel, edit=True, **{key: True}
                )
        yield
    finally:
        # Restoring viewport options.
        if viewport_defaults:
            cmds.modelEditor(
                panel, edit=True, **viewport_defaults
            )


@contextlib.contextmanager
def material_loading_mode(mode="immediate"):
    """Set material loading mode during context"""
    original = cmds.displayPref(query=True, materialLoadingMode=True)
    cmds.displayPref(materialLoadingMode=mode)
    try:
        yield
    finally:
        cmds.displayPref(materialLoadingMode=original)


def get_namespace(node):
    """Return namespace of given node"""
    node_name = node.rsplit("|", 1)[-1]
    if ":" in node_name:
        return node_name.rsplit(":", 1)[0]
    else:
        return ""


def strip_namespace(node, namespace):
    """Strip given namespace from node path.

    The namespace will only be stripped from names
    if it starts with that namespace. If the namespace
    occurs within another namespace it's not removed.

    Examples:
        >>> strip_namespace("namespace:node", namespace="namespace:")
        "node"
        >>> strip_namespace("hello:world:node", namespace="hello:world")
        "node"
        >>> strip_namespace("hello:world:node", namespace="hello")
        "world:node"
        >>> strip_namespace("hello:world:node", namespace="world")
        "hello:world:node"
        >>> strip_namespace("ns:group|ns:node", namespace="ns")
        "group|node"

    Returns:
        str: Node name without given starting namespace.

    """

    # Ensure namespace ends with `:`
    if not namespace.endswith(":"):
        namespace = "{}:".format(namespace)

    # The long path for a node can also have the namespace
    # in its parents so we need to remove it from each
    return "|".join(
        name[len(namespace):] if name.startswith(namespace) else name
        for name in node.split("|")
    )


def get_custom_namespace(custom_namespace):
    """Return unique namespace.

    The input namespace can contain a single group
    of '#' number tokens to indicate where the namespace's
    unique index should go. The amount of tokens defines
    the zero padding of the number, e.g ### turns into 001.

    Warning: Note that a namespace will always be
        prefixed with a _ if it starts with a digit

    Example:
        >>> get_custom_namespace("myspace_##_")
        # myspace_01_
        >>> get_custom_namespace("##_myspace")
        # _01_myspace
        >>> get_custom_namespace("myspace##")
        # myspace01

    """
    split = re.split("([#]+)", custom_namespace, 1)

    if len(split) == 3:
        base, padding, suffix = split
        padding = "%0{}d".format(len(padding))
    else:
        base = split[0]
        padding = "%02d"  # default padding
        suffix = ""

    return unique_namespace(
        base,
        format=padding,
        prefix="_" if not base or base[0].isdigit() else "",
        suffix=suffix
    )


def unique_namespace(namespace, format="%02d", prefix="", suffix=""):
    """Return unique namespace

    Arguments:
        namespace (str): Name of namespace to consider
        format (str, optional): Formatting of the given iteration number
        suffix (str, optional): Only consider namespaces with this suffix.

    >>> unique_namespace("bar")
    # bar01
    >>> unique_namespace(":hello")
    # :hello01
    >>> unique_namespace("bar:", suffix="_NS")
    # bar01_NS:

    """

    def current_namespace():
        current = cmds.namespaceInfo(currentNamespace=True,
                                     absoluteName=True)
        # When inside a namespace Maya adds no trailing :
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

    def exists(n):
        # Check for clash with nodes and namespaces
        fullpath = ROOT + n
        return cmds.objExists(fullpath) or cmds.namespace(exists=fullpath)

    iteration = 1
    while True:
        nr_namespace = namespace + format % iteration
        unique = prefix + nr_namespace + suffix

        if not exists(unique):
            return start + unique + end

        iteration += 1


def read(node):
    """Return user-defined attributes from `node`"""

    data = dict()

    for attr in cmds.listAttr(node, userDefined=True) or list():
        try:
            value = cmds.getAttr(node + "." + attr, asString=True)

        except RuntimeError:
            # For Message type attribute or others that have connections,
            # take source node name as value.
            source = cmds.listConnections(node + "." + attr,
                                          source=True,
                                          destination=False)
            source = cmds.ls(source, long=True) or [None]
            value = source[0]

        except ValueError:
            # Some attributes cannot be read directly,
            # such as mesh and color attributes. These
            # are considered non-essential to this
            # particular publishing pipeline.
            value = None

        data[attr] = value

    return data


def matrix_equals(a, b, tolerance=1e-10):
    """
    Compares two matrices with an imperfection tolerance

    Args:
        a (list, tuple): the matrix to check
        b (list, tuple): the matrix to check against
        tolerance (float): the precision of the differences

    Returns:
        bool : True or False

    """
    if not all(abs(x - y) < tolerance for x, y in zip(a, b)):
        return False
    return True


def float_round(num, places=0, direction=ceil):
    return direction(num * (10**places)) / float(10**places)


def pairwise(iterable):
    """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
    from six.moves import zip

    a = iter(iterable)
    return zip(a, a)


def collect_animation_defs(fps=False):
    """Get the basic animation attribute defintions for the publisher.

    Returns:
        OrderedDict

    """

    # get scene values as defaults
    frame_start = cmds.playbackOptions(query=True, minTime=True)
    frame_end = cmds.playbackOptions(query=True, maxTime=True)
    frame_start_handle = cmds.playbackOptions(
        query=True, animationStartTime=True
    )
    frame_end_handle = cmds.playbackOptions(query=True, animationEndTime=True)

    handle_start = frame_start - frame_start_handle
    handle_end = frame_end_handle - frame_end

    # build attributes
    defs = [
        NumberDef("frameStart",
                  label="Frame Start",
                  default=frame_start,
                  decimals=0),
        NumberDef("frameEnd",
                  label="Frame End",
                  default=frame_end,
                  decimals=0),
        NumberDef("handleStart",
                  label="Handle Start",
                  default=handle_start,
                  decimals=0),
        NumberDef("handleEnd",
                  label="Handle End",
                  default=handle_end,
                  decimals=0),
        NumberDef("step",
                  label="Step size",
                  tooltip="A smaller step size means more samples and larger "
                          "output files.\n"
                          "A 1.0 step size is a single sample every frame.\n"
                          "A 0.5 step size is two samples per frame.\n"
                          "A 0.2 step size is five samples per frame.",
                  default=1.0,
                  decimals=3),
    ]

    if fps:
        current_fps = mel.eval('currentTimeUnitToFPS()')
        fps_def = NumberDef(
            "fps", label="FPS", default=current_fps, decimals=5
        )
        defs.append(fps_def)

    return defs


def imprint(node, data):
    """Write `data` to `node` as userDefined attributes

    Arguments:
        node (str): Long name of node
        data (dict): Dictionary of key/value pairs

    Example:
        >>> from maya import cmds
        >>> def compute():
        ...   return 6
        ...
        >>> cube, generator = cmds.polyCube()
        >>> imprint(cube, {
        ...   "regularString": "myFamily",
        ...   "computedValue": lambda: compute()
        ... })
        ...
        >>> cmds.getAttr(cube + ".computedValue")
        6

    """

    for key, value in data.items():

        if callable(value):
            # Support values evaluated at imprint
            value = value()

        if isinstance(value, bool):
            add_type = {"attributeType": "bool"}
            set_type = {"keyable": False, "channelBox": True}
        elif isinstance(value, string_types):
            add_type = {"dataType": "string"}
            set_type = {"type": "string"}
        elif isinstance(value, int):
            add_type = {"attributeType": "long"}
            set_type = {"keyable": False, "channelBox": True}
        elif isinstance(value, float):
            add_type = {"attributeType": "double"}
            set_type = {"keyable": False, "channelBox": True}
        elif isinstance(value, (list, tuple)):
            add_type = {"attributeType": "enum", "enumName": ":".join(value)}
            set_type = {"keyable": False, "channelBox": True}
            value = 0  # enum default
        else:
            raise TypeError("Unsupported type: %r" % type(value))

        cmds.addAttr(node, longName=key, **add_type)
        cmds.setAttr(node + "." + key, value, **set_type)


def lsattr(attr, value=None):
    """Return nodes matching `key` and `value`

    Arguments:
        attr (str): Name of Maya attribute
        value (object, optional): Value of attribute. If none
            is provided, return all nodes with this attribute.

    Example:
        >> lsattr("id", "myId")
        ["myNode"]
        >> lsattr("id")
        ["myNode", "myOtherNode"]

    """

    if value is None:
        return cmds.ls("*.%s" % attr,
                       recursive=True,
                       objectsOnly=True,
                       long=True)
    return lsattrs({attr: value})


def lsattrs(attrs):
    """Return nodes with the given attribute(s).

    Arguments:
        attrs (dict): Name and value pairs of expected matches

    Example:
        >>> # Return nodes with an `age` of five.
        >>> lsattrs({"age": "five"})
        >>> # Return nodes with both `age` and `color` of five and blue.
        >>> lsattrs({"age": "five", "color": "blue"})

    Return:
         list: matching nodes.

    """

    dep_fn = OpenMaya.MFnDependencyNode()
    dag_fn = OpenMaya.MFnDagNode()
    selection_list = OpenMaya.MSelectionList()

    first_attr = next(iter(attrs))

    try:
        selection_list.add("*.{0}".format(first_attr),
                           searchChildNamespaces=True)
    except RuntimeError as exc:
        if str(exc).endswith("Object does not exist"):
            return []

    matches = set()
    for i in range(selection_list.length()):
        node = selection_list.getDependNode(i)
        if node.hasFn(OpenMaya.MFn.kDagNode):
            fn_node = dag_fn.setObject(node)
            full_path_names = [path.fullPathName()
                               for path in fn_node.getAllPaths()]
        else:
            fn_node = dep_fn.setObject(node)
            full_path_names = [fn_node.name()]

        for attr in attrs:
            try:
                plug = fn_node.findPlug(attr, True)
                if plug.asString() != attrs[attr]:
                    break
            except RuntimeError:
                break
        else:
            matches.update(full_path_names)

    return list(matches)


@contextlib.contextmanager
def attribute_values(attr_values):
    """Remaps node attributes to values during context.

    Arguments:
        attr_values (dict): Dictionary with (attr, value)

    """

    original = [(attr, cmds.getAttr(attr)) for attr in attr_values]
    try:
        for attr, value in attr_values.items():
            if isinstance(value, string_types):
                cmds.setAttr(attr, value, type="string")
            else:
                cmds.setAttr(attr, value)
        yield
    finally:
        for attr, value in original:
            if isinstance(value, string_types):
                cmds.setAttr(attr, value, type="string")
            elif value is None and cmds.getAttr(attr, type=True) == "string":
                # In some cases the maya.cmds.getAttr command returns None
                # for string attributes but this value cannot assigned.
                # Note: After setting it once to "" it will then return ""
                #       instead of None. So this would only happen once.
                cmds.setAttr(attr, "", type="string")
            else:
                cmds.setAttr(attr, value)


@contextlib.contextmanager
def keytangent_default(in_tangent_type='auto',
                       out_tangent_type='auto'):
    """Set the default keyTangent for new keys during this context"""

    original_itt = cmds.keyTangent(query=True, g=True, itt=True)[0]
    original_ott = cmds.keyTangent(query=True, g=True, ott=True)[0]
    cmds.keyTangent(g=True, itt=in_tangent_type)
    cmds.keyTangent(g=True, ott=out_tangent_type)
    try:
        yield
    finally:
        cmds.keyTangent(g=True, itt=original_itt)
        cmds.keyTangent(g=True, ott=original_ott)


@contextlib.contextmanager
def undo_chunk():
    """Open a undo chunk during context."""

    try:
        cmds.undoInfo(openChunk=True)
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def evaluation(mode="off"):
    """Set the evaluation manager during context.

    Arguments:
        mode (str): The mode to apply during context.
            "off": The standard DG evaluation (stable)
            "serial": A serial DG evaluation
            "parallel": The Maya 2016+ parallel evaluation

    """

    original = cmds.evaluationManager(query=True, mode=1)[0]
    try:
        cmds.evaluationManager(mode=mode)
        yield
    finally:
        cmds.evaluationManager(mode=original)


@contextlib.contextmanager
def empty_sets(sets, force=False):
    """Remove all members of the sets during the context"""

    assert isinstance(sets, (list, tuple))

    original = dict()
    original_connections = []

    # Store original state
    for obj_set in sets:
        members = cmds.sets(obj_set, query=True)
        original[obj_set] = members

    try:
        for obj_set in sets:
            cmds.sets(clear=obj_set)
            if force:
                # Break all connections if force is enabled, this way we
                # prevent Maya from exporting any reference nodes which are
                # connected with placeHolder[x] attributes
                plug = "%s.dagSetMembers" % obj_set
                connections = cmds.listConnections(plug,
                                                   source=True,
                                                   destination=False,
                                                   plugs=True,
                                                   connections=True) or []
                original_connections.extend(connections)
                for dest, src in pairwise(connections):
                    cmds.disconnectAttr(src, dest)
        yield
    finally:

        for dest, src in pairwise(original_connections):
            cmds.connectAttr(src, dest)

        # Restore original members
        _iteritems = getattr(original, "iteritems", original.items)
        for origin_set, members in _iteritems():
            cmds.sets(members, forceElement=origin_set)


@contextlib.contextmanager
def renderlayer(layer):
    """Set the renderlayer during the context

    Arguments:
        layer (str): Name of layer to switch to.

    """

    original = cmds.editRenderLayerGlobals(query=True,
                                           currentRenderLayer=True)

    try:
        cmds.editRenderLayerGlobals(currentRenderLayer=layer)
        yield
    finally:
        cmds.editRenderLayerGlobals(currentRenderLayer=original)


class delete_after(object):
    """Context Manager that will delete collected nodes after exit.

    This allows to ensure the nodes added to the context are deleted
    afterwards. This is useful if you want to ensure nodes are deleted
    even if an error is raised.

    Examples:
        with delete_after() as delete_bin:
            cube = maya.cmds.polyCube()
            delete_bin.extend(cube)
            # cube exists
        # cube deleted

    """

    def __init__(self, nodes=None):

        self._nodes = list()

        if nodes:
            self.extend(nodes)

    def append(self, node):
        self._nodes.append(node)

    def extend(self, nodes):
        self._nodes.extend(nodes)

    def __iter__(self):
        return iter(self._nodes)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._nodes:
            cmds.delete(self._nodes)


def get_current_renderlayer():
    return cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)


def get_renderer(layer):
    with renderlayer(layer):
        return cmds.getAttr("defaultRenderGlobals.currentRenderer")


@contextlib.contextmanager
def no_undo(flush=False):
    """Disable the undo queue during the context

    Arguments:
        flush (bool): When True the undo queue will be emptied when returning
            from the context losing all undo history. Defaults to False.

    """
    original = cmds.undoInfo(query=True, state=True)
    keyword = 'state' if flush else 'stateWithoutFlush'

    try:
        cmds.undoInfo(**{keyword: False})
        yield
    finally:
        cmds.undoInfo(**{keyword: original})


def get_shader_assignments_from_shapes(shapes, components=True):
    """Return the shape assignment per related shading engines.

    Returns a dictionary where the keys are shadingGroups and the values are
    lists of assigned shapes or shape-components.

    Since `maya.cmds.sets` returns shader members on the shapes as components
    on the transform we correct that in this method too.

    For the 'shapes' this will return a dictionary like:
        {
            "shadingEngineX": ["nodeX", "nodeY"],
            "shadingEngineY": ["nodeA", "nodeB"]
        }

    Args:
        shapes (list): The shapes to collect the assignments for.
        components (bool): Whether to include the component assignments.

    Returns:
        dict: The {shadingEngine: shapes} relationships

    """

    shapes = cmds.ls(shapes,
                     long=True,
                     shapes=True,
                     objectsOnly=True)
    if not shapes:
        return {}

    # Collect shading engines and their shapes
    assignments = defaultdict(list)
    for shape in shapes:

        # Get unique shading groups for the shape
        shading_groups = cmds.listConnections(shape,
                                              source=False,
                                              destination=True,
                                              plugs=False,
                                              connections=False,
                                              type="shadingEngine") or []
        shading_groups = list(set(shading_groups))
        for shading_group in shading_groups:
            assignments[shading_group].append(shape)

    if components:
        # Note: Components returned from maya.cmds.sets are "listed" as if
        # being assigned to the transform like: pCube1.f[0] as opposed
        # to pCubeShape1.f[0] so we correct that here too.

        # Build a mapping from parent to shapes to include in lookup.
        transforms = {shape.rsplit("|", 1)[0]: shape for shape in shapes}
        lookup = set(shapes) | set(transforms.keys())

        component_assignments = defaultdict(list)
        for shading_group in assignments.keys():
            members = cmds.ls(cmds.sets(shading_group, query=True), long=True)
            for member in members:

                node = member.split(".", 1)[0]
                if node not in lookup:
                    continue

                # Component
                if "." in member:

                    # Fix transform to shape as shaders are assigned to shapes
                    if node in transforms:
                        shape = transforms[node]
                        component = member.split(".", 1)[1]
                        member = "{0}.{1}".format(shape, component)

                component_assignments[shading_group].append(member)
        assignments = component_assignments

    return dict(assignments)


@contextlib.contextmanager
def shader(nodes, shadingEngine="initialShadingGroup"):
    """Assign a shader to nodes during the context"""

    shapes = cmds.ls(nodes, dag=1, objectsOnly=1, shapes=1, long=1)
    original = get_shader_assignments_from_shapes(shapes)

    try:
        # Assign override shader
        if shapes:
            cmds.sets(shapes, edit=True, forceElement=shadingEngine)
        yield
    finally:

        # Assign original shaders
        for sg, members in original.items():
            if members:
                cmds.sets(members, edit=True, forceElement=sg)


@contextlib.contextmanager
def displaySmoothness(nodes,
                      divisionsU=0,
                      divisionsV=0,
                      pointsWire=4,
                      pointsShaded=1,
                      polygonObject=1):
    """Set the displaySmoothness during the context"""

    # Ensure only non-intermediate shapes
    nodes = cmds.ls(nodes,
                    dag=1,
                    shapes=1,
                    long=1,
                    noIntermediate=True)

    def parse(node):
        """Parse the current state of a node"""
        state = {}
        for key in ["divisionsU",
                    "divisionsV",
                    "pointsWire",
                    "pointsShaded",
                    "polygonObject"]:
            value = cmds.displaySmoothness(node, query=1, **{key: True})
            if value is not None:
                state[key] = value[0]
        return state

    originals = dict((node, parse(node)) for node in nodes)

    try:
        # Apply current state
        cmds.displaySmoothness(nodes,
                               divisionsU=divisionsU,
                               divisionsV=divisionsV,
                               pointsWire=pointsWire,
                               pointsShaded=pointsShaded,
                               polygonObject=polygonObject)
        yield
    finally:
        # Revert state
        _iteritems = getattr(originals, "iteritems", originals.items)
        for node, state in _iteritems():
            if state:
                cmds.displaySmoothness(node, **state)


@contextlib.contextmanager
def no_display_layers(nodes):
    """Ensure nodes are not in a displayLayer during context.

    Arguments:
        nodes (list): The nodes to remove from any display layer.

    """

    # Ensure long names
    nodes = cmds.ls(nodes, long=True)

    # Get the original state
    lookup = set(nodes)
    original = {}
    for layer in cmds.ls(type='displayLayer'):

        # Skip default layer
        if layer == "defaultLayer":
            continue

        members = cmds.editDisplayLayerMembers(layer,
                                               query=True,
                                               fullNames=True)
        if not members:
            continue
        members = set(members)

        included = lookup.intersection(members)
        if included:
            original[layer] = list(included)

    try:
        # Add all nodes to default layer
        cmds.editDisplayLayerMembers("defaultLayer", nodes, noRecurse=True)
        yield
    finally:
        # Restore original members
        _iteritems = getattr(original, "iteritems", original.items)
        for layer, members in _iteritems():
            cmds.editDisplayLayerMembers(layer, members, noRecurse=True)


@contextlib.contextmanager
def namespaced(namespace, new=True, relative_names=None):
    """Work inside namespace during context

    Args:
        new (bool): When enabled this will rename the namespace to a unique
            namespace if the input namespace already exists.

    Yields:
        str: The namespace that is used during the context

    """
    original = cmds.namespaceInfo(cur=True, absoluteName=True)
    original_relative_names = cmds.namespace(query=True, relativeNames=True)
    if new:
        namespace = unique_namespace(namespace)
        cmds.namespace(add=namespace)
    if relative_names is not None:
        cmds.namespace(relativeNames=relative_names)
    try:
        cmds.namespace(set=namespace)
        yield namespace
    finally:
        cmds.namespace(set=original)
        if relative_names is not None:
            cmds.namespace(relativeNames=original_relative_names)


@contextlib.contextmanager
def maintained_selection_api():
    """Maintain selection using the Maya Python API.

    Warning: This is *not* added to the undo stack.

    """
    original = OpenMaya.MGlobal.getActiveSelectionList()
    try:
        yield
    finally:
        OpenMaya.MGlobal.setActiveSelectionList(original)


@contextlib.contextmanager
def tool(context):
    """Set a tool context during the context manager.

    """
    original = cmds.currentCtx()
    try:
        cmds.setToolTo(context)
        yield
    finally:
        cmds.setToolTo(original)


def polyConstraint(components, *args, **kwargs):
    """Return the list of *components* with the constraints applied.

    A wrapper around Maya's `polySelectConstraint` to retrieve its results as
    a list without altering selections. For a list of possible constraints
    see `maya.cmds.polySelectConstraint` documentation.

    Arguments:
        components (list): List of components of polygon meshes

    Returns:
        list: The list of components filtered by the given constraints.

    """

    kwargs.pop('mode', None)

    with no_undo(flush=False):
        # Reverting selection to the original selection using
        # `maya.cmds.select` can be slow in rare cases where previously
        # `maya.cmds.polySelectConstraint` had set constrain to "All and Next"
        # and the "Random" setting was activated. To work around this we
        # revert to the original selection using the Maya API. This is safe
        # since we're not generating any undo change anyway.
        with tool("selectSuperContext"):
            # Selection can be very slow when in a manipulator mode.
            # So we force the selection context which is fast.
            with maintained_selection_api():
                # Apply constraint using mode=2 (current and next) so
                # it applies to the selection made before it; because just
                # a `maya.cmds.select()` call will not trigger the constraint.
                with reset_polySelectConstraint():
                    cmds.select(components, r=1, noExpand=True)
                    cmds.polySelectConstraint(*args, mode=2, **kwargs)
                    result = cmds.ls(selection=True)
                    cmds.select(clear=True)
                    return result


@contextlib.contextmanager
def reset_polySelectConstraint(reset=True):
    """Context during which the given polyConstraint settings are disabled.

    The original settings are restored after the context.

    """

    original = cmds.polySelectConstraint(query=True, stateString=True)

    try:
        if reset:
            # Ensure command is available in mel
            # This can happen when running standalone
            if not mel.eval("exists resetPolySelectConstraint"):
                mel.eval("source polygonConstraint")

            # Reset all parameters
            mel.eval("resetPolySelectConstraint;")
        cmds.polySelectConstraint(disable=True)
        yield
    finally:
        mel.eval(original)


def is_visible(node,
               displayLayer=True,
               intermediateObject=True,
               parentHidden=True,
               visibility=True):
    """Is `node` visible?

    Returns whether a node is hidden by one of the following methods:
    - The node exists (always checked)
    - The node must be a dagNode (always checked)
    - The node's visibility is off.
    - The node is set as intermediate Object.
    - The node is in a disabled displayLayer.
    - Whether any of its parent nodes is hidden.

    Roughly based on: http://ewertb.soundlinker.com/mel/mel.098.php

    Returns:
        bool: Whether the node is visible in the scene

    """

    # Only existing objects can be visible
    if not cmds.objExists(node):
        return False

    # Only dagNodes can be visible
    if not cmds.objectType(node, isAType='dagNode'):
        return False

    if visibility:
        if not cmds.getAttr('{0}.visibility'.format(node)):
            return False

    if intermediateObject and cmds.objectType(node, isAType='shape'):
        if cmds.getAttr('{0}.intermediateObject'.format(node)):
            return False

    if displayLayer:
        # Display layers set overrideEnabled and overrideVisibility on members
        if cmds.attributeQuery('overrideEnabled', node=node, exists=True):
            override_enabled = cmds.getAttr('{}.overrideEnabled'.format(node))
            override_visibility = cmds.getAttr('{}.overrideVisibility'.format(
                node))
            if override_enabled and override_visibility:
                return False

    if parentHidden:
        parents = cmds.listRelatives(node, parent=True, fullPath=True)
        if parents:
            parent = parents[0]
            if not is_visible(parent,
                              displayLayer=displayLayer,
                              intermediateObject=False,
                              parentHidden=parentHidden,
                              visibility=visibility):
                return False

    return True


def extract_alembic(file,
                    startFrame=None,
                    endFrame=None,
                    selection=True,
                    uvWrite=True,
                    eulerFilter=True,
                    dataFormat="ogawa",
                    verbose=False,
                    **kwargs):
    """Extract a single Alembic Cache.

    This extracts an Alembic cache using the `-selection` flag to minimize
    the extracted content to solely what was Collected into the instance.

    Arguments:

        startFrame (float): Start frame of output. Ignored if `frameRange`
            provided.

        endFrame (float): End frame of output. Ignored if `frameRange`
            provided.

        frameRange (tuple or str): Two-tuple with start and end frame or a
            string formatted as: "startFrame endFrame". This argument
            overrides `startFrame` and `endFrame` arguments.

        dataFormat (str): The data format to use for the cache,
                          defaults to "ogawa"

        verbose (bool): When on, outputs frame number information to the
            Script Editor or output window during extraction.

        noNormals (bool): When on, normal data from the original polygon
            objects is not included in the exported Alembic cache file.

        renderableOnly (bool): When on, any non-renderable nodes or hierarchy,
            such as hidden objects, are not included in the Alembic file.
            Defaults to False.

        stripNamespaces (bool): When on, any namespaces associated with the
            exported objects are removed from the Alembic file. For example, an
            object with the namespace taco:foo:bar appears as bar in the
            Alembic file.

        uvWrite (bool): When on, UV data from polygon meshes and subdivision
            objects are written to the Alembic file. Only the current UV map is
            included.

        worldSpace (bool): When on, the top node in the node hierarchy is
            stored as world space. By default, these nodes are stored as local
            space. Defaults to False.

        eulerFilter (bool): When on, X, Y, and Z rotation data is filtered with
            an Euler filter. Euler filtering helps resolve irregularities in
            rotations especially if X, Y, and Z rotations exceed 360 degrees.
            Defaults to True.

    """

    # Ensure alembic exporter is loaded
    cmds.loadPlugin('AbcExport', quiet=True)

    # Alembic Exporter requires forward slashes
    file = file.replace('\\', '/')

    # Pass the start and end frame on as `frameRange` so that it
    # never conflicts with that argument
    if "frameRange" not in kwargs:
        # Fallback to maya timeline if no start or end frame provided.
        if startFrame is None:
            startFrame = cmds.playbackOptions(query=True,
                                              animationStartTime=True)
        if endFrame is None:
            endFrame = cmds.playbackOptions(query=True,
                                            animationEndTime=True)

        # Ensure valid types are converted to frame range
        assert isinstance(startFrame, _alembic_options["startFrame"])
        assert isinstance(endFrame, _alembic_options["endFrame"])
        kwargs["frameRange"] = "{0} {1}".format(startFrame, endFrame)
    else:
        # Allow conversion from tuple for `frameRange`
        frame_range = kwargs["frameRange"]
        if isinstance(frame_range, (list, tuple)):
            assert len(frame_range) == 2
            kwargs["frameRange"] = "{0} {1}".format(frame_range[0],
                                                    frame_range[1])

    # Assemble options
    options = {
        "selection": selection,
        "uvWrite": uvWrite,
        "eulerFilter": eulerFilter,
        "dataFormat": dataFormat
    }
    options.update(kwargs)

    # Validate options
    for key, value in options.copy().items():

        # Discard unknown options
        if key not in _alembic_options:
            log.warning("extract_alembic() does not support option '%s'. "
                        "Flag will be ignored..", key)
            options.pop(key)
            continue

        # Validate value type
        valid_types = _alembic_options[key]
        if not isinstance(value, valid_types):
            raise TypeError("Alembic option unsupported type: "
                            "{0} (expected {1})".format(value, valid_types))

        # Ignore empty values, like an empty string, since they mess up how
        # job arguments are built
        if isinstance(value, (list, tuple)):
            value = [x for x in value if x.strip()]

            # Ignore option completely if no values remaining
            if not value:
                options.pop(key)
                continue

            options[key] = value

    # The `writeCreases` argument was changed to `autoSubd` in Maya 2018+
    maya_version = int(cmds.about(version=True))
    if maya_version >= 2018:
        options['autoSubd'] = options.pop('writeCreases', False)

    # Format the job string from options
    job_args = list()
    for key, value in options.items():
        if isinstance(value, (list, tuple)):
            for entry in value:
                job_args.append("-{} {}".format(key, entry))
        elif isinstance(value, bool):
            # Add only when state is set to True
            if value:
                job_args.append("-{0}".format(key))
        else:
            job_args.append("-{0} {1}".format(key, value))

    job_str = " ".join(job_args)
    job_str += ' -file "%s"' % file

    # Ensure output directory exists
    parent_dir = os.path.dirname(file)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    if verbose:
        log.debug("Preparing Alembic export with options: %s",
                  json.dumps(options, indent=4))
        log.debug("Extracting Alembic with job arguments: %s", job_str)

    # Perform extraction
    print("Alembic Job Arguments : {}".format(job_str))

    # Disable the parallel evaluation temporarily to ensure no buggy
    # exports are made. (PLN-31)
    # TODO: Make sure this actually fixes the issues
    with evaluation("off"):
        cmds.AbcExport(j=job_str, verbose=verbose)

    if verbose:
        log.debug("Extracted Alembic to: %s", file)

    return file


# region ID
def get_id_required_nodes(referenced_nodes=False, nodes=None):
    """Filter out any node which are locked (reference) or readOnly

    Args:
        referenced_nodes (bool): set True to filter out reference nodes
        nodes (list, Optional): nodes to consider
    Returns:
        nodes (set): list of filtered nodes
    """

    lookup = None
    if nodes is None:
        # Consider all nodes
        nodes = cmds.ls()
    else:
        # Build a lookup for the only allowed nodes in output based
        # on `nodes` input of the function (+ ensure long names)
        lookup = set(cmds.ls(nodes, long=True))

    def _node_type_exists(node_type):
        try:
            cmds.nodeType(node_type, isTypeName=True)
            return True
        except RuntimeError:
            return False

    # `readOnly` flag is obsolete as of Maya 2016 therefore we explicitly
    # remove default nodes and reference nodes
    camera_shapes = ["frontShape", "sideShape", "topShape", "perspShape"]

    ignore = set()
    if not referenced_nodes:
        ignore |= set(cmds.ls(long=True, referencedNodes=True))

    # list all defaultNodes to filter out from the rest
    ignore |= set(cmds.ls(long=True, defaultNodes=True))
    ignore |= set(cmds.ls(camera_shapes, long=True))

    # Remove Turtle from the result of `cmds.ls` if Turtle is loaded
    # TODO: This should be a less specific check for a single plug-in.
    if _node_type_exists("ilrBakeLayer"):
        ignore |= set(cmds.ls(type="ilrBakeLayer", long=True))

    # Establish set of nodes types to include
    types = ["objectSet", "file", "mesh", "nurbsCurve", "nurbsSurface"]

    # Check if plugin nodes are available for Maya by checking if the plugin
    # is loaded
    if cmds.pluginInfo("pgYetiMaya", query=True, loaded=True):
        types.append("pgYetiMaya")

    # We *always* ignore intermediate shapes, so we filter them out directly
    nodes = cmds.ls(nodes, type=types, long=True, noIntermediate=True)

    # The items which need to pass the id to their parent
    # Add the collected transform to the nodes
    dag = cmds.ls(nodes, type="dagNode", long=True)  # query only dag nodes
    transforms = cmds.listRelatives(dag,
                                    parent=True,
                                    fullPath=True) or []

    nodes = set(nodes)
    nodes |= set(transforms)

    nodes -= ignore  # Remove the ignored nodes
    if not nodes:
        return nodes

    # Ensure only nodes from the input `nodes` are returned when a
    # filter was applied on function call because we also iterated
    # to parents and alike
    if lookup is not None:
        nodes &= lookup

    # Avoid locked nodes
    nodes_list = list(nodes)
    locked = cmds.lockNode(nodes_list, query=True, lock=True)
    for node, lock in zip(nodes_list, locked):
        if lock:
            log.warning("Skipping locked node: %s" % node)
            nodes.remove(node)

    return nodes


def get_id(node):
    """Get the `cbId` attribute of the given node.

    Args:
        node (str): the name of the node to retrieve the attribute from
    Returns:
        str

    """
    if node is None:
        return

    sel = OpenMaya.MSelectionList()
    sel.add(node)

    api_node = sel.getDependNode(0)
    fn = OpenMaya.MFnDependencyNode(api_node)

    if not fn.hasAttribute("cbId"):
        return

    try:
        return fn.findPlug("cbId", False).asString()
    except RuntimeError:
        log.warning("Failed to retrieve cbId on %s", node)
        return


def generate_ids(nodes, asset_id=None):
    """Returns new unique ids for the given nodes.

    Note: This does not assign the new ids, it only generates the values.

    To assign new ids using this method:
    >>> nodes = ["a", "b", "c"]
    >>> for node, id in generate_ids(nodes):
    >>>     set_id(node, id)

    To also override any existing values (and assign regenerated ids):
    >>> nodes = ["a", "b", "c"]
    >>> for node, id in generate_ids(nodes):
    >>>     set_id(node, id, overwrite=True)

    Args:
        nodes (list): List of nodes.
        asset_id (str or bson.ObjectId): The database id for the *asset* to
            generate for. When None provided the current asset in the
            active session is used.

    Returns:
        list: A list of (node, id) tuples.

    """

    if asset_id is None:
        # Get the asset ID from the database for the asset of current context
        project_name = get_current_project_name()
        asset_name = get_current_asset_name()
        asset_doc = get_asset_by_name(project_name, asset_name, fields=["_id"])
        assert asset_doc, "No current asset found in Session"
        asset_id = asset_doc['_id']

    node_ids = []
    for node in nodes:
        _, uid = str(uuid.uuid4()).rsplit("-", 1)
        unique_id = "{}:{}".format(asset_id, uid)
        node_ids.append((node, unique_id))

    return node_ids


def set_id(node, unique_id, overwrite=False):
    """Add cbId to `node` unless one already exists.

    Args:
        node (str): the node to add the "cbId" on
        unique_id (str): The unique node id to assign.
            This should be generated by `generate_ids`.
        overwrite (bool, optional): When True overrides the current value even
            if `node` already has an id. Defaults to False.

    Returns:
        None

    """

    exists = cmds.attributeQuery("cbId", node=node, exists=True)

    # Add the attribute if it does not exist yet
    if not exists:
        cmds.addAttr(node, longName="cbId", dataType="string")

    # Set the value
    if not exists or overwrite:
        attr = "{0}.cbId".format(node)
        cmds.setAttr(attr, unique_id, type="string")


def get_attribute(plug,
                  asString=False,
                  expandEnvironmentVariables=False,
                  **kwargs):
    """Maya getAttr with some fixes based on `pymel.core.general.getAttr()`.

    Like Pymel getAttr this applies some changes to `maya.cmds.getAttr`
      - maya pointlessly returned vector results as a tuple wrapped in a list
        (ex.  '[(1,2,3)]'). This command unpacks the vector for you.
      - when getting a multi-attr, maya would raise an error, but this will
        return a list of values for the multi-attr
      - added support for getting message attributes by returning the
        connections instead

    Note that the asString + expandEnvironmentVariables argument naming
    convention matches the `maya.cmds.getAttr` arguments so that it can
    act as a direct replacement for it.

    Args:
        plug (str): Node's attribute plug as `node.attribute`
        asString (bool): Return string value for enum attributes instead
            of the index. Note that the return value can be dependent on the
            UI language Maya is running in.
        expandEnvironmentVariables (bool): Expand any environment variable and
            (tilde characters on UNIX) found in string attributes which are
            returned.

    Kwargs:
        Supports the keyword arguments of `maya.cmds.getAttr`

    Returns:
        object: The value of the maya attribute.

    """
    attr_type = cmds.getAttr(plug, type=True)
    if asString:
        kwargs["asString"] = True
    if expandEnvironmentVariables:
        kwargs["expandEnvironmentVariables"] = True
    try:
        res = cmds.getAttr(plug, **kwargs)
    except RuntimeError:
        if attr_type == "message":
            return cmds.listConnections(plug)

        node, attr = plug.split(".", 1)
        children = cmds.attributeQuery(attr, node=node, listChildren=True)
        if children:
            return [
                get_attribute("{}.{}".format(node, child))
                for child in children
            ]

        raise

    # Convert vector result wrapped in tuple
    if isinstance(res, list) and len(res):
        if isinstance(res[0], tuple) and len(res):
            if attr_type in {'pointArray', 'vectorArray'}:
                return res
            return res[0]

    return res


def set_attribute(attribute, value, node):
    """Adjust attributes based on the value from the attribute data

    If an attribute does not exists on the target it will be added with
    the dataType being controlled by the value type.

    Args:
        attribute (str): name of the attribute to change
        value: the value to change to attribute to
        node (str): name of the node

    Returns:
        None
    """

    value_type = type(value).__name__
    kwargs = ATTRIBUTE_DICT[value_type]
    if not cmds.attributeQuery(attribute, node=node, exists=True):
        log.debug("Creating attribute '{}' on "
                  "'{}'".format(attribute, node))
        cmds.addAttr(node, longName=attribute, **kwargs)

    node_attr = "{}.{}".format(node, attribute)
    enum_type = cmds.attributeQuery(attribute, node=node, enum=True)
    if enum_type and value_type == "str":
        enum_string_values = cmds.attributeQuery(
            attribute, node=node, listEnum=True
        )[0].split(":")
        cmds.setAttr(
            "{}.{}".format(node, attribute), enum_string_values.index(value)
        )
    elif "dataType" in kwargs:
        attr_type = kwargs["dataType"]
        cmds.setAttr(node_attr, value, type=attr_type)
    else:
        cmds.setAttr(node_attr, value)


def apply_attributes(attributes, nodes_by_id):
    """Alter the attributes to match the state when publishing

    Apply attribute settings from the publish to the node in the scene based
    on the UUID which is stored in the cbId attribute.

    Args:
        attributes (list): list of dictionaries
        nodes_by_id (dict): collection of nodes based on UUID
                           {uuid: [node, node]}

    """

    for attr_data in attributes:
        nodes = nodes_by_id[attr_data["uuid"]]
        attr_value = attr_data["attributes"]
        for node in nodes:
            for attr, value in attr_value.items():
                set_attribute(attr, value, node)


def get_container_members(container):
    """Returns the members of a container.
    This includes the nodes from any loaded references in the container.
    """
    if isinstance(container, dict):
        # Assume it's a container dictionary
        container = container["objectName"]

    members = cmds.sets(container, query=True) or []
    members = cmds.ls(members, long=True, objectsOnly=True) or []
    all_members = set(members)

    # Include any referenced nodes from any reference in the container
    # This is required since we've removed adding ALL nodes of a reference
    # into the container set and only add the reference node now.
    for ref in cmds.ls(members, exactType="reference", objectsOnly=True):

        # Ignore any `:sharedReferenceNode`
        if ref.rsplit(":", 1)[-1].startswith("sharedReferenceNode"):
            continue

        # Ignore _UNKNOWN_REF_NODE_ (PLN-160)
        if ref.rsplit(":", 1)[-1].startswith("_UNKNOWN_REF_NODE_"):
            continue

        reference_members = cmds.referenceQuery(ref, nodes=True, dagPath=True)
        reference_members = cmds.ls(reference_members,
                                    long=True,
                                    objectsOnly=True)
        all_members.update(reference_members)

    return list(all_members)


# region LOOKDEV
def list_looks(project_name, asset_id):
    """Return all look subsets for the given asset

    This assumes all look subsets start with "look*" in their names.
    """
    # # get all subsets with look leading in
    # the name associated with the asset
    # TODO this should probably look for family 'look' instead of checking
    #   subset name that can not start with family
    subset_docs = get_subsets(project_name, asset_ids=[asset_id])
    return [
        subset_doc
        for subset_doc in subset_docs
        if subset_doc["name"].startswith("look")
    ]


def assign_look_by_version(nodes, version_id):
    """Assign nodes a specific published look version by id.

    This assumes the nodes correspond with the asset.

    Args:
        nodes(list): nodes to assign look to
        version_id (bson.ObjectId): database id of the version

    Returns:
        None
    """

    project_name = get_current_project_name()

    # Get representations of shader file and relationships
    look_representation = get_representation_by_name(
        project_name, "ma", version_id
    )
    json_representation = get_representation_by_name(
        project_name, "json", version_id
    )

    # See if representation is already loaded, if so reuse it.
    host = registered_host()
    representation_id = str(look_representation['_id'])
    for container in host.ls():
        if (container['loader'] == "LookLoader" and
                container['representation'] == representation_id):
            log.info("Reusing loaded look ..")
            container_node = container['objectName']
            break
    else:
        log.info("Using look for the first time ..")

        # Load file
        _loaders = discover_loader_plugins()
        loaders = loaders_from_representation(_loaders, representation_id)
        Loader = next((i for i in loaders if i.__name__ == "LookLoader"), None)
        if Loader is None:
            raise RuntimeError("Could not find LookLoader, this is a bug")

        # Reference the look file
        with maintained_selection():
            container_node = load_container(Loader, look_representation)

    # Get container members
    shader_nodes = get_container_members(container_node)

    # Load relationships
    shader_relation = get_representation_path(json_representation)
    with open(shader_relation, "r") as f:
        relationships = json.load(f)

    # Assign relationships
    apply_shaders(relationships, shader_nodes, nodes)


def assign_look(nodes, subset="lookDefault"):
    """Assigns a look to a node.

    Optimizes the nodes by grouping by asset id and finding
    related subset by name.

    Args:
        nodes (list): all nodes to assign the look to
        subset (str): name of the subset to find
    """

    # Group all nodes per asset id
    grouped = defaultdict(list)
    for node in nodes:
        pype_id = get_id(node)
        if not pype_id:
            continue

        parts = pype_id.split(":", 1)
        grouped[parts[0]].append(node)

    project_name = get_current_project_name()
    subset_docs = get_subsets(
        project_name, subset_names=[subset], asset_ids=grouped.keys()
    )
    subset_docs_by_asset_id = {
        str(subset_doc["parent"]): subset_doc
        for subset_doc in subset_docs
    }
    subset_ids = {
        subset_doc["_id"]
        for subset_doc in subset_docs_by_asset_id.values()
    }
    last_version_docs = get_last_versions(
        project_name,
        subset_ids=subset_ids,
        fields=["_id", "name", "data.families"]
    )
    last_version_docs_by_subset_id = {
        last_version_doc["parent"]: last_version_doc
        for last_version_doc in last_version_docs
    }

    for asset_id, asset_nodes in grouped.items():
        # create objectId for database
        subset_doc = subset_docs_by_asset_id.get(asset_id)
        if not subset_doc:
            log.warning("No subset '{}' found for {}".format(subset, asset_id))
            continue

        last_version = last_version_docs_by_subset_id.get(subset_doc["_id"])
        if not last_version:
            log.warning((
                "Not found last version for subset '{}' on asset with id {}"
            ).format(subset, asset_id))
            continue

        families = last_version.get("data", {}).get("families") or []
        if "look" not in families:
            log.warning((
                "Last version for subset '{}' on asset with id {}"
                " does not have look family"
            ).format(subset, asset_id))
            continue

        log.debug("Assigning look '{}' <v{:03d}>".format(
            subset, last_version["name"]))

        assign_look_by_version(asset_nodes, last_version["_id"])


def apply_shaders(relationships, shadernodes, nodes):
    """Link shadingEngine to the right nodes based on relationship data

    Relationship data is constructed of a collection of `sets` and `attributes`
    `sets` corresponds with the shaderEngines found in the lookdev.
    Each set has the keys `name`, `members` and `uuid`, the `members`
    hold a collection of node information `name` and `uuid`.

    Args:
        relationships (dict): relationship data
        shadernodes (list): list of nodes of the shading objectSets (includes
        VRayObjectProperties and shadingEngines)
        nodes (list): list of nodes to apply shader to

    Returns:
        None
    """

    attributes = relationships.get("attributes", [])
    shader_data = relationships.get("relationships", {})

    shading_engines = cmds.ls(shadernodes, type="objectSet", long=True)
    assert shading_engines, "Error in retrieving objectSets from reference"

    # region compute lookup
    nodes_by_id = defaultdict(list)
    for node in nodes:
        nodes_by_id[get_id(node)].append(node)

    shading_engines_by_id = defaultdict(list)
    for shad in shading_engines:
        shading_engines_by_id[get_id(shad)].append(shad)
    # endregion

    # region assign shading engines and other sets
    for data in shader_data.values():
        # collect all unique IDs of the set members
        shader_uuid = data["uuid"]
        member_uuids = [member["uuid"] for member in data["members"]]

        filtered_nodes = list()
        for m_uuid in member_uuids:
            filtered_nodes.extend(nodes_by_id[m_uuid])

        id_shading_engines = shading_engines_by_id[shader_uuid]
        if not id_shading_engines:
            log.error("No shader found with cbId "
                      "'{}'".format(shader_uuid))
            continue
        elif len(id_shading_engines) > 1:
            log.error("Skipping shader assignment. "
                      "More than one shader found with cbId "
                      "'{}'. (found: {})".format(shader_uuid,
                                                 id_shading_engines))
            continue

        if not filtered_nodes:
            log.warning("No nodes found for shading engine "
                        "'{0}'".format(id_shading_engines[0]))
            continue
        try:
            cmds.sets(filtered_nodes, forceElement=id_shading_engines[0])
        except RuntimeError as rte:
            log.error("Error during shader assignment: {}".format(rte))

    # endregion

    apply_attributes(attributes, nodes_by_id)


# endregion LOOKDEV
def get_isolate_view_sets():
    """Return isolate view sets of all modelPanels.

    Returns:
        list: all sets related to isolate view

    """

    view_sets = set()
    for panel in cmds.getPanel(type="modelPanel") or []:
        view_set = cmds.modelEditor(panel, query=True, viewObjects=True)
        if view_set:
            view_sets.add(view_set)

    return view_sets


def get_related_sets(node):
    """Return objectSets that are relationships for a look for `node`.

    Filters out based on:
    - id attribute is NOT `pyblish.avalon.container`
    - shapes and deformer shapes (alembic creates meshShapeDeformed)
    - set name ends with any from a predefined list
    - set in not in viewport set (isolate selected for example)

    Args:
        node (str): name of the current node to check

    Returns:
        list: The related sets

    """

    # Ignore specific suffices
    ignore_suffices = ["out_SET", "controls_SET", "_INST", "_CON"]

    # Default nodes to ignore
    defaults = {"defaultLightSet", "defaultObjectSet"}

    # Ids to ignore
    ignored = {"pyblish.avalon.instance", "pyblish.avalon.container"}

    view_sets = get_isolate_view_sets()

    sets = cmds.listSets(object=node, extendToShape=False)
    if not sets:
        return []

    # Fix 'no object matches name' errors on nodes returned by listSets.
    # In rare cases it can happen that a node is added to an internal maya
    # set inaccessible by maya commands, for example check some nodes
    # returned by `cmds.listSets(allSets=True)`
    sets = cmds.ls(sets)

    # Ignore `avalon.container`
    sets = [s for s in sets if
            not cmds.attributeQuery("id", node=s, exists=True) or
            not cmds.getAttr("%s.id" % s) in ignored]

    # Exclude deformer sets (`type=2` for `maya.cmds.listSets`)
    deformer_sets = cmds.listSets(object=node,
                                  extendToShape=False,
                                  type=2) or []
    deformer_sets = set(deformer_sets)  # optimize lookup
    sets = [s for s in sets if s not in deformer_sets]

    # Ignore when the set has a specific suffix
    sets = [s for s in sets if not any(s.endswith(x) for x in ignore_suffices)]

    # Ignore viewport filter view sets (from isolate select and
    # viewports)
    sets = [s for s in sets if s not in view_sets]
    sets = [s for s in sets if s not in defaults]

    return sets


def get_container_transforms(container, members=None, root=False):
    """Retrieve the root node of the container content

    When a container is created through a Loader the content
    of the file will be grouped under a transform. The name of the root
    transform is stored in the container information

    Args:
        container (dict): the container
        members (list): optional and convenience argument
        root (bool): return highest node in hierarchy if True

    Returns:
        root (list / str):
    """

    if not members:
        members = get_container_members(container)

    results = cmds.ls(members, type="transform", long=True)
    if root:
        root = get_highest_in_hierarchy(results)
        if root:
            results = root[0]

    return results


def get_highest_in_hierarchy(nodes):
    """Return highest nodes in the hierarchy that are in the `nodes` list.

    The "highest in hierarchy" are the nodes closest to world: top-most level.

    Args:
        nodes (list): The nodes in which find the highest in hierarchies.

    Returns:
        list: The highest nodes from the input nodes.

    """

    # Ensure we use long names
    nodes = cmds.ls(nodes, long=True)
    lookup = set(nodes)

    highest = []
    for node in nodes:
        # If no parents are within the nodes input list
        # then this is a highest node
        if not any(n in lookup for n in iter_parents(node)):
            highest.append(node)

    return highest


def iter_parents(node):
    """Iter parents of node from its long name.

    Note: The `node` *must* be the long node name.

    Args:
        node (str): Node long name.

    Yields:
        str: All parent node names (long names)

    """
    while True:
        split = node.rsplit("|", 1)
        if len(split) == 1 or not split[0]:
            return

        node = split[0]
        yield node


def remove_other_uv_sets(mesh):
    """Remove all other UV sets than the current UV set.

    Keep only current UV set and ensure it's the renamed to default 'map1'.

    """

    uvSets = cmds.polyUVSet(mesh, query=True, allUVSets=True)
    current = cmds.polyUVSet(mesh, query=True, currentUVSet=True)[0]

    # Copy over to map1
    if current != 'map1':
        cmds.polyUVSet(mesh, uvSet=current, newUVSet='map1', copy=True)
        cmds.polyUVSet(mesh, currentUVSet=True, uvSet='map1')
        current = 'map1'

    # Delete all non-current UV sets
    deleteUVSets = [uvSet for uvSet in uvSets if uvSet != current]
    uvSet = None

    # Maya Bug (tested in 2015/2016):
    # In some cases the API's MFnMesh will report less UV sets than
    # maya.cmds.polyUVSet. This seems to happen when the deletion of UV sets
    # has not triggered a cleanup of the UVSet array attribute on the mesh
    # node. It will still have extra entries in the attribute, though it will
    # not show up in API or UI. Nevertheless it does show up in
    # maya.cmds.polyUVSet. To ensure we clean up the array we'll force delete
    # the extra remaining 'indices' that we don't want.

    # TODO: Implement a better fix
    # The best way to fix would be to get the UVSet indices from api with
    # MFnMesh (to ensure we keep correct ones) and then only force delete the
    # other entries in the array attribute on the node. But for now we're
    # deleting all entries except first one. Note that the first entry could
    # never be removed (the default 'map1' always exists and is supposed to
    # be undeletable.)
    try:
        for uvSet in deleteUVSets:
            cmds.polyUVSet(mesh, delete=True, uvSet=uvSet)
    except RuntimeError as exc:
        log.warning('Error uvSet: %s - %s', uvSet, exc)
        indices = cmds.getAttr('{0}.uvSet'.format(mesh),
                               multiIndices=True)
        if not indices:
            log.warning("No uv set found indices for: %s", mesh)
            return

        # Delete from end to avoid shifting indices
        # and remove the indices in the attribute
        indices = reversed(indices[1:])
        for i in indices:
            attr = '{0}.uvSet[{1}]'.format(mesh, i)
            cmds.removeMultiInstance(attr, b=True)


def get_node_parent(node):
    """Return full path name for parent of node"""
    parents = cmds.listRelatives(node, parent=True, fullPath=True)
    return parents[0] if parents else None


def get_id_from_sibling(node, history_only=True):
    """Return first node id in the history chain that matches this node.

    The nodes in history must be of the exact same node type and must be
    parented under the same parent.

    Optionally, if no matching node is found from the history, all the
    siblings of the node that are of the same type are checked.
    Additionally to having the same parent, the sibling must be marked as
    'intermediate object'.

    Args:
        node (str): node to retrieve the history from
        history_only (bool): if True and if nothing found in history,
            look for an 'intermediate object' in all the node's siblings
            of same type

    Returns:
        str or None: The id from the sibling node or None when no id found
            on any valid nodes in the history or siblings.

    """

    node = cmds.ls(node, long=True)[0]

    # Find all similar nodes in history
    history = cmds.listHistory(node)
    node_type = cmds.nodeType(node)
    similar_nodes = cmds.ls(history, exactType=node_type, long=True)

    # Exclude itself
    similar_nodes = [x for x in similar_nodes if x != node]

    # The node *must be* under the same parent
    parent = get_node_parent(node)
    similar_nodes = [i for i in similar_nodes if get_node_parent(i) == parent]

    # Check all of the remaining similar nodes and take the first one
    # with an id and assume it's the original.
    for similar_node in similar_nodes:
        _id = get_id(similar_node)
        if _id:
            return _id

    if not history_only:
        # Get siblings of same type
        similar_nodes = cmds.listRelatives(parent,
                                           type=node_type,
                                           fullPath=True)
        similar_nodes = cmds.ls(similar_nodes, exactType=node_type, long=True)

        # Exclude itself
        similar_nodes = [x for x in similar_nodes if x != node]

        # Get all unique ids from siblings in order since
        # we consistently take the first one found
        sibling_ids = OrderedDict()
        for similar_node in similar_nodes:
            # Check if "intermediate object"
            if not cmds.getAttr(similar_node + ".intermediateObject"):
                continue

            _id = get_id(similar_node)
            if not _id:
                continue

            if _id in sibling_ids:
                sibling_ids[_id].append(similar_node)
            else:
                sibling_ids[_id] = [similar_node]

        if sibling_ids:
            first_id, found_nodes = next(iter(sibling_ids.items()))

            # Log a warning if we've found multiple unique ids
            if len(sibling_ids) > 1:
                log.warning(("Found more than 1 intermediate shape with"
                             " unique id for '{}'. Using id of first"
                             " found: '{}'".format(node, found_nodes[0])))

            return first_id


def set_scene_fps(fps, update=True):
    """Set FPS from project configuration

    Args:
        fps (int, float): desired FPS
        update(bool): toggle update animation, default is True

    Returns:
        None

    """

    fps_mapping = {
        '15': 'game',
        '24': 'film',
        '25': 'pal',
        '30': 'ntsc',
        '48': 'show',
        '50': 'palf',
        '60': 'ntscf',
        '23.976023976023978': '23.976fps',
        '29.97002997002997': '29.97fps',
        '47.952047952047955': '47.952fps',
        '59.94005994005994': '59.94fps',
        '44100': '44100fps',
        '48000': '48000fps'
    }

    unit = fps_mapping.get(str(convert_to_maya_fps(fps)), None)
    if unit is None:
        raise ValueError("Unsupported FPS value: `%s`" % fps)

    # Get time slider current state
    start_frame = cmds.playbackOptions(query=True, minTime=True)
    end_frame = cmds.playbackOptions(query=True, maxTime=True)

    # Get animation data
    animation_start = cmds.playbackOptions(query=True, animationStartTime=True)
    animation_end = cmds.playbackOptions(query=True, animationEndTime=True)

    current_frame = cmds.currentTime(query=True)

    log.info("Setting scene FPS to: '{}'".format(unit))
    cmds.currentUnit(time=unit, updateAnimation=update)

    # Set time slider data back to previous state
    cmds.playbackOptions(edit=True, minTime=start_frame)
    cmds.playbackOptions(edit=True, maxTime=end_frame)

    # Set animation data
    cmds.playbackOptions(edit=True, animationStartTime=animation_start)
    cmds.playbackOptions(edit=True, animationEndTime=animation_end)

    cmds.currentTime(current_frame, edit=True, update=True)

    # Force file stated to 'modified'
    cmds.file(modified=True)


def set_scene_resolution(width, height, pixelAspect):
    """Set the render resolution

    Args:
        width(int): value of the width
        height(int): value of the height

    Returns:
        None

    """

    control_node = "defaultResolution"
    current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
    aspect_ratio_attr = "deviceAspectRatio"

    # Give VRay a helping hand as it is slightly different from the rest
    if current_renderer == "vray":
        aspect_ratio_attr = "aspectRatio"
        vray_node = "vraySettings"
        if cmds.objExists(vray_node):
            control_node = vray_node
        else:
            log.error("Can't set VRay resolution because there is no node "
                      "named: `%s`" % vray_node)

    log.info("Setting scene resolution to: %s x %s" % (width, height))
    cmds.setAttr("%s.width" % control_node, width)
    cmds.setAttr("%s.height" % control_node, height)

    deviceAspectRatio = ((float(width) / float(height)) * float(pixelAspect))
    cmds.setAttr(
        "{}.{}".format(control_node, aspect_ratio_attr), deviceAspectRatio)
    cmds.setAttr("%s.pixelAspect" % control_node, pixelAspect)


def get_fps_for_current_context():
    """Get fps that should be set for current context.

    Todos:
        - Skip project value.
        - Merge logic with 'get_frame_range' and 'reset_scene_resolution' ->
            all the values in the functions can be collected at one place as
            they have same requirements.

    Returns:
        Union[int, float]: FPS value.
    """

    project_name = get_current_project_name()
    asset_name = get_current_asset_name()
    asset_doc = get_asset_by_name(
        project_name, asset_name, fields=["data.fps"]
    ) or {}
    fps = asset_doc.get("data", {}).get("fps")
    if not fps:
        project_doc = get_project(project_name, fields=["data.fps"]) or {}
        fps = project_doc.get("data", {}).get("fps")

        if not fps:
            fps = 25

    return convert_to_maya_fps(fps)


def get_frame_range(include_animation_range=False):
    """Get the current assets frame range and handles.

    Args:
        include_animation_range (bool, optional): Whether to include
            `animationStart` and `animationEnd` keys to define the outer
            range of the timeline. It is excluded by default.

    Returns:
        dict: Asset's expected frame range values.

    """

    # Set frame start/end
    project_name = get_current_project_name()
    asset_name = get_current_asset_name()
    asset = get_asset_by_name(project_name, asset_name)

    frame_start = asset["data"].get("frameStart")
    frame_end = asset["data"].get("frameEnd")

    if frame_start is None or frame_end is None:
        cmds.warning("No edit information found for %s" % asset_name)
        return

    handle_start = asset["data"].get("handleStart") or 0
    handle_end = asset["data"].get("handleEnd") or 0

    frame_range = {
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end
    }
    if include_animation_range:
        # The animation range values are only included to define whether
        # the Maya time slider should include the handles or not.
        # Some usages of this function use the full dictionary to define
        # instance attributes for which we want to exclude the animation
        # keys. That is why these are excluded by default.
        task_name = get_current_task_name()
        settings = get_project_settings(project_name)
        include_handles_settings = settings["maya"]["include_handles"]
        current_task = asset.get("data").get("tasks").get(task_name)

        animation_start = frame_start
        animation_end = frame_end

        include_handles = include_handles_settings["include_handles_default"]
        for item in include_handles_settings["per_task_type"]:
            if current_task["type"] in item["task_type"]:
                include_handles = item["include_handles"]
                break
        if include_handles:
            animation_start -= int(handle_start)
            animation_end += int(handle_end)

        frame_range["animationStart"] = animation_start
        frame_range["animationEnd"] = animation_end

    return frame_range


def reset_frame_range(playback=True, render=True, fps=True):
    """Set frame range to current asset

    Args:
        playback (bool, Optional): Whether to set the maya timeline playback
            frame range. Defaults to True.
        render (bool, Optional): Whether to set the maya render frame range.
            Defaults to True.
        fps (bool, Optional): Whether to set scene FPS. Defaults to True.
    """
    if fps:
        set_scene_fps(get_fps_for_current_context())

    frame_range = get_frame_range(include_animation_range=True)
    if not frame_range:
        # No frame range data found for asset
        return

    frame_start = frame_range["frameStart"]
    frame_end = frame_range["frameEnd"]
    animation_start = frame_range["animationStart"]
    animation_end = frame_range["animationEnd"]

    if playback:
        cmds.playbackOptions(
            minTime=frame_start,
            maxTime=frame_end,
            animationStartTime=animation_start,
            animationEndTime=animation_end
        )
        cmds.currentTime(frame_start)

    if render:
        cmds.setAttr("defaultRenderGlobals.startFrame", animation_start)
        cmds.setAttr("defaultRenderGlobals.endFrame", animation_end)


def reset_scene_resolution():
    """Apply the scene resolution  from the project definition

    scene resolution can be overwritten by an asset if the asset.data contains
    any information regarding scene resolution .

    Returns:
        None
    """

    project_name = get_current_project_name()
    project_doc = get_project(project_name)
    project_data = project_doc["data"]
    asset_data = get_current_project_asset()["data"]

    # Set project resolution
    width_key = "resolutionWidth"
    height_key = "resolutionHeight"
    pixelAspect_key = "pixelAspect"

    width = asset_data.get(width_key, project_data.get(width_key, 1920))
    height = asset_data.get(height_key, project_data.get(height_key, 1080))
    pixelAspect = asset_data.get(pixelAspect_key,
                                 project_data.get(pixelAspect_key, 1))

    set_scene_resolution(width, height, pixelAspect)


def set_context_settings():
    """Apply the project settings from the project definition

    Settings can be overwritten by an asset if the asset.data contains
    any information regarding those settings.

    Examples of settings:
        fps
        resolution
        renderer

    Returns:
        None
    """


    # Set project fps
    set_scene_fps(get_fps_for_current_context())

    reset_scene_resolution()

    # Set frame range.
    reset_frame_range()

    # Set colorspace
    set_colorspace()


# Valid FPS
def validate_fps():
    """Validate current scene FPS and show pop-up when it is incorrect

    Returns:
        bool

    """

    expected_fps = get_fps_for_current_context()
    current_fps = mel.eval('currentTimeUnitToFPS()')

    fps_match = current_fps == expected_fps
    if not fps_match and not IS_HEADLESS:
        from openpype.widgets import popup

        parent = get_main_window()

        dialog = popup.PopupUpdateKeys(parent=parent)
        dialog.setModal(True)
        dialog.setWindowTitle("Maya scene does not match project FPS")
        dialog.setMessage(
            "Scene {} FPS does not match project {} FPS".format(
                current_fps, expected_fps
            )
        )
        dialog.setButtonText("Fix")

        # Set new text for button (add optional argument for the popup?)
        toggle = dialog.widgets["toggle"]
        update = toggle.isChecked()
        dialog.on_clicked_state.connect(
            lambda: set_scene_fps(expected_fps, update)
        )

        dialog.show()

        return False

    return fps_match


def bake(nodes,
         frame_range=None,
         step=1.0,
         simulation=True,
         preserve_outside_keys=False,
         disable_implicit_control=True,
         shape=True):
    """Bake the given nodes over the time range.

    This will bake all attributes of the node, including custom attributes.

    Args:
        nodes (list): Names of transform nodes, eg. camera, light.
        frame_range (list): frame range with start and end frame.
            or if None then takes timeSliderRange
        simulation (bool): Whether to perform a full simulation of the
            attributes over time.
        preserve_outside_keys (bool): Keep keys that are outside of the baked
            range.
        disable_implicit_control (bool): When True will disable any
            constraints to the object.
        shape (bool): When True also bake attributes on the children shapes.
        step (float): The step size to sample by.

    Returns:
        None

    """

    # Parse inputs
    if not nodes:
        return

    assert isinstance(nodes, (list, tuple)), "Nodes must be a list or tuple"

    # If frame range is None fall back to time slider playback time range
    if frame_range is None:
        frame_range = [cmds.playbackOptions(query=True, minTime=True),
                       cmds.playbackOptions(query=True, maxTime=True)]

    # If frame range is single frame bake one frame more,
    # otherwise maya.cmds.bakeResults gets confused
    if frame_range[1] == frame_range[0]:
        frame_range[1] += 1

    # Bake it
    with keytangent_default(in_tangent_type='auto',
                            out_tangent_type='auto'):
        cmds.bakeResults(nodes,
                         simulation=simulation,
                         preserveOutsideKeys=preserve_outside_keys,
                         disableImplicitControl=disable_implicit_control,
                         shape=shape,
                         sampleBy=step,
                         time=(frame_range[0], frame_range[1]))


def bake_to_world_space(nodes,
                        frame_range=None,
                        simulation=True,
                        preserve_outside_keys=False,
                        disable_implicit_control=True,
                        shape=True,
                        step=1.0):
    """Bake the nodes to world space transformation (incl. other attributes)

    Bakes the transforms to world space (while maintaining all its animated
    attributes and settings) by duplicating the node. Then parents it to world
    and constrains to the original.

    Other attributes are also baked by connecting all attributes directly.
    Baking is then done using Maya's bakeResults command.

    See `bake` for the argument documentation.

    Returns:
         list: The newly created and baked node names.

    """
    @contextlib.contextmanager
    def _unlock_attr(attr):
        """Unlock attribute during context if it is locked"""
        if not cmds.getAttr(attr, lock=True):
            # If not locked, do nothing
            yield
            return
        try:
            cmds.setAttr(attr, lock=False)
            yield
        finally:
            cmds.setAttr(attr, lock=True)

    def _get_attrs(node):
        """Workaround for buggy shape attribute listing with listAttr

        This will only return keyable settable attributes that have an
        incoming connections (those that have a reason to be baked).

        Technically this *may* fail to return attributes driven by complex
        expressions for which maya makes no connections, e.g. doing actual
        `setAttr` calls in expressions.

        Arguments:
            node (str): The node to list attributes for.

        Returns:
            list: Keyable attributes with incoming connections.
                The attribute may be locked.

        """
        attrs = cmds.listAttr(node,
                              write=True,
                              scalar=True,
                              settable=True,
                              connectable=True,
                              keyable=True,
                              shortNames=True) or []
        valid_attrs = []
        for attr in attrs:
            node_attr = '{0}.{1}'.format(node, attr)

            # Sometimes Maya returns 'non-existent' attributes for shapes
            # so we filter those out
            if not cmds.attributeQuery(attr, node=node, exists=True):
                continue

            # We only need those that have a connection, just to be safe
            # that it's actually keyable/connectable anyway.
            if cmds.connectionInfo(node_attr,
                                   isDestination=True):
                valid_attrs.append(attr)

        return valid_attrs

    transform_attrs = {"t", "r", "s",
                       "tx", "ty", "tz",
                       "rx", "ry", "rz",
                       "sx", "sy", "sz"}

    world_space_nodes = []
    with ExitStack() as stack:
        delete_bin = stack.enter_context(delete_after())
        # Create the duplicate nodes that are in world-space connected to
        # the originals
        for node in nodes:

            # Duplicate the node
            short_name = node.rsplit("|", 1)[-1]
            new_name = "{0}_baked".format(short_name)
            new_node = cmds.duplicate(node,
                                      name=new_name,
                                      renameChildren=True)[0]  # noqa

            # Parent new node to world
            if cmds.listRelatives(new_node, parent=True):
                new_node = cmds.parent(new_node, world=True)[0]

            # Temporarily unlock and passthrough connect all attributes
            # so we can bake them over time
            # Skip transform attributes because we will constrain them later
            attrs = set(_get_attrs(node)) - transform_attrs
            for attr in attrs:
                orig_node_attr = "{}.{}".format(node, attr)
                new_node_attr = "{}.{}".format(new_node, attr)

                # unlock during context to avoid connection errors
                stack.enter_context(_unlock_attr(new_node_attr))
                cmds.connectAttr(orig_node_attr,
                                 new_node_attr,
                                 force=True)

            # If shapes are also baked then also temporarily unlock and
            # passthrough connect all shape attributes for baking
            if shape:
                children_shapes = cmds.listRelatives(new_node,
                                                     children=True,
                                                     fullPath=True,
                                                     shapes=True)
                if children_shapes:
                    orig_children_shapes = cmds.listRelatives(node,
                                                              children=True,
                                                              fullPath=True,
                                                              shapes=True)
                    for orig_shape, new_shape in zip(orig_children_shapes,
                                                     children_shapes):
                        attrs = _get_attrs(orig_shape)
                        for attr in attrs:
                            orig_node_attr = "{}.{}".format(orig_shape, attr)
                            new_node_attr = "{}.{}".format(new_shape, attr)

                            # unlock during context to avoid connection errors
                            stack.enter_context(_unlock_attr(new_node_attr))
                            cmds.connectAttr(orig_node_attr,
                                             new_node_attr,
                                             force=True)

            # Constraint transforms
            for attr in transform_attrs:
                transform_attr = "{}.{}".format(new_node, attr)
                stack.enter_context(_unlock_attr(transform_attr))
            delete_bin.extend(cmds.parentConstraint(node, new_node, mo=False))
            delete_bin.extend(cmds.scaleConstraint(node, new_node, mo=False))

            world_space_nodes.append(new_node)

        bake(world_space_nodes,
             frame_range=frame_range,
             step=step,
             simulation=simulation,
             preserve_outside_keys=preserve_outside_keys,
             disable_implicit_control=disable_implicit_control,
             shape=shape)

    return world_space_nodes


def load_capture_preset(data):
    """Convert OpenPype Extract Playblast settings to `capture` arguments

    Input data is the settings from:
        `project_settings/maya/publish/ExtractPlayblast/capture_preset`

    Args:
        data (dict): Capture preset settings from OpenPype settings

    Returns:
        dict: `capture.capture` compatible keyword arguments

    """

    options = dict()
    viewport_options = dict()
    viewport2_options = dict()
    camera_options = dict()

    # Straight key-value match from settings to capture arguments
    options.update(data["Codec"])
    options.update(data["Generic"])
    options.update(data["Resolution"])

    camera_options.update(data['Camera Options'])
    viewport_options.update(data["Renderer"])

    # DISPLAY OPTIONS
    disp_options = {}
    for key, value in data['Display Options'].items():
        if key.startswith('background'):
            # Convert background, backgroundTop, backgroundBottom colors
            if len(value) == 4:
                # Ignore alpha + convert RGB to float
                value = [
                    float(value[0]) / 255,
                    float(value[1]) / 255,
                    float(value[2]) / 255
                ]
            disp_options[key] = value
        elif key == "displayGradient":
            disp_options[key] = value

    options['display_options'] = disp_options

    # Viewport Options has a mixture of Viewport2 Options and Viewport Options
    # to pass along to capture. So we'll need to differentiate between the two
    VIEWPORT2_OPTIONS = {
        "textureMaxResolution",
        "renderDepthOfField",
        "ssaoEnable",
        "ssaoSamples",
        "ssaoAmount",
        "ssaoRadius",
        "ssaoFilterRadius",
        "hwFogStart",
        "hwFogEnd",
        "hwFogAlpha",
        "hwFogFalloff",
        "hwFogColorR",
        "hwFogColorG",
        "hwFogColorB",
        "hwFogDensity",
        "motionBlurEnable",
        "motionBlurSampleCount",
        "motionBlurShutterOpenFraction",
        "lineAAEnable"
    }
    for key, value in data['Viewport Options'].items():

        # There are some keys we want to ignore
        if key in {"override_viewport_options", "high_quality"}:
            continue

        # First handle special cases where we do value conversion to
        # separate option values
        if key == 'textureMaxResolution':
            viewport2_options['textureMaxResolution'] = value
            if value > 0:
                viewport2_options['enableTextureMaxRes'] = True
                viewport2_options['textureMaxResMode'] = 1
            else:
                viewport2_options['enableTextureMaxRes'] = False
                viewport2_options['textureMaxResMode'] = 0

        elif key == 'multiSample':
            viewport2_options['multiSampleEnable'] = value > 0
            viewport2_options['multiSampleCount'] = value

        elif key == 'alphaCut':
            viewport2_options['transparencyAlgorithm'] = 5
            viewport2_options['transparencyQuality'] = 1

        elif key == 'hwFogFalloff':
            # Settings enum value string to integer
            viewport2_options['hwFogFalloff'] = int(value)

        # Then handle Viewport 2.0 Options
        elif key in VIEWPORT2_OPTIONS:
            viewport2_options[key] = value

        # Then assume remainder is Viewport Options
        else:
            viewport_options[key] = value

    options['viewport_options'] = viewport_options
    options['viewport2_options'] = viewport2_options
    options['camera_options'] = camera_options

    # use active sound track
    scene = capture.parse_active_scene()
    options['sound'] = scene['sound']

    return options


def get_attr_in_layer(attr, layer):
    """Return attribute value in specified renderlayer.

    Same as cmds.getAttr but this gets the attribute's value in a
    given render layer without having to switch to it.

    Warning for parent attribute overrides:
        Attributes that have render layer overrides to their parent attribute
        are not captured correctly since they do not have a direct connection.
        For example, an override to sphere.rotate when querying sphere.rotateX
        will not return correctly!

    Note: This is much faster for Maya's renderLayer system, yet the code
        does no optimized query for render setup.

    Args:
        attr (str): attribute name, ex. "node.attribute"
        layer (str): layer name

    Returns:
        The return value from `maya.cmds.getAttr`

    """

    try:
        if cmds.mayaHasRenderSetup():
            from . import lib_rendersetup
            return lib_rendersetup.get_attr_in_layer(attr, layer)
    except AttributeError:
        pass

    # Ignore complex query if we're in the layer anyway
    current_layer = cmds.editRenderLayerGlobals(query=True,
                                                currentRenderLayer=True)
    if layer == current_layer:
        return cmds.getAttr(attr)

    connections = cmds.listConnections(attr,
                                       plugs=True,
                                       source=False,
                                       destination=True,
                                       type="renderLayer") or []
    connections = filter(lambda x: x.endswith(".plug"), connections)
    if not connections:
        return cmds.getAttr(attr)

    # Some value types perform a conversion when assigning
    # TODO: See if there's a maya method to allow this conversion
    # instead of computing it ourselves.
    attr_type = cmds.getAttr(attr, type=True)
    conversion = None
    if attr_type == "time":
        conversion = mel.eval('currentTimeUnitToFPS()')  # returns float
    elif attr_type == "doubleAngle":
        # Radians to Degrees: 180 / pi
        # TODO: This will likely only be correct when Maya units are set
        #       to degrees
        conversion = 57.2957795131
    elif attr_type == "doubleLinear":
        raise NotImplementedError("doubleLinear conversion not implemented.")

    for connection in connections:
        if connection.startswith(layer + "."):
            attr_split = connection.split(".")
            if attr_split[0] == layer:
                attr = ".".join(attr_split[0:-1])
                value = cmds.getAttr("%s.value" % attr)
                if conversion:
                    value *= conversion
                return value

    else:
        # When connections are present, but none
        # to the specific renderlayer than the layer
        # should have the "defaultRenderLayer"'s value
        layer = "defaultRenderLayer"
        for connection in connections:
            if connection.startswith(layer):
                attr_split = connection.split(".")
                if attr_split[0] == "defaultRenderLayer":
                    attr = ".".join(attr_split[0:-1])
                    value = cmds.getAttr("%s.value" % attr)
                    if conversion:
                        value *= conversion
                    return value

    return cmds.getAttr(attr)


def fix_incompatible_containers():
    """Backwards compatibility: old containers to use new ReferenceLoader"""
    old_loaders = {
        "MayaAsciiLoader",
        "AbcLoader",
        "ModelLoader",
        "CameraLoader",
        "RigLoader",
        "FBXLoader"
    }
    host = registered_host()
    for container in host.ls():
        loader = container['loader']
        if loader in old_loaders:
            log.info(
                "Converting legacy container loader {} to "
                "ReferenceLoader: {}".format(loader, container["objectName"])
            )
            cmds.setAttr(container["objectName"] + ".loader",
                         "ReferenceLoader", type="string")


def update_content_on_context_change():
    """
    This will update scene content to match new asset on context change
    """
    scene_sets = cmds.listSets(allSets=True)
    asset_doc = get_current_project_asset()
    new_asset = asset_doc["name"]
    new_data = asset_doc["data"]
    for s in scene_sets:
        try:
            if cmds.getAttr("{}.id".format(s)) == "pyblish.avalon.instance":
                attr = cmds.listAttr(s)
                print(s)
                if "asset" in attr:
                    print("  - setting asset to: [ {} ]".format(new_asset))
                    cmds.setAttr("{}.asset".format(s),
                                 new_asset, type="string")
                if "frameStart" in attr:
                    cmds.setAttr("{}.frameStart".format(s),
                                 new_data["frameStart"])
                if "frameEnd" in attr:
                    cmds.setAttr("{}.frameEnd".format(s),
                                 new_data["frameEnd"],)
        except ValueError:
            pass


def show_message(title, msg):
    from qtpy import QtWidgets
    from openpype.widgets import message_window

    # Find maya main window
    top_level_widgets = {w.objectName(): w for w in
                         QtWidgets.QApplication.topLevelWidgets()}

    parent = top_level_widgets.get("MayaWindow", None)
    if parent is None:
        pass
    else:
        message_window.message(title=title, message=msg, parent=parent)


def iter_shader_edits(relationships, shader_nodes, nodes_by_id, label=None):
    """Yield edits as a set of actions."""

    attributes = relationships.get("attributes", [])
    shader_data = relationships.get("relationships", {})

    shading_engines = cmds.ls(shader_nodes, type="objectSet", long=True)
    assert shading_engines, "Error in retrieving objectSets from reference"

    # region compute lookup
    shading_engines_by_id = defaultdict(list)
    for shad in shading_engines:
        shading_engines_by_id[get_id(shad)].append(shad)
    # endregion

    # region assign shading engines and other sets
    for data in shader_data.values():
        # collect all unique IDs of the set members
        shader_uuid = data["uuid"]
        member_uuids = [
            (member["uuid"], member.get("components"))
            for member in data["members"]]

        filtered_nodes = list()
        for _uuid, components in member_uuids:
            nodes = nodes_by_id.get(_uuid, None)
            if nodes is None:
                continue

            if components:
                # Assign to the components
                nodes = [".".join([node, components]) for node in nodes]

            filtered_nodes.extend(nodes)

        id_shading_engines = shading_engines_by_id[shader_uuid]
        if not id_shading_engines:
            log.error("{} - No shader found with cbId "
                      "'{}'".format(label, shader_uuid))
            continue
        elif len(id_shading_engines) > 1:
            log.error("{} - Skipping shader assignment. "
                      "More than one shader found with cbId "
                      "'{}'. (found: {})".format(label, shader_uuid,
                                                 id_shading_engines))
            continue

        if not filtered_nodes:
            log.warning("{} - No nodes found for shading engine "
                        "'{}'".format(label, id_shading_engines[0]))
            continue

        yield {"action": "assign",
               "uuid": data["uuid"],
               "nodes": filtered_nodes,
               "shader": id_shading_engines[0]}

    for data in attributes:
        nodes = nodes_by_id.get(data["uuid"], [])
        attr_value = data["attributes"]
        yield {"action": "setattr",
               "uuid": data["uuid"],
               "nodes": nodes,
               "attributes": attr_value}


def set_colorspace():
    """Set Colorspace from project configuration"""

    project_name = get_current_project_name()
    imageio = get_project_settings(project_name)["maya"]["imageio"]

    # ocio compatibility variables
    ocio_v2_maya_version = 2022
    maya_version = int(cmds.about(version=True))
    ocio_v2_support = use_ocio_v2 = maya_version >= ocio_v2_maya_version
    is_ocio_set = bool(os.environ.get("OCIO"))

    use_workfile_settings = imageio.get("workfile", {}).get("enabled")
    if use_workfile_settings:
        root_dict = imageio["workfile"]
    else:
        # TODO: deprecated code from 3.15.5 - remove
        # Maya 2022+ introduces new OCIO v2 color management settings that
        # can override the old color management preferences. OpenPype has
        # separate settings for both so we fall back when necessary.
        use_ocio_v2 = imageio["colorManagementPreference_v2"]["enabled"]
        if use_ocio_v2 and not ocio_v2_support:
            # Fallback to legacy behavior with a warning
            log.warning(
                "Color Management Preference v2 is enabled but not "
                "supported by current Maya version: {} (< {}). Falling "
                "back to legacy settings.".format(
                    maya_version, ocio_v2_maya_version)
            )

        if use_ocio_v2:
            root_dict = imageio["colorManagementPreference_v2"]
        else:
            root_dict = imageio["colorManagementPreference"]

        if not isinstance(root_dict, dict):
            msg = "set_colorspace(): argument should be dictionary"
            log.error(msg)
            return

    # backward compatibility
    # TODO: deprecated code from 3.15.5 - remove with deprecated code above
    view_name = root_dict.get("viewTransform")
    if view_name is None:
        view_name = root_dict.get("viewName")

    log.debug(">> root_dict: {}".format(pformat(root_dict)))
    if not root_dict:
        return

    # set color spaces for rendering space and view transforms
    def _colormanage(**kwargs):
        """Wrapper around `cmds.colorManagementPrefs`.

        This logs errors instead of raising an error so color management
        settings get applied as much as possible.

        """
        assert len(kwargs) == 1, "Must receive one keyword argument"
        try:
            cmds.colorManagementPrefs(edit=True, **kwargs)
            log.debug("Setting Color Management Preference: {}".format(kwargs))
        except RuntimeError as exc:
            log.error(exc)

    # enable color management
    cmds.colorManagementPrefs(edit=True, cmEnabled=True)
    cmds.colorManagementPrefs(edit=True, ocioRulesEnabled=True)

    if use_ocio_v2:
        log.info("Using Maya OCIO v2")
        if not is_ocio_set:
            # Set the Maya 2022+ default OCIO v2 config file path
            log.info("Setting default Maya OCIO v2 config")
            # Note: Setting "" as value also sets this default however
            # introduces a bug where launching a file on startup will prompt
            # to save the empty scene before it, so we set using the path.
            # This value has been the same for 2022, 2023 and 2024
            path = "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio"
            cmds.colorManagementPrefs(edit=True, configFilePath=path)

        # set rendering space and view transform
        _colormanage(renderingSpaceName=root_dict["renderSpace"])
        _colormanage(viewName=view_name)
        _colormanage(displayName=root_dict["displayName"])
    else:
        log.info("Using Maya OCIO v1 (legacy)")
        if not is_ocio_set:
            # Set the Maya default config file path
            log.info("Setting default Maya OCIO v1 legacy config")
            cmds.colorManagementPrefs(edit=True, configFilePath="legacy")

        # set rendering space and view transform
        _colormanage(renderingSpaceName=root_dict["renderSpace"])
        _colormanage(viewTransformName=view_name)


@contextlib.contextmanager
def parent_nodes(nodes, parent=None):
    # type: (list, str) -> list
    """Context manager to un-parent provided nodes and return them back."""

    def _as_mdagpath(node):
        """Return MDagPath for node path."""
        if not node:
            return
        sel = OpenMaya.MSelectionList()
        sel.add(node)
        return sel.getDagPath(0)

    # We can only parent dag nodes so we ensure input contains only dag nodes
    nodes = cmds.ls(nodes, type="dagNode", long=True)
    if not nodes:
        # opt-out early
        yield
        return

    parent_node_path = None
    delete_parent = False
    if parent:
        if not cmds.objExists(parent):
            parent_node = cmds.createNode("transform",
                                          name=parent,
                                          skipSelect=False)
            delete_parent = True
        else:
            parent_node = parent
        parent_node_path = cmds.ls(parent_node, long=True)[0]

    # Store original parents
    node_parents = []
    for node in nodes:
        node_parent = get_node_parent(node)
        node_parents.append((_as_mdagpath(node), _as_mdagpath(node_parent)))

    try:
        for node, node_parent in node_parents:
            node_parent_path = node_parent.fullPathName() if node_parent else None  # noqa
            if node_parent_path == parent_node_path:
                # Already a child
                continue

            if parent_node_path:
                cmds.parent(node.fullPathName(), parent_node_path)
            else:
                cmds.parent(node.fullPathName(), world=True)

        yield
    finally:
        # Reparent to original parents
        for node, original_parent in node_parents:
            node_path = node.fullPathName()
            if not node_path:
                # Node must have been deleted
                continue

            node_parent_path = get_node_parent(node_path)

            original_parent_path = None
            if original_parent:
                original_parent_path = original_parent.fullPathName()
                if not original_parent_path:
                    # Original parent node must have been deleted
                    continue

            if node_parent_path != original_parent_path:
                if not original_parent_path:
                    cmds.parent(node_path, world=True)
                else:
                    cmds.parent(node_path, original_parent_path)

        if delete_parent:
            cmds.delete(parent_node_path)


@contextlib.contextmanager
def maintained_time():
    ct = cmds.currentTime(query=True)
    try:
        yield
    finally:
        cmds.currentTime(ct, edit=True)


def iter_visible_nodes_in_range(nodes, start, end):
    """Yield nodes that are visible in start-end frame range.

    - Ignores intermediateObjects completely.
    - Considers animated visibility attributes + upstream visibilities.

    This is optimized for large scenes where some nodes in the parent
    hierarchy might have some input connections to the visibilities,
    e.g. key, driven keys, connections to other attributes, etc.

    This only does a single time step to `start` if current frame is
    not inside frame range since the assumption is made that changing
    a frame isn't so slow that it beats querying all visibility
    plugs through MDGContext on another frame.

    Args:
        nodes (list): List of node names to consider.
        start (int, float): Start frame.
        end (int, float): End frame.

    Returns:
        list: List of node names. These will be long full path names so
            might have a longer name than the input nodes.

    """
    # States we consider per node
    VISIBLE = 1  # always visible
    INVISIBLE = 0  # always invisible
    ANIMATED = -1  # animated visibility

    # Ensure integers
    start = int(start)
    end = int(end)

    # Consider only non-intermediate dag nodes and use the "long" names.
    nodes = cmds.ls(nodes, long=True, noIntermediate=True, type="dagNode")
    if not nodes:
        return

    with maintained_time():
        # Go to first frame of the range if the current time is outside
        # the queried range so can directly query all visible nodes on
        # that frame.
        current_time = cmds.currentTime(query=True)
        if not (start <= current_time <= end):
            cmds.currentTime(start)

        visible = cmds.ls(nodes, long=True, visible=True)
        for node in visible:
            yield node
        if len(visible) == len(nodes) or start == end:
            # All are visible on frame one, so they are at least visible once
            # inside the frame range.
            return

    # For the invisible ones check whether its visibility and/or
    # any of its parents visibility attributes are animated. If so, it might
    # get visible on other frames in the range.
    def memodict(f):
        """Memoization decorator for a function taking a single argument.

        See: http://code.activestate.com/recipes/
             578231-probably-the-fastest-memoization-decorator-in-the-/
        """

        class memodict(dict):
            def __missing__(self, key):
                ret = self[key] = f(key)
                return ret

        return memodict().__getitem__

    @memodict
    def get_state(node):
        plug = node + ".visibility"
        connections = cmds.listConnections(plug,
                                           source=True,
                                           destination=False)
        if connections:
            return ANIMATED
        else:
            return VISIBLE if cmds.getAttr(plug) else INVISIBLE

    visible = set(visible)
    invisible = [node for node in nodes if node not in visible]
    always_invisible = set()
    # Iterate over the nodes by short to long names to iterate the highest
    # in hierarchy nodes first. So the collected data can be used from the
    # cache for parent queries in next iterations.
    node_dependencies = dict()
    for node in sorted(invisible, key=len):

        state = get_state(node)
        if state == INVISIBLE:
            always_invisible.add(node)
            continue

        # If not always invisible by itself we should go through and check
        # the parents to see if any of them are always invisible. For those
        # that are "ANIMATED" we consider that this node is dependent on
        # that attribute, we store them as dependency.
        dependencies = set()
        if state == ANIMATED:
            dependencies.add(node)

        traversed_parents = list()
        for parent in iter_parents(node):

            if parent in always_invisible or get_state(parent) == INVISIBLE:
                # When parent is always invisible then consider this parent,
                # this node we started from and any of the parents we
                # have traversed in-between to be *always invisible*
                always_invisible.add(parent)
                always_invisible.add(node)
                always_invisible.update(traversed_parents)
                break

            # If we have traversed the parent before and its visibility
            # was dependent on animated visibilities then we can just extend
            # its dependencies for to those for this node and break further
            # iteration upwards.
            parent_dependencies = node_dependencies.get(parent, None)
            if parent_dependencies is not None:
                dependencies.update(parent_dependencies)
                break

            state = get_state(parent)
            if state == ANIMATED:
                dependencies.add(parent)

            traversed_parents.append(parent)

        if node not in always_invisible and dependencies:
            node_dependencies[node] = dependencies

    if not node_dependencies:
        return

    # Now we only have to check the visibilities for nodes that have animated
    # visibility dependencies upstream. The fastest way to check these
    # visibility attributes across different frames is with Python api 2.0
    # so we do that.
    @memodict
    def get_visibility_mplug(node):
        """Return api 2.0 MPlug with cached memoize decorator"""
        sel = OpenMaya.MSelectionList()
        sel.add(node)
        dag = sel.getDagPath(0)
        return OpenMaya.MFnDagNode(dag).findPlug("visibility", True)

    @contextlib.contextmanager
    def dgcontext(mtime):
        """MDGContext context manager"""
        context = OpenMaya.MDGContext(mtime)
        try:
            previous = context.makeCurrent()
            yield context
        finally:
            previous.makeCurrent()

    # We skip the first frame as we already used that frame to check for
    # overall visibilities. And end+1 to include the end frame.
    scene_units = OpenMaya.MTime.uiUnit()
    for frame in range(start + 1, end + 1):
        mtime = OpenMaya.MTime(frame, unit=scene_units)

        # Build little cache so we don't query the same MPlug's value
        # again if it was checked on this frame and also is a dependency
        # for another node
        frame_visibilities = {}
        with dgcontext(mtime) as context:
            for node, dependencies in list(node_dependencies.items()):
                for dependency in dependencies:
                    dependency_visible = frame_visibilities.get(dependency,
                                                                None)
                    if dependency_visible is None:
                        mplug = get_visibility_mplug(dependency)
                        dependency_visible = mplug.asBool(context)
                        frame_visibilities[dependency] = dependency_visible

                    if not dependency_visible:
                        # One dependency is not visible, thus the
                        # node is not visible.
                        break

                else:
                    # All dependencies are visible.
                    yield node
                    # Remove node with dependencies for next frame iterations
                    # because it was visible at least once.
                    node_dependencies.pop(node)

        # If no more nodes to process break the frame iterations..
        if not node_dependencies:
            break


def get_attribute_input(attr):
    connections = cmds.listConnections(attr, plugs=True, destination=False)
    return connections[0] if connections else None


def convert_to_maya_fps(fps):
    """Convert any fps to supported Maya framerates."""
    float_framerates = [
        23.976023976023978,
        # WTF is 29.97 df vs fps?
        29.97002997002997,
        47.952047952047955,
        59.94005994005994
    ]
    # 44100 fps evaluates as 41000.0. Why? Omitting for now.
    int_framerates = [
        2,
        3,
        4,
        5,
        6,
        8,
        10,
        12,
        15,
        16,
        20,
        24,
        25,
        30,
        40,
        48,
        50,
        60,
        75,
        80,
        90,
        100,
        120,
        125,
        150,
        200,
        240,
        250,
        300,
        375,
        400,
        500,
        600,
        750,
        1200,
        1500,
        2000,
        3000,
        6000,
        48000
    ]

    # If input fps is a whole number we'll return.
    if float(fps).is_integer():
        # Validate fps is part of Maya's fps selection.
        if int(fps) not in int_framerates:
            raise ValueError(
                "Framerate \"{}\" is not supported in Maya".format(fps)
            )
        return int(fps)
    else:
        # Differences to supported float frame rates.
        differences = []
        for i in float_framerates:
            differences.append(abs(i - fps))

        # Validate difference does not stray too far from supported framerates.
        min_difference = min(differences)
        min_index = differences.index(min_difference)
        supported_framerate = float_framerates[min_index]
        if min_difference > 0.1:
            raise ValueError(
                "Framerate \"{}\" strays too far from any supported framerate"
                " in Maya. Closest supported framerate is \"{}\"".format(
                    fps, supported_framerate
                )
            )

        return supported_framerate


def write_xgen_file(data, filepath):
    """Overwrites data in .xgen files.

    Quite naive approach to mainly overwrite "xgDataPath" and "xgProjectPath".

    Args:
        data (dict): Dictionary of key, value. Key matches with xgen file.
        For example:
            {"xgDataPath": "some/path"}
        filepath (string): Absolute path of .xgen file.
    """
    # Generate regex lookup for line to key basically
    # match any of the keys in `\t{key}\t\t`
    keys = "|".join(re.escape(key) for key in data.keys())
    re_keys = re.compile("^\t({})\t\t".format(keys))

    lines = []
    with open(filepath, "r") as f:
        for line in f:
            match = re_keys.match(line)
            if match:
                key = match.group(1)
                value = data[key]
                line = "\t{}\t\t{}\n".format(key, value)

            lines.append(line)

    with open(filepath, "w") as f:
        f.writelines(lines)


def get_color_management_preferences():
    """Get and resolve OCIO preferences."""
    data = {
        # Is color management enabled.
        "enabled": cmds.colorManagementPrefs(
            query=True, cmEnabled=True
        ),
        "rendering_space": cmds.colorManagementPrefs(
            query=True, renderingSpaceName=True
        ),
        "output_transform": cmds.colorManagementPrefs(
            query=True, outputTransformName=True
        ),
        "output_transform_enabled": cmds.colorManagementPrefs(
            query=True, outputTransformEnabled=True
        ),
        "view_transform": cmds.colorManagementPrefs(
            query=True, viewTransformName=True
        )
    }

    # Split view and display from view_transform. view_transform comes in
    # format of "{view} ({display})".
    regex = re.compile(r"^(?P<view>.+) \((?P<display>.+)\)$")
    if int(cmds.about(version=True)) <= 2020:
        # view_transform comes in format of "{view} {display}" in 2020.
        regex = re.compile(r"^(?P<view>.+) (?P<display>.+)$")

    match = regex.match(data["view_transform"])
    if not match:
        raise ValueError(
            "Unable to parse view and display from Maya view transform: '{}' "
            "using regex '{}'".format(data["view_transform"], regex.pattern)
        )

    data.update({
        "display": match.group("display"),
        "view": match.group("view")
    })

    # Get config absolute path.
    path = cmds.colorManagementPrefs(
        query=True, configFilePath=True
    )

    # The OCIO config supports a custom <MAYA_RESOURCES> token.
    maya_resources_token = "<MAYA_RESOURCES>"
    maya_resources_path = OpenMaya.MGlobal.getAbsolutePathToResources()
    path = path.replace(maya_resources_token, maya_resources_path)

    data["config"] = path

    return data


def get_color_management_output_transform():
    preferences = get_color_management_preferences()
    colorspace = preferences["rendering_space"]
    if preferences["output_transform_enabled"]:
        colorspace = preferences["output_transform"]
    return colorspace


def image_info(file_path):
    # type: (str) -> dict
    """Based on tha texture path, get its bit depth and format information.
    Take reference from makeTx.py in Arnold:
        ImageInfo(filename): Get Image Information for colorspace
        AiTextureGetFormat(filename): Get Texture Format
        AiTextureGetBitDepth(filename): Get Texture bit depth
    Args:
        file_path (str): Path to the texture file.
    Returns:
        dict: Dictionary with the information about the texture file.
    """
    from arnold import (
        AiTextureGetBitDepth,
        AiTextureGetFormat
    )
    # Get Texture Information
    img_info = {'filename': file_path}
    if os.path.isfile(file_path):
        img_info['bit_depth'] = AiTextureGetBitDepth(file_path)  # noqa
        img_info['format'] = AiTextureGetFormat(file_path)  # noqa
    else:
        img_info['bit_depth'] = 8
        img_info['format'] = "unknown"
    return img_info


def guess_colorspace(img_info):
    # type: (dict) -> str
    """Guess the colorspace of the input image filename.
    Note:
        Reference from makeTx.py
    Args:
        img_info (dict): Image info generated by :func:`image_info`
    Returns:
        str: color space name use in the `--colorconvert`
             option of maketx.
    """
    from arnold import (
        AiTextureInvalidate,
        # types
        AI_TYPE_BYTE,
        AI_TYPE_INT,
        AI_TYPE_UINT
    )
    try:
        if img_info['bit_depth'] <= 16:
            if img_info['format'] in (AI_TYPE_BYTE, AI_TYPE_INT, AI_TYPE_UINT): # noqa
                return 'sRGB'
            else:
                return 'linear'
        # now discard the image file as AiTextureGetFormat has loaded it
        AiTextureInvalidate(img_info['filename'])       # noqa
    except ValueError:
        print(("[maketx] Error: Could not guess"
               "colorspace for {}").format(img_info["filename"]))
        return "linear"


def len_flattened(components):
    """Return the length of the list as if it was flattened.

    Maya will return consecutive components as a single entry
    when requesting with `maya.cmds.ls` without the `flatten`
    flag. Though enabling `flatten` on a large list (e.g. millions)
    will result in a slow result. This command will return the amount
    of entries in a non-flattened list by parsing the result with
    regex.

    Args:
        components (list): The non-flattened components.

    Returns:
        int: The amount of entries.

    """
    assert isinstance(components, (list, tuple))
    n = 0

    pattern = re.compile(r"\[(\d+):(\d+)\]")
    for c in components:
        match = pattern.search(c)
        if match:
            start, end = match.groups()
            n += int(end) - int(start) + 1
        else:
            n += 1
    return n


def get_all_children(nodes):
    """Return all children of `nodes` including each instanced child.
    Using maya.cmds.listRelatives(allDescendents=True) includes only the first
    instance. As such, this function acts as an optimal replacement with a
    focus on a fast query.

    """

    sel = OpenMaya.MSelectionList()
    traversed = set()
    iterator = OpenMaya.MItDag(OpenMaya.MItDag.kDepthFirst)
    for node in nodes:

        if node in traversed:
            # Ignore if already processed as a child
            # before
            continue

        sel.clear()
        sel.add(node)
        dag = sel.getDagPath(0)

        iterator.reset(dag)
        # ignore self
        iterator.next()  # noqa: B305
        while not iterator.isDone():

            path = iterator.fullPathName()

            if path in traversed:
                iterator.prune()
                iterator.next()  # noqa: B305
                continue

            traversed.add(path)
            iterator.next()  # noqa: B305

    return list(traversed)


def get_capture_preset(task_name, task_type, subset, project_settings, log):
    """Get capture preset for playblasting.

    Logic for transitioning from old style capture preset to new capture preset
    profiles.

    Args:
        task_name (str): Task name.
        take_type (str): Task type.
        subset (str): Subset name.
        project_settings (dict): Project settings.
        log (object): Logging object.
    """
    capture_preset = None
    filtering_criteria = {
        "hosts": "maya",
        "families": "review",
        "task_names": task_name,
        "task_types": task_type,
        "subset": subset
    }

    plugin_settings = project_settings["maya"]["publish"]["ExtractPlayblast"]
    if plugin_settings["profiles"]:
        profile = filter_profiles(
            plugin_settings["profiles"],
            filtering_criteria,
            logger=log
        )
        capture_preset = profile.get("capture_preset")
    else:
        log.warning("No profiles present for Extract Playblast")

    # Backward compatibility for deprecated Extract Playblast settings
    # without profiles.
    if capture_preset is None:
        log.debug(
            "Falling back to deprecated Extract Playblast capture preset "
            "because no new style playblast profiles are defined."
        )
        capture_preset = plugin_settings["capture_preset"]

    return capture_preset or {}


def get_reference_node(members, log=None):
    """Get the reference node from the container members
    Args:
        members: list of node names

    Returns:
        str: Reference node name.

    """

    # Collect the references without .placeHolderList[] attributes as
    # unique entries (objects only) and skipping the sharedReferenceNode.
    references = set()
    for ref in cmds.ls(members, exactType="reference", objectsOnly=True):

        # Ignore any `:sharedReferenceNode`
        if ref.rsplit(":", 1)[-1].startswith("sharedReferenceNode"):
            continue

        # Ignore _UNKNOWN_REF_NODE_ (PLN-160)
        if ref.rsplit(":", 1)[-1].startswith("_UNKNOWN_REF_NODE_"):
            continue

        references.add(ref)

    assert references, "No reference node found in container"

    # Get highest reference node (least parents)
    highest = min(references,
                  key=lambda x: len(get_reference_node_parents(x)))

    # Warn the user when we're taking the highest reference node
    if len(references) > 1:
        if not log:
            log = logging.getLogger(__name__)

        log.warning("More than one reference node found in "
                    "container, using highest reference node: "
                    "%s (in: %s)", highest, list(references))

    return highest


def get_reference_node_parents(ref):
    """Return all parent reference nodes of reference node

    Args:
        ref (str): reference node.

    Returns:
        list: The upstream parent reference nodes.

    """
    parent = cmds.referenceQuery(ref,
                                 referenceNode=True,
                                 parent=True)
    parents = []
    while parent:
        parents.append(parent)
        parent = cmds.referenceQuery(parent,
                                     referenceNode=True,
                                     parent=True)
    return parents


def create_rig_animation_instance(
    nodes, context, namespace, options=None, log=None
):
    """Create an animation publish instance for loaded rigs.

    See the RecreateRigAnimationInstance inventory action on how to use this
    for loaded rig containers.

    Arguments:
        nodes (list): Member nodes of the rig instance.
        context (dict): Representation context of the rig container
        namespace (str): Namespace of the rig container
        options (dict, optional): Additional loader data
        log (logging.Logger, optional): Logger to log to if provided

    Returns:
        None

    """
    if options is None:
        options = {}
    name = context["representation"]["name"]
    output = next((node for node in nodes if
                   node.endswith("out_SET")), None)
    controls = next((node for node in nodes if
                     node.endswith("controls_SET")), None)
    if name != "fbx":
        assert output, "No out_SET in rig, this is a bug."
        assert controls, "No controls_SET in rig, this is a bug."

    anim_skeleton = next((node for node in nodes if
                          node.endswith("skeletonAnim_SET")), None)
    skeleton_mesh = next((node for node in nodes if
                          node.endswith("skeletonMesh_SET")), None)

    # Find the roots amongst the loaded nodes
    roots = (
        cmds.ls(nodes, assemblies=True, long=True) or
        get_highest_in_hierarchy(nodes)
    )
    assert roots, "No root nodes in rig, this is a bug."

    custom_subset = options.get("animationSubsetName")
    if custom_subset:
        formatting_data = {
            "asset": context["asset"],
            "subset": context['subset']['name'],
            "family": (
                context['subset']['data'].get('family') or
                context['subset']['data']['families'][0]
            )
        }
        namespace = get_custom_namespace(
            custom_subset.format(
                **formatting_data
            )
        )

    if log:
        log.info("Creating subset: {}".format(namespace))

    # Fill creator identifier
    creator_identifier = "io.openpype.creators.maya.animation"

    host = registered_host()
    create_context = CreateContext(host)
    # Create the animation instance
    rig_sets = [output, controls, anim_skeleton, skeleton_mesh]
    # Remove sets that this particular rig does not have
    rig_sets = [s for s in rig_sets if s is not None]
    with maintained_selection():
        cmds.select(rig_sets + roots, noExpand=True)
        create_context.create(
            creator_identifier=creator_identifier,
            variant=namespace,
            pre_create_data={"use_selection": True}
        )
