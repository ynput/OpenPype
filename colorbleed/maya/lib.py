"""Standalone helper functions"""

import re
import os
import bson
import json
import logging
import contextlib
from collections import OrderedDict, defaultdict

from avalon import maya, io

from maya import cmds, mel


log = logging.getLogger(__name__)

project = io.find_one({"type": "project",
                       "name": os.environ["AVALON_PROJECT"]},
                       projection={"config.template.publish": True,
                                   "_id": False})
TEMPLATE = project["config"]["template"]["publish"]


def maintained_selection(arg=None):
    if arg is not None:
        return _maintained_selection_context()
    else:
        return _maintained_selection_decorator(arg)


def _maintained_selection_decorator(func):
    """Function decorator to maintain the selection once called

    Example:
        >>> @_maintained_selection
        ... def my_function():
        ...    # Modify selection
        ...    cmds.select(clear=True)
        ...
        >>> # Selection restored

    """

    def wrapper(*args, **kwargs):
        previous_selection = cmds.ls(selection=True)
        try:
            return func(*args, **kwargs)
        finally:
            if previous_selection:
                cmds.select(previous_selection,
                            replace=True,
                            noExpand=True)
            else:
                cmds.select(deselect=True,
                            noExpand=True)

    return wrapper


@contextlib.contextmanager
def _maintained_selection_context():
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
            cmds.select(deselect=True,
                        noExpand=True)


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
        print("la")
        with maintained_selection():
            print("po")
            # Apply constraint using mode=2 (current and next) so
            # it applies to the selection made before it; because just
            # a `maya.cmds.select()` call will not trigger the constraint.
            with reset_polySelectConstraint():
                print("do")
                cmds.select(components, r=1)
                cmds.polySelectConstraint(*args, mode=2, **kwargs)
                result = cmds.ls(selection=True)

    return result


@contextlib.contextmanager
def reset_polySelectConstraint(reset=True):
    """Context during which the given polyConstraint settings are disabled.

    The original settings are restored after the context.

    """

    original = cmds.polySelectConstraint(query=True, stateString=True)

    try:
        if reset:
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

    # Format the job string from options
    job_args = list()
    for key, value in options.items():
        if isinstance(value, (list, tuple)):
            for entry in value:
                job_args.append("-{} {}".format(key, entry))
        elif isinstance(value, bool):
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


def remap_resource_nodes(resources, folder=None):

    log.info("Updating resource nodes ...")
    for resource in resources:
        source = resource["source"]
        if folder:
            fname = os.path.basename(source)
            fpath = os.path.join(folder, fname)
        else:
            fpath = source

        node_attr = resource["attribute"]
        cmds.setAttr(node_attr, fpath, type="string")

    log.info("Saving file ...")
    cmds.file(save=True, type="mayaAscii")


def _get_id(node):
    """
    Get the `cbId` attribute of the given node
    Args:
        node (str): the name of the node to retrieve the attribute from

    Returns:
        str

    """

    if node is None:
        return

    try:
        attr = "{}.cbId".format(node)
        attribute_value = cmds.getAttr(attr)
    except Exception as e:
        log.warning(e)
        return

    return attribute_value


def filter_by_id(nodes, uuids):
    """Filter all nodes which match the UUIDs

    Args:
        nodes (list): collection of nodes to check
        uuids (list): a list of UUIDs which are linked to the shader

    Returns:
        list: matching nodes
    """

    filtered_nodes = []
    for node in nodes:
        if node is None:
            continue

        if not cmds.attributeQuery("cbId", node=node, exists=True):
            continue

        # Deformed shaped
        attr = "{}.cbId".format(node)
        attribute_value = cmds.getAttr(attr)
        if attribute_value not in uuids:
            continue

        filtered_nodes.append(node)

    return filtered_nodes


def get_representation_file(representation, template=TEMPLATE):
    """
    Rebuild the filepath of the representation's context
    Args:
        representation (dict): data of the registered in the database
        template (str): the template to fill

    Returns:
        str

    """
    context = representation["context"].copy()
    context["root"] = os.environ["AVALON_ROOT"]
    return template.format(**context)


def list_looks(asset_id):
    """Return all look subsets for the given asset

    This assumes all look subsets start with "look*" in their names.
    """

    # # get all subsets with look leading in
    # the name associated with the asset
    subset = io.find({"parent": asset_id,
                      "type": "subset",
                      "name": {"$regex": "look*"}})

    return list(subset)


def assign_look_by_version(nodes, version_id):
    """Assign nodes a specific published look version by id.

    This assumes the nodes correspond with the asset.

    Args:
        nodes(list): nodes to assign look to
        version_id (bson.ObjectId)

    Returns:
        None
    """

    # get representations of shader file and relationships
    shader_file = io.find_one({"type": "representation",
                               "parent": version_id,
                               "name": "ma"})

    shader_relations = io.find_one({"type": "representation",
                                    "parent": version_id,
                                    "name": "json"})

    # Load file
    shader_filepath = get_representation_file(shader_file)
    shader_relation = get_representation_file(shader_relations)

    try:
        existing_reference = cmds.file(shader_filepath,
                                       query=True,
                                       referenceNode=True)
    except RuntimeError as e:
        if e.message.rstrip() != "Cannot find the scene file.":
            raise

        log.info("Loading lookdev for the first time..")

        # Define namespace
        assetname = shader_file['context']['asset']
        ns_assetname = "{}_".format(assetname)
        namespace = maya.unique_namespace(ns_assetname,
                                          format="%03d",
                                          suffix="_look")

        # Reference the look file
        with maya.maintained_selection():
            shader_nodes = cmds.file(shader_filepath,
                                     namespace=namespace,
                                     reference=True,
                                     returnNewNodes=True)
    else:
        log.info("Reusing existing lookdev..")
        shader_nodes = cmds.referenceQuery(existing_reference, nodes=True)

    # Assign relationships
    with open(shader_relation, "r") as f:
        relationships = json.load(f)

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
        colorbleed_id = cmds.getAttr("{}.cbId".format(node))
        asset_id = colorbleed_id.split(":")[0]
        grouped[asset_id].append(node)

    for asset_id, asset_nodes in grouped.items():
        # create objectId for database
        asset_id = bson.ObjectId(asset_id)
        subset = io.find_one({"type": "subset",
                              "name": subset,
                              "parent": asset_id})

        assert subset, "No subset found for {}".format(asset_id)

        # get last version
        version = io.find_one({"parent": subset['_id'],
                               "type": "version",
                               "data.families":
                                   {"$in":["colorbleed.lookdev"]}
                               },
                              sort=[("name", -1)],
                              projection={"_id": True})

        log.debug("Assigning look '{}' <{}> to nodes: {}".format(subset,
                                                                 version,
                                                                 asset_nodes))

        assign_look_by_version(asset_nodes, version['_id'])


def apply_shaders(relationships, shader_nodes, nodes):
    """Apply all shaders to the nodes based on the relationship data

    Args:
        relationships (dict): shader to node relationships
        shader_nodes (list): shader network nodes
        nodes (list): nodes to assign to

    Returns:
        None
    """

    shader_sets = relationships.get("sets", [])
    shading_engines = cmds.ls(shader_nodes, type="shadingEngine", long=True)
    assert len(shading_engines) > 0, ("Error in retrieving shading engine "
                                      "from reference")

    # Pre-filter nodes and shader nodes
    nodes_by_id = defaultdict(list)
    shader_nodes_by_id = defaultdict(list)
    for node in nodes:
        _id = _get_id(node)
        nodes_by_id[_id].append(node)

    for shader_node in shader_nodes:
        _id = _get_id(shader_node)
        shader_nodes_by_id[_id].append(shader_node)

    # get all nodes which we need to link per shader
    for shader_set in shader_sets:
        # collect shading engine
        uuid = shader_set["uuid"]
        shading_engine = shader_nodes_by_id.get(uuid, [])
        assert len(shading_engine) == 1, ("Could not find the correct "
                                          "shading engine with cbId "
                                          "'{}'".format(uuid))

        # collect members
        filtered_nodes = list()
        for member in shader_set["members"]:
            member_uuid = member["uuid"]
            members = nodes_by_id.get(member_uuid, [])
            filtered_nodes.extend(members)

        cmds.sets(filtered_nodes, forceElement=shading_engine[0])
