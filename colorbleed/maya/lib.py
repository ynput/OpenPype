"""Standalone helper functions"""

import re
import os
import uuid

import bson
import json
import logging
import contextlib
from collections import OrderedDict, defaultdict

from maya import cmds, mel

from avalon import api, maya, io, pipeline
from colorbleed import lib


log = logging.getLogger(__name__)

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

RENDER_ATTRS = {"vray":
                    {
                        "node": "vraySettings",
                        "prefix": "fileNamePrefix",
                        "padding": "fileNamePadding",
                        "ext": "imageFormatStr"
                    },
                "default":
                    {
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


def unique(name):
    assert isinstance(name, basestring), "`name` must be string"

    while cmds.objExists(name):
        matches = re.findall(r"\d+$", name)

        if matches:
            match = matches[-1]
            name = name.rstrip(match)
            number = int(match) + 1
        else:
            number = 1

        name = name + str(number)

    return name


def uv_from_element(element):
    """Return the UV coordinate of given 'element'

    Supports components, meshes, nurbs.

    """

    supported = ["mesh", "nurbsSurface"]

    uv = [0.5, 0.5]

    if "." not in element:
        type = cmds.nodeType(element)
        if type == "transform":
            geometry_shape = cmds.listRelatives(element, shapes=True)

            if len(geometry_shape) >= 1:
                geometry_shape = geometry_shape[0]
            else:
                return

        elif type in supported:
            geometry_shape = element

        else:
            cmds.error("Could not do what you wanted..")
            return
    else:
        # If it is indeed a component - get the current Mesh
        try:
            parent = element.split(".", 1)[0]

            # Maya is funny in that when the transform of the shape
            # of the component elemen has children, the name returned
            # by that elementection is the shape. Otherwise, it is
            # the transform. So lets see what type we're dealing with here.
            if cmds.nodeType(parent) in supported:
                geometry_shape = parent
            else:
                geometry_shape = cmds.listRelatives(parent, shapes=1)[0]

            if not geometry_shape:
                cmds.error("Skipping %s: Could not find shape." % element)
                return

            if len(cmds.ls(geometry_shape)) > 1:
                cmds.warning("Multiple shapes with identical "
                             "names found. This might not work")

        except TypeError as e:
            cmds.warning("Skipping %s: Didn't find a shape "
                         "for component elementection. %s" % (element, e))
            return

        try:
            type = cmds.nodeType(geometry_shape)

            if type == "nurbsSurface":
                # If a surfacePoint is elementected on a nurbs surface
                root, u, v = element.rsplit("[", 2)
                uv = [float(u[:-1]), float(v[:-1])]

            if type == "mesh":
                # -----------
                # Average the U and V values
                # ===========
                uvs = cmds.polyListComponentConversion(element, toUV=1)
                if not uvs:
                    cmds.warning("Couldn't derive any UV's from "
                                 "component, reverting to default U and V")
                    raise TypeError

                # Flatten list of Uv's as sometimes it returns
                # neighbors like this [2:3] instead of [2], [3]
                flattened = []

                for uv in uvs:
                    flattened.extend(cmds.ls(uv, flatten=True))

                uvs = flattened

                sumU = 0
                sumV = 0
                for uv in uvs:
                    try:
                        u, v = cmds.polyEditUV(uv, query=True)
                    except Exception:
                        cmds.warning("Couldn't find any UV coordinated, "
                                     "reverting to default U and V")
                        raise TypeError

                    sumU += u
                    sumV += v

                averagedU = sumU / len(uvs)
                averagedV = sumV / len(uvs)

                uv = [averagedU, averagedV]
        except TypeError:
            pass

    return uv


def shape_from_element(element):
    """Return shape of given 'element'

    Supports components, meshes, and surfaces

    """

    try:
        # Get either shape or transform, based on element-type
        node = cmds.ls(element, objectsOnly=True)[0]
    except Exception:
        cmds.warning("Could not find node in %s" % element)
        return None

    if cmds.nodeType(node) == 'transform':
        try:
            return cmds.listRelatives(node, shapes=True)[0]
        except Exception:
            cmds.warning("Could not find shape in %s" % element)
            return None

    else:
        return node


def collect_animation_data():
    """Get the basic animation data

    Returns:
        OrderedDict

    """

    # get scene values as defaults
    start = cmds.playbackOptions(query=True, animationStartTime=True)
    end = cmds.playbackOptions(query=True, animationEndTime=True)

    # build attributes
    data = OrderedDict()
    data["startFrame"] = start
    data["endFrame"] = end
    data["handles"] = 1
    data["step"] = 1.0

    return data


@contextlib.contextmanager
def renderlayer(layer):
    """Set the renderlayer during the context"""

    original = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)

    try:
        cmds.editRenderLayerGlobals(currentRenderLayer=layer)
        yield
    finally:
        cmds.editRenderLayerGlobals(currentRenderLayer=original)


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
        with maya.maintained_selection():
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
            override_visibility = cmds.getAttr('{}.overrideVisibility'.format(node))
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
                    uvWrite= True,
                    eulerFilter= True,
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
            options.pop(key)
            continue

        # Validate value type
        valid_types = _alembic_options[key]
        if not isinstance(value, valid_types):
            raise TypeError("Alembic option unsupported type: "
                            "{0} (expected {1})".format(value, valid_types))

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


def maya_temp_folder():
    scene_dir = os.path.dirname(cmds.file(query=True, sceneName=True))
    tmp_dir = os.path.abspath(os.path.join(scene_dir, "..", "tmp"))
    if not os.path.isdir(tmp_dir):
        os.makedirs(tmp_dir)

    return tmp_dir


# region ID
def get_id_required_nodes(referenced_nodes=False, nodes=None):
    """Filter out any node which are locked (reference) or readOnly

    Args:
        referenced_nodes (bool): set True to filter out reference nodes
        nodes (list, Optional): nodes to consider
    Returns:
        nodes (set): list of filtered nodes
    """

    if nodes is None:
        # Consider all nodes
        nodes = cmds.ls()

    def _node_type_exists(node_type):
        try:
            cmds.nodeType(node_type, isTypeName=True)
            return True
        except RuntimeError:
            return False

    # `readOnly` flag is obsolete as of Maya 2016 therefor we explicitly remove
    # default nodes and reference nodes
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
    if cmds.pluginInfo("pgYetiMaya",  query=True, loaded=True):
        types.append("pgYetiMaya")

    # We *always* ignore intermediate shapes, so we filter them out
    # directly
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

    # Avoid locked nodes
    nodes_list = list(nodes)
    locked = cmds.lockNode(nodes_list, query=True, lock=True)
    for node, lock in zip(nodes_list, locked):
        if lock:
            log.warning("Skipping locked node: %s" % node)
            nodes.remove(node)

    return nodes


def get_id(node):
    """
    Get the `cbId` attribute of the given node
    Args:
        node (str): the name of the node to retrieve the attribute from

    Returns:
        str

    """

    if node is None:
        return

    if not cmds.attributeQuery("cbId", node=node, exists=True):
        return

    return cmds.getAttr("{}.cbId".format(node))


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

    attr = "{0}.cbId".format(node)
    exists = cmds.attributeQuery("cbId", node=node, exists=True)

    # Add the attribute if it does not exist yet
    if not exists:
        cmds.addAttr(node, longName="cbId", dataType="string")

    # Set the value
    if not exists or overwrite:
        cmds.setAttr(attr, unique_id, type="string")


def remove_id(node):
    """Remove the id attribute from the input node.

    Args:
        node (str): The node name

    Returns:
        bool: Whether an id attribute was deleted

    """
    if cmds.attributeQuery("cbId", node=node, exists=True):
        cmds.deleteAttr("{}.cbId".format(node))
        return True
    return False


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
        with maya.maintained_selection():
            container_node = pipeline.load(Loader, look_representation)

    # Get container members
    shader_nodes = cmds.sets(container_node, query=True)

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
        colorbleed_id = get_id(node)
        if not colorbleed_id:
            continue

        parts = colorbleed_id.split(":", 1)
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
                                   {"$in": ["colorbleed.look"]}
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
        for uuid in member_uuids:
            filtered_nodes.extend(nodes_by_id[uuid])

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
        root (bool): return highest node in hierachy if True

    Returns:
        root (list / str):
    """

    if not members:
        members = cmds.sets(container["objectName"], query=True)

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


def get_id_from_history(node):
    """Return first node id in the history chain that matches this node.

    The nodes in history must be of the exact same node type and must be
    parented under the same parent.

    Args:
        node (str): node to retrieve the

    Returns:
        str or None: The id from the node in history or None when no id found
            on any valid nodes in the history.

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


def set_project_fps():
    """Set FPS from project configuration

    Returns:
        None

    """

    int_fps = {15, 24, 5, 30, 48, 50, 60, 44100, 48000}
    float_fps = {23.976, 29.97, 29.97, 47.952, 59.94}

    fps = lib.get_project_fps()

    if isinstance(fps, float) and fps in float_fps:
        unit = "{:f}fps".format(int(fps))

    elif int(fps) in int_fps:
        unit = "{:d}fps".format(int(fps))

    else:
        raise ("Unsupported FPS value: `%s`" % fps)

    log.info("Updating FPS to '{}'".format(unit))
    cmds.currentUnit(time=unit)


# Valid FPS
def validate_fps():
    """Validate current scene FPS and show pop-up when it is incorrect

    Returns:
        None

    """

    current_fps = mel.eval('currentTimeUnitToFPS()')  # returns float
    fps = lib.get_project_fps()
    if fps != current_fps:

        from avalon.vendor.Qt import QtWidgets
        from ..widgets import popup

        # Find maya main window
        top_level_widgets = {w.objectName(): w for w in
                             QtWidgets.QApplication.topLevelWidgets()}

        parent = top_level_widgets.get("MayaWindow", None)
        if parent is None:
            pass
        else:
            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Maya scene not in line with project")
            dialog.setMessage("The FPS is out of sync, please fix")
            # Set new text for button (add optional argument for the popup?)
            dialog.widgets["show"].setText("Fix")
            dialog.on_show.connect(set_project_fps)

            dialog.show()
