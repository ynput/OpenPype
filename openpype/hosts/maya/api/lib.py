"""Standalone helper functions"""

import os
import sys
import platform
import uuid
import math

import json
import logging
import contextlib
from collections import OrderedDict, defaultdict
from math import ceil
from six import string_types
import bson

from maya import cmds, mel
import maya.api.OpenMaya as om

from avalon import api, io, pipeline

from openpype import lib
from openpype.api import get_anatomy_settings
from .commands import reset_frame_range


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

RENDER_ATTRS = {"vray": {
    "node": "vraySettings",
    "prefix": "fileNamePrefix",
    "padding": "fileNamePadding",
    "ext": "imageFormatStr"
},
    "default": {
    "node": "defaultRenderGlobals",
    "prefix": "imageFilePrefix",
    "padding": "extensionPadding"
}
}


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

RENDERLIKE_INSTANCE_FAMILIES = ["rendering", "vrayscene"]


def get_main_window():
    """Acquire Maya's main window"""
    from Qt import QtWidgets

    if self._parent is None:
        self._parent = {
            widget.objectName(): widget
            for widget in QtWidgets.QApplication.topLevelWidgets()
        }["MayaWindow"]
    return self._parent


@contextlib.contextmanager
def suspended_refresh():
    """Suspend viewport refreshes"""

    try:
        cmds.refresh(suspend=True)
        yield
    finally:
        cmds.refresh(suspend=False)


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


def _get_mel_global(name):
    """Return the value of a mel global variable"""
    return mel.eval("$%s = $%s;" % (name, name))


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


def export_alembic(nodes,
                   file,
                   frame_range=None,
                   write_uv=True,
                   write_visibility=True,
                   attribute_prefix=None):
    """Wrap native MEL command with limited set of arguments

    Arguments:
        nodes (list): Long names of nodes to cache

        file (str): Absolute path to output destination

        frame_range (tuple, optional): Start- and end-frame of cache,
            default to current animation range.

        write_uv (bool, optional): Whether or not to include UVs,
            default to True

        write_visibility (bool, optional): Turn on to store the visibility
        state of objects in the Alembic file. Otherwise, all objects are
        considered visible, default to True

        attribute_prefix (str, optional): Include all user-defined
            attributes with this prefix.

    """

    if frame_range is None:
        frame_range = (
            cmds.playbackOptions(query=True, ast=True),
            cmds.playbackOptions(query=True, aet=True)
        )

    options = [
        ("file", file),
        ("frameRange", "%s %s" % frame_range),
    ] + [("root", mesh) for mesh in nodes]

    if isinstance(attribute_prefix, string_types):
        # Include all attributes prefixed with "mb"
        # TODO(marcus): This would be a good candidate for
        #   external registration, so that the developer
        #   doesn't have to edit this function to modify
        #   the behavior of Alembic export.
        options.append(("attrPrefix", str(attribute_prefix)))

    if write_uv:
        options.append(("uvWrite", ""))

    if write_visibility:
        options.append(("writeVisibility", ""))

    # Generate MEL command
    mel_args = list()
    for key, value in options:
        mel_args.append("-{0} {1}".format(key, value))

    mel_args_string = " ".join(mel_args)
    mel_cmd = "AbcExport -j \"{0}\"".format(mel_args_string)

    # For debuggability, put the string passed to MEL in the Script editor.
    print("mel.eval('%s')" % mel_cmd)

    return mel.eval(mel_cmd)


def collect_animation_data(fps=False):
    """Get the basic animation data

    Returns:
        OrderedDict

    """

    # get scene values as defaults
    start = cmds.playbackOptions(query=True, animationStartTime=True)
    end = cmds.playbackOptions(query=True, animationEndTime=True)

    # build attributes
    data = OrderedDict()
    data["frameStart"] = start
    data["frameEnd"] = end
    data["handleStart"] = 0
    data["handleEnd"] = 0
    data["step"] = 1.0

    if fps:
        data["fps"] = mel.eval('currentTimeUnitToFPS()')

    return data


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
        >> # Return nodes with an `age` of five.
        >> lsattr({"age": "five"})
        >> # Return nodes with both `age` and `color` of five and blue.
        >> lsattr({"age": "five", "color": "blue"})

    Return:
         list: matching nodes.

    """

    dep_fn = om.MFnDependencyNode()
    dag_fn = om.MFnDagNode()
    selection_list = om.MSelectionList()

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
        if node.hasFn(om.MFn.kDagNode):
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


def get_renderer(layer):
    with renderlayer(layer):
        return cmds.getAttr("defaultRenderGlobals.currentRenderer")


def get_current_renderlayer():
    return cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)


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
def namespaced(namespace, new=True):
    """Work inside namespace during context

    Args:
        new (bool): When enabled this will rename the namespace to a unique
            namespace if the input namespace already exists.

    Yields:
        str: The namespace that is used during the context

    """
    original = cmds.namespaceInfo(cur=True, absoluteName=True)
    if new:
        namespace = unique_namespace(namespace)
        cmds.namespace(add=namespace)

    try:
        cmds.namespace(set=namespace)
        yield namespace
    finally:
        cmds.namespace(set=original)


@contextlib.contextmanager
def maintained_selection_api():
    """Maintain selection using the Maya Python API.

    Warning: This is *not* added to the undo stack.

    """
    original = om.MGlobal.getActiveSelectionList()
    try:
        yield
    finally:
        om.MGlobal.setActiveSelectionList(original)


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

    sel = om.MSelectionList()
    sel.add(node)

    api_node = sel.getDependNode(0)
    fn = om.MFnDependencyNode(api_node)

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
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]},
                                 projection={"_id": True})
        assert asset_data, "No current asset found in Session"
        asset_id = asset_data['_id']

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


# endregion ID
def get_reference_node(path):
    """
    Get the reference node when the path is found being used in a reference
    Args:
        path (str): the file path to check

    Returns:
        node (str): name of the reference node in question
    """
    try:
        node = cmds.file(path, query=True, referenceNode=True)
    except RuntimeError:
        log.debug('File is not referenced : "{}"'.format(path))
        return

    reference_path = cmds.referenceQuery(path, filename=True)
    if os.path.normpath(path) == os.path.normpath(reference_path):
        return node


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
    if "dataType" in kwargs:
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
    members = set(members)

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

        reference_members = cmds.referenceQuery(ref, nodes=True)
        reference_members = cmds.ls(reference_members,
                                    long=True,
                                    objectsOnly=True)
        members.update(reference_members)

    return members


# region LOOKDEV
def list_looks(asset_id):
    """Return all look subsets for the given asset

    This assumes all look subsets start with "look*" in their names.
    """

    # # get all subsets with look leading in
    # the name associated with the asset
    subset = io.find({"parent": bson.ObjectId(asset_id),
                      "type": "subset",
                      "name": {"$regex": "look*"}})

    return list(subset)


def assign_look_by_version(nodes, version_id):
    """Assign nodes a specific published look version by id.

    This assumes the nodes correspond with the asset.

    Args:
        nodes(list): nodes to assign look to
        version_id (bson.ObjectId): database id of the version

    Returns:
        None
    """

    # Get representations of shader file and relationships
    look_representation = io.find_one({"type": "representation",
                                       "parent": version_id,
                                       "name": "ma"})

    json_representation = io.find_one({"type": "representation",
                                       "parent": version_id,
                                       "name": "json"})

    # See if representation is already loaded, if so reuse it.
    host = api.registered_host()
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
        loaders = api.loaders_from_representation(api.discover(api.Loader),
                                                  representation_id)
        Loader = next((i for i in loaders if i.__name__ == "LookLoader"), None)
        if Loader is None:
            raise RuntimeError("Could not find LookLoader, this is a bug")

        # Reference the look file
        with maintained_selection():
            container_node = pipeline.load(Loader, look_representation)

    # Get container members
    shader_nodes = get_container_members(container_node)

    # Load relationships
    shader_relation = api.get_representation_path(json_representation)
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

    for asset_id, asset_nodes in grouped.items():
        # create objectId for database
        try:
            asset_id = bson.ObjectId(asset_id)
        except bson.errors.InvalidId:
            log.warning("Asset ID is not compatible with bson")
            continue
        subset_data = io.find_one({"type": "subset",
                                   "name": subset,
                                   "parent": asset_id})

        if not subset_data:
            log.warning("No subset '{}' found for {}".format(subset, asset_id))
            continue

        # get last version
        # with backwards compatibility
        version = io.find_one({"parent": subset_data['_id'],
                               "type": "version",
                               "data.families":
                                   {"$in": ["look"]}
                               },
                              sort=[("name", -1)],
                              projection={"_id": True, "name": True})

        log.debug("Assigning look '{}' <v{:03d}>".format(subset,
                                                         version["name"]))

        assign_look_by_version(asset_nodes, version['_id'])


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

        cmds.sets(filtered_nodes, forceElement=id_shading_engines[0])
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
        if len(split) == 1:
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

    def _get_parent(node):
        """Return full path name for parent of node"""
        return cmds.listRelatives(node, parent=True, fullPath=True)

    node = cmds.ls(node, long=True)[0]

    # Find all similar nodes in history
    history = cmds.listHistory(node)
    node_type = cmds.nodeType(node)
    similar_nodes = cmds.ls(history, exactType=node_type, long=True)

    # Exclude itself
    similar_nodes = [x for x in similar_nodes if x != node]

    # The node *must be* under the same parent
    parent = _get_parent(node)
    similar_nodes = [i for i in similar_nodes if _get_parent(i) == parent]

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



# Project settings
def set_scene_fps(fps, update=True):
    """Set FPS from project configuration

    Args:
        fps (int, float): desired FPS
        update(bool): toggle update animation, default is True

    Returns:
        None

    """

    fps_mapping = {'15': 'game',
                   '24': 'film',
                   '25': 'pal',
                   '30': 'ntsc',
                   '48': 'show',
                   '50': 'palf',
                   '60': 'ntscf',
                   '23.98': '23.976fps',
                   '23.976': '23.976fps',
                   '29.97': '29.97fps',
                   '47.952': '47.952fps',
                   '47.95': '47.952fps',
                   '59.94': '59.94fps',
                   '44100': '44100fps',
                   '48000': '48000fps'}

    # pull from mapping
    # this should convert float string to float and int to int
    # so 25.0 is converted to 25, but 23.98 will be still float.
    dec, ipart = math.modf(fps)
    if dec == 0.0:
        fps = int(ipart)

    unit = fps_mapping.get(str(fps), None)
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

    # Give VRay a helping hand as it is slightly different from the rest
    if current_renderer == "vray":
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
    cmds.setAttr("%s.deviceAspectRatio" % control_node, deviceAspectRatio)
    cmds.setAttr("%s.pixelAspect" % control_node, pixelAspect)


def reset_scene_resolution():
    """Apply the scene resolution  from the project definition

    scene resolution can be overwritten by an asset if the asset.data contains
    any information regarding scene resolution .

    Returns:
        None
    """

    project_doc = io.find_one({"type": "project"})
    project_data = project_doc["data"]
    asset_data = lib.get_asset()["data"]

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

    # Todo (Wijnand): apply renderer and resolution of project
    project_doc = io.find_one({"type": "project"})
    project_data = project_doc["data"]
    asset_data = lib.get_asset()["data"]

    # Set project fps
    fps = asset_data.get("fps", project_data.get("fps", 25))
    api.Session["AVALON_FPS"] = str(fps)
    set_scene_fps(fps)

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

    fps = lib.get_asset()["data"]["fps"]
    # TODO(antirotor): This is hack as for framerates having multiple
    # decimal places. FTrack is ceiling decimal values on
    # fps to two decimal places but Maya 2019+ is reporting those fps
    # with much higher resolution. As we currently cannot fix Ftrack
    # rounding, we have to round those numbers coming from Maya.
    current_fps = float_round(mel.eval('currentTimeUnitToFPS()'), 2)

    fps_match = current_fps == fps
    if not fps_match and not IS_HEADLESS:
        from openpype.widgets import popup

        parent = get_main_window()

        dialog = popup.Popup2(parent=parent)
        dialog.setModal(True)
        dialog.setWindowTitle("Maya scene not in line with project")
        dialog.setMessage("The FPS is out of sync, please fix")

        # Set new text for button (add optional argument for the popup?)
        toggle = dialog.widgets["toggle"]
        update = toggle.isChecked()
        dialog.on_show.connect(lambda: set_scene_fps(fps, update))

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

    def _get_attrs(node):
        """Workaround for buggy shape attribute listing with listAttr"""
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

    transform_attrs = set(["t", "r", "s",
                           "tx", "ty", "tz",
                           "rx", "ry", "rz",
                           "sx", "sy", "sz"])

    world_space_nodes = []
    with delete_after() as delete_bin:

        # Create the duplicate nodes that are in world-space connected to
        # the originals
        for node in nodes:

            # Duplicate the node
            short_name = node.rsplit("|", 1)[-1]
            new_name = "{0}_baked".format(short_name)
            new_node = cmds.duplicate(node,
                                      name=new_name,
                                      renameChildren=True)[0]

            # Connect all attributes on the node except for transform
            # attributes
            attrs = _get_attrs(node)
            attrs = set(attrs) - transform_attrs if attrs else []

            for attr in attrs:
                orig_node_attr = '{0}.{1}'.format(node, attr)
                new_node_attr = '{0}.{1}'.format(new_node, attr)

                # unlock to avoid connection errors
                cmds.setAttr(new_node_attr, lock=False)

                cmds.connectAttr(orig_node_attr,
                                 new_node_attr,
                                 force=True)

            # If shapes are also baked then connect those keyable attributes
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
                            orig_node_attr = '{0}.{1}'.format(orig_shape, attr)
                            new_node_attr = '{0}.{1}'.format(new_shape, attr)

                            # unlock to avoid connection errors
                            cmds.setAttr(new_node_attr, lock=False)

                            cmds.connectAttr(orig_node_attr,
                                             new_node_attr,
                                             force=True)

            # Parent to world
            if cmds.listRelatives(new_node, parent=True):
                new_node = cmds.parent(new_node, world=True)[0]

            # Unlock transform attributes so constraint can be created
            for attr in transform_attrs:
                cmds.setAttr('{0}.{1}'.format(new_node, attr), lock=False)

            # Constraints
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


def load_capture_preset(data=None):
    import capture

    preset = data

    options = dict()

    # CODEC
    id = 'Codec'
    for key in preset[id]:
        options[str(key)] = preset[id][key]

    # GENERIC
    id = 'Generic'
    for key in preset[id]:
        options[str(key)] = preset[id][key]

    # RESOLUTION
    id = 'Resolution'
    options['height'] = preset[id]['height']
    options['width'] = preset[id]['width']

    # DISPLAY OPTIONS
    id = 'Display Options'
    disp_options = {}
    for key in preset['Display Options']:
        if key.startswith('background'):
            disp_options[key] = preset['Display Options'][key]
            if len(disp_options[key]) == 4:
                disp_options[key][0] = (float(disp_options[key][0])/255)
                disp_options[key][1] = (float(disp_options[key][1])/255)
                disp_options[key][2] = (float(disp_options[key][2])/255)
                disp_options[key].pop()
        else:
            disp_options['displayGradient'] = True

    options['display_options'] = disp_options

    # VIEWPORT OPTIONS
    temp_options = {}
    id = 'Renderer'
    for key in preset[id]:
        temp_options[str(key)] = preset[id][key]

    temp_options2 = {}
    id = 'Viewport Options'
    for key in preset[id]:
        if key == 'textureMaxResolution':
            if preset[id][key] > 0:
                temp_options2['textureMaxResolution'] = preset[id][key]
                temp_options2['enableTextureMaxRes'] = True
                temp_options2['textureMaxResMode'] = 1
            else:
                temp_options2['textureMaxResolution'] = preset[id][key]
                temp_options2['enableTextureMaxRes'] = False
                temp_options2['textureMaxResMode'] = 0

        if key == 'multiSample':
            if preset[id][key] > 0:
                temp_options2['multiSampleEnable'] = True
                temp_options2['multiSampleCount'] = preset[id][key]
            else:
                temp_options2['multiSampleEnable'] = False
                temp_options2['multiSampleCount'] = preset[id][key]

        if key == 'ssaoEnable':
            if preset[id][key] is True:
                temp_options2['ssaoEnable'] = True
            else:
                temp_options2['ssaoEnable'] = False

        if key == 'alphaCut':
            temp_options2['transparencyAlgorithm'] = 5
            temp_options2['transparencyQuality'] = 1

        if key == 'headsUpDisplay':
            temp_options['headsUpDisplay'] = True

        else:
            temp_options[str(key)] = preset[id][key]

    for key in ['override_viewport_options',
                'high_quality',
                'alphaCut',
                'gpuCacheDisplayFilter',
                'multiSample',
                'ssaoEnable',
                'textureMaxResolution'
                ]:
        temp_options.pop(key, None)

    options['viewport_options'] = temp_options
    options['viewport2_options'] = temp_options2

    # use active sound track
    scene = capture.parse_active_scene()
    options['sound'] = scene['sound']

    # options['display_options'] = temp_options

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

    host = api.registered_host()
    for container in host.ls():
        loader = container['loader']

        print(container['loader'])

        if loader in ["MayaAsciiLoader",
                      "AbcLoader",
                      "ModelLoader",
                      "CameraLoader",
                      "RigLoader",
                      "FBXLoader"]:
            cmds.setAttr(container["objectName"] + ".loader",
                         "ReferenceLoader", type="string")


def _null(*args):
    pass


class shelf():
    '''A simple class to build shelves in maya. Since the build method is empty,
    it should be extended by the derived class to build the necessary shelf
    elements. By default it creates an empty shelf called "customShelf".'''

    ###########################################################################
    '''This is an example shelf.'''
    # class customShelf(_shelf):
    #     def build(self):
    #         self.addButon(label="button1")
    #         self.addButon("button2")
    #         self.addButon("popup")
    #         p = cmds.popupMenu(b=1)
    #         self.addMenuItem(p, "popupMenuItem1")
    #         self.addMenuItem(p, "popupMenuItem2")
    #         sub = self.addSubMenu(p, "subMenuLevel1")
    #         self.addMenuItem(sub, "subMenuLevel1Item1")
    #         sub2 = self.addSubMenu(sub, "subMenuLevel2")
    #         self.addMenuItem(sub2, "subMenuLevel2Item1")
    #         self.addMenuItem(sub2, "subMenuLevel2Item2")
    #         self.addMenuItem(sub, "subMenuLevel1Item2")
    #         self.addMenuItem(p, "popupMenuItem3")
    #         self.addButon("button3")
    # customShelf()
    ###########################################################################

    def __init__(self, name="customShelf", iconPath="", preset={}):
        self.name = name

        self.iconPath = iconPath

        self.labelBackground = (0, 0, 0, 0)
        self.labelColour = (.9, .9, .9)

        self.preset = preset

        self._cleanOldShelf()
        cmds.setParent(self.name)
        self.build()

    def build(self):
        '''This method should be overwritten in derived classes to actually
        build the shelf elements. Otherwise, nothing is added to the shelf.'''
        for item in self.preset['items']:
            if not item.get('command'):
                item['command'] = self._null
            if item['type'] == 'button':
                self.addButon(item['name'],
                              command=item['command'],
                              icon=item['icon'])
            if item['type'] == 'menuItem':
                self.addMenuItem(item['parent'],
                                 item['name'],
                                 command=item['command'],
                                 icon=item['icon'])
            if item['type'] == 'subMenu':
                self.addMenuItem(item['parent'],
                                 item['name'],
                                 command=item['command'],
                                 icon=item['icon'])

    def addButon(self, label, icon="commandButton.png",
                 command=_null, doubleCommand=_null):
        '''
            Adds a shelf button with the specified label, command,
            double click command and image.
        '''
        cmds.setParent(self.name)
        if icon:
            icon = os.path.join(self.iconPath, icon)
            print(icon)
        cmds.shelfButton(width=37, height=37, image=icon, label=label,
                         command=command, dcc=doubleCommand,
                         imageOverlayLabel=label, olb=self.labelBackground,
                         olc=self.labelColour)

    def addMenuItem(self, parent, label, command=_null, icon=""):
        '''
            Adds a shelf button with the specified label, command,
            double click command and image.
        '''
        if icon:
            icon = os.path.join(self.iconPath, icon)
            print(icon)
        return cmds.menuItem(p=parent, label=label, c=command, i="")

    def addSubMenu(self, parent, label, icon=None):
        '''
            Adds a sub menu item with the specified label and icon to
            the specified parent popup menu.
        '''
        if icon:
            icon = os.path.join(self.iconPath, icon)
            print(icon)
        return cmds.menuItem(p=parent, label=label, i=icon, subMenu=1)

    def _cleanOldShelf(self):
        '''
            Checks if the shelf exists and empties it if it does
            or creates it if it does not.
        '''
        if cmds.shelfLayout(self.name, ex=1):
            if cmds.shelfLayout(self.name, q=1, ca=1):
                for each in cmds.shelfLayout(self.name, q=1, ca=1):
                    cmds.deleteUI(each)
        else:
            cmds.shelfLayout(self.name, p="ShelfLayout")


def _get_render_instances():
    """Return all 'render-like' instances.

    This returns list of instance sets that needs to receive information
    about render layer changes.

    Returns:
        list: list of instances

    """
    objectset = cmds.ls("*.id", long=True, type="objectSet",
                        recursive=True, objectsOnly=True)

    instances = []
    for objset in objectset:
        if not cmds.attributeQuery("id", node=objset, exists=True):
            continue

        id_attr = "{}.id".format(objset)
        if cmds.getAttr(id_attr) != "pyblish.avalon.instance":
            continue

        has_family = cmds.attributeQuery("family",
                                         node=objset,
                                         exists=True)
        if not has_family:
            continue

        if cmds.getAttr(
                "{}.family".format(objset)) in RENDERLIKE_INSTANCE_FAMILIES:
            instances.append(objset)

    return instances


renderItemObserverList = []


class RenderSetupListObserver:
    """Observer to catch changes in render setup layers."""

    def listItemAdded(self, item):
        print("--- adding ...")
        self._add_render_layer(item)

    def listItemRemoved(self, item):
        print("--- removing ...")
        self._remove_render_layer(item.name())

    def _add_render_layer(self, item):
        render_sets = _get_render_instances()
        layer_name = item.name()

        for render_set in render_sets:
            members = cmds.sets(render_set, query=True) or []

            namespace_name = "_{}".format(render_set)
            if not cmds.namespace(exists=namespace_name):
                index = 1
                namespace_name = "_{}".format(render_set)
                try:
                    cmds.namespace(rm=namespace_name)
                except RuntimeError:
                    # namespace is not empty, so we leave it untouched
                    pass
                orignal_namespace_name = namespace_name
                while(cmds.namespace(exists=namespace_name)):
                    namespace_name = "{}{}".format(
                        orignal_namespace_name, index)
                    index += 1

                namespace = cmds.namespace(add=namespace_name)

            if members:
                # if set already have namespaced members, use the same
                # namespace as others.
                namespace = members[0].rpartition(":")[0]
            else:
                namespace = namespace_name

            render_layer_set_name = "{}:{}".format(namespace, layer_name)
            if render_layer_set_name in members:
                continue
            print("  - creating set for {}".format(layer_name))
            maya_set = cmds.sets(n=render_layer_set_name, empty=True)
            cmds.sets(maya_set, forceElement=render_set)
            rio = RenderSetupItemObserver(item)
            print("-   adding observer for {}".format(item.name()))
            item.addItemObserver(rio.itemChanged)
            renderItemObserverList.append(rio)

    def _remove_render_layer(self, layer_name):
        render_sets = _get_render_instances()

        for render_set in render_sets:
            members = cmds.sets(render_set, query=True)
            if not members:
                continue

            # all sets under set should have the same namespace
            namespace = members[0].rpartition(":")[0]
            render_layer_set_name = "{}:{}".format(namespace, layer_name)

            if render_layer_set_name in members:
                print("  - removing set for {}".format(layer_name))
                cmds.delete(render_layer_set_name)


class RenderSetupItemObserver:
    """Handle changes in render setup items."""

    def __init__(self, item):
        self.item = item
        self.original_name = item.name()

    def itemChanged(self, *args, **kwargs):
        """Item changed callback."""
        if self.item.name() == self.original_name:
            return

        render_sets = _get_render_instances()

        for render_set in render_sets:
            members = cmds.sets(render_set, query=True)
            if not members:
                continue

            # all sets under set should have the same namespace
            namespace = members[0].rpartition(":")[0]
            render_layer_set_name = "{}:{}".format(
                namespace, self.original_name)

            if render_layer_set_name in members:
                print(" <> renaming {} to {}".format(self.original_name,
                                                     self.item.name()))
                cmds.rename(render_layer_set_name,
                            "{}:{}".format(
                                namespace, self.item.name()))
            self.original_name = self.item.name()


renderListObserver = RenderSetupListObserver()


def add_render_layer_change_observer():
    import maya.app.renderSetup.model.renderSetup as renderSetup

    rs = renderSetup.instance()
    render_sets = _get_render_instances()

    layers = rs.getRenderLayers()
    for render_set in render_sets:
        members = cmds.sets(render_set, query=True)
        if not members:
            continue
        # all sets under set should have the same namespace
        namespace = members[0].rpartition(":")[0]
        for layer in layers:
            render_layer_set_name = "{}:{}".format(namespace, layer.name())
            if render_layer_set_name not in members:
                continue
            rio = RenderSetupItemObserver(layer)
            print("-   adding observer for {}".format(layer.name()))
            layer.addItemObserver(rio.itemChanged)
            renderItemObserverList.append(rio)


def add_render_layer_observer():
    import maya.app.renderSetup.model.renderSetup as renderSetup

    print(">   adding renderSetup observer ...")
    rs = renderSetup.instance()
    rs.addListObserver(renderListObserver)
    pass


def remove_render_layer_observer():
    import maya.app.renderSetup.model.renderSetup as renderSetup

    print("<   removing renderSetup observer ...")
    rs = renderSetup.instance()
    try:
        rs.removeListObserver(renderListObserver)
    except ValueError:
        # no observer set yet
        pass


def update_content_on_context_change():
    """
    This will update scene content to match new asset on context change
    """
    scene_sets = cmds.listSets(allSets=True)
    new_asset = api.Session["AVALON_ASSET"]
    new_data = lib.get_asset()["data"]
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
    from Qt import QtWidgets
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
    """Set Colorspace from project configuration
    """
    project_name = os.getenv("AVALON_PROJECT")
    imageio = get_anatomy_settings(project_name)["imageio"]["maya"]

    # Maya 2022+ introduces new OCIO v2 color management settings that
    # can override the old color managenement preferences. OpenPype has
    # separate settings for both so we fall back when necessary.
    use_ocio_v2 = imageio["colorManagementPreference_v2"]["enabled"]
    required_maya_version = 2022
    maya_version = int(cmds.about(version=True))
    maya_supports_ocio_v2 = maya_version >= required_maya_version
    if use_ocio_v2 and not maya_supports_ocio_v2:
        # Fallback to legacy behavior with a warning
        log.warning("Color Management Preference v2 is enabled but not "
                    "supported by current Maya version: {} (< {}). Falling "
                    "back to legacy settings.".format(
                        maya_version, required_maya_version)
                    )
        use_ocio_v2 = False

    if use_ocio_v2:
        root_dict = imageio["colorManagementPreference_v2"]
    else:
        root_dict = imageio["colorManagementPreference"]

    if not isinstance(root_dict, dict):
        msg = "set_colorspace(): argument should be dictionary"
        log.error(msg)

    log.debug(">> root_dict: {}".format(root_dict))

    # enable color management
    cmds.colorManagementPrefs(e=True, cmEnabled=True)
    cmds.colorManagementPrefs(e=True, ocioRulesEnabled=True)

    # set config path
    custom_ocio_config = False
    if root_dict.get("configFilePath"):
        unresolved_path = root_dict["configFilePath"]
        ocio_paths = unresolved_path[platform.system().lower()]

        resolved_path = None
        for ocio_p in ocio_paths:
            resolved_path = str(ocio_p).format(**os.environ)
            if not os.path.exists(resolved_path):
                continue

        if resolved_path:
            filepath = str(resolved_path).replace("\\", "/")
            cmds.colorManagementPrefs(e=True, configFilePath=filepath)
            cmds.colorManagementPrefs(e=True, cmConfigFileEnabled=True)
            log.debug("maya '{}' changed to: {}".format(
                "configFilePath", resolved_path))
            custom_ocio_config = True
        else:
            cmds.colorManagementPrefs(e=True, cmConfigFileEnabled=False)
            cmds.colorManagementPrefs(e=True, configFilePath="")

    # If no custom OCIO config file was set we make sure that Maya 2022+
    # either chooses between Maya's newer default v2 or legacy config based
    # on OpenPype setting to use ocio v2 or not.
    if maya_supports_ocio_v2 and not custom_ocio_config:
        if use_ocio_v2:
            # Use Maya 2022+ default OCIO v2 config
            log.info("Setting default Maya OCIO v2 config")
            cmds.colorManagementPrefs(edit=True, configFilePath="")
        else:
            # Set the Maya default config file path
            log.info("Setting default Maya OCIO v1 legacy config")
            cmds.colorManagementPrefs(edit=True, configFilePath="legacy")

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

    if use_ocio_v2:
        _colormanage(renderingSpaceName=root_dict["renderSpace"])
        _colormanage(displayName=root_dict["displayName"])
        _colormanage(viewName=root_dict["viewName"])
    else:
        _colormanage(renderingSpaceName=root_dict["renderSpace"])
        if maya_supports_ocio_v2:
            _colormanage(viewName=root_dict["viewTransform"])
            _colormanage(displayName="legacy")
        else:
            _colormanage(viewTransformName=root_dict["viewTransform"])


@contextlib.contextmanager
def root_parent(nodes):
    # type: (list) -> list
    """Context manager to un-parent provided nodes and return them back."""
    import pymel.core as pm  # noqa

    node_parents = []
    for node in nodes:
        n = pm.PyNode(node)
        try:
            root = pm.listRelatives(n, parent=1)[0]
        except IndexError:
            root = None
        node_parents.append((n, root))
    try:
        for node in node_parents:
            node[0].setParent(world=True)
        yield
    finally:
        for node in node_parents:
            if node[1]:
                node[0].setParent(node[1])
