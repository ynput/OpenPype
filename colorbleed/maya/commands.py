"""Used for scripting

These are used in other scripts and mostly require explicit input,
such as which specific nodes they apply to.

For interactive use, see :mod:`interactive.py`

"""

import sys

from maya import cmds

from . import lib

if sys.version_info[0] == 3:
    basestring = str

# Flags
LocalSpace = 1 << 0
WorldSpace = 1 << 1


def auto_connect2(src, dst):
    """Connect to `dst` based on what `dst` is and `src` has available

    TODO: Offer optionbox of choices when multiple inputs are possible.
        For example, connecting a mesh to a wrap node could either
        go to driverMesh, or baseMesh.

    """

    to_from = {
        "mesh": (
            ["mesh", (".outMesh", ".inMesh")],
        ),
        "nurbsSurface": (
            ["nurbsSurface", (".local", ".create")],
        ),
        "nurbsCurve": (
            ["nurbsCurve", (".local", ".create")],
        ),
        "decomposeMatrix": (
            ["transform", (".worldMatrix", ".inputMatrix")],
        ),
        "transform": (
            [
                "transform", (
                    (".translate", ".rotate", ".scale"),
                    (".translate", ".rotate", ".scale"))
            ],
            [
                "decomposeMatrix", (
                    (".outTranslate", ".outRotate", ".outScale"),
                    (".translate", ".rotate", ".scale"))
            ],
        ),
        "objectSet": (
            ["dagNode", (".message", ".dagSetMembers")],
            ["entity", (".message", ".dnSetMembers")],
        ),
    }

    support = next(
        (to_from[to] for to in to_from
         if to in cmds.nodeType(dst, inherited=True)), None
    )

    if not support:
        # Guess, based on available inputs,
        # what is the closest match
        print("Guessing..")
        pass

    assert support, "No supported outputs for '%s'" % (cmds.nodeType(src))

    out_, in_ = next(
        (typ for typ in support
         if typ[0] in cmds.nodeType(src, inherited=True)), (None, None)
    )

    assert in_ and out_, "No matching attributes found for %s" % src

    if not isinstance(in_, tuple):
        in_ = (in_,)

    if not isinstance(out_, tuple):
        out_ = (out_,)

    assert len(in_) == len(out_)

    map(lambda io: cmds.connectAttr(src + io[0],
                                    dst + io[1],
                                    force=True), zip(out_, in_))


def auto_connect(src, dst):
    """Connect `src` to `dst` via the most likely input and output

    Usage:
        >>> # Create cube and transfer mesh into new shape
        >>> shape = cmds.createNode("mesh", name="newShape")
        >>> transform, generator = cmds.polyCube(name="original")
        >>> auto_connect(generator, shape)
        >>> cmds.delete(transform)

    """

    out_ = {
        "mesh": ".outMesh",
        "nurbsSurface": ".local",
        "nurbsCurve": ".local",
        "decomposeMatrix": (".outTranslate",
                            ".outRotate",
                            ".outScale"),
        "transform": (".translate",
                      ".rotate",
                      ".scale",
                      ".visibility")
    }

    in_ = {
        "mesh": ".inMesh",
        "nurbsSurface": ".create",
        "nurbsCurve": ".create",
        "decomposeMatrix": "inputMatrix",
        "transform": (".translate",
                      ".rotate",
                      ".scale",
                      ".visibility"),
        "objectSet": ["dnSetMembers", "dgSetMembers"]
    }

    try:
        in_ = in_[cmds.nodeType(dst)]
    except KeyError:
        in_ = next((attr for attr in (".input",
                                      ".inputGeometry")
                   if cmds.objExists(dst + attr)), None)

    try:
        out_ = out_[cmds.nodeType(src)]
    except KeyError:
        out_ = next((attr for attr in (".output",
                                       ".outputGeometry")
                    if cmds.objExists(src + attr)), None)

    assert in_ and out_, "No matching attributes found for %s" % src

    if not isinstance(in_, tuple):
        in_ = (in_,)

    if not isinstance(out_, tuple):
        out_ = (out_,)

    assert len(in_) == len(out_)

    map(lambda io: cmds.connectAttr(src + io[0],
                                    dst + io[1],
                                    force=True), zip(out_, in_))


@lib.maintained_selection
def match_transform(src, dst):
    """Transform `src` to `dst`, taking worldspace into account

    Arguments:
        src (str): Absolute path to source transform
        dst (str): Absolute path to destination transform

    """

    try:
        parent = cmds.listRelatives(src, parent=True)[0]
    except Exception:
        parent = None

    node_decompose = cmds.createNode("decomposeMatrix")
    node_multmatrix = cmds.createNode("multMatrix")

    connections = {
        dst + ".worldMatrix": node_multmatrix + ".matrixIn[0]",
        node_multmatrix + ".matrixSum": node_decompose + ".inputMatrix",
        node_decompose + ".outputTranslate": src + ".translate",
        node_decompose + ".outputRotate": src + ".rotate",
        node_decompose + ".outputScale": src + ".scale",
    }

    if parent:
        connections.update({
            parent + ".worldInverseMatrix": node_multmatrix + ".matrixIn[1]"
        })

    for s, d in connections.iteritems():
        cmds.connectAttr(s, d, force=True)

    cmds.refresh()

    cmds.delete([node_decompose, node_multmatrix])


def connect_shapes(src, dst):
    """Connect geometry of `src` to source geometry of dst

    Arguments:
        src (str): Name of source shape
        dst (list): Names of destination nodes

    """

    out_attr = None

    if cmds.nodeType(src) == "mesh":
        out_attr = ".outMesh"

    elif cmds.nodeType(src) in ("nurbsSurface", "nurbsCurve"):
        out_attr = ".local"

    else:
        for wildcard in (".output",):
            if cmds.objExists(src + wildcard):
                out_attr = wildcard
                break

    if not out_attr:
        return cmds.warning("Could not detect output of %s" % src)

    for target in dst:
        in_attr = None

        if cmds.nodeType(target) == "mesh":
            in_attr = ".inMesh"

        elif cmds.nodeType(target) in ("nurbsSurface", "nurbsCurve"):
            in_attr = ".create"

        else:
            # Support unspecific nodes with common input attributes
            for support, wildcard in (("mesh", ".inputPolymesh"),
                                      ("mesh", ".inputMesh"),
                                      ("mesh", ".inputGeometry")):
                if cmds.objExists(target + wildcard):
                    if not cmds.nodeType(src) == support:
                        cmds.warning("Could not connect: %s -> %s" % (src,
                                                                      target))
                        break

                    in_attr = wildcard
                    break

        if not in_attr:
            cmds.warning("Could not detect input of %s" % target)
            continue

        try:
            cmds.connectAttr(src + out_attr,
                             target + in_attr,
                             force=True)
        except Exception as e:
            cmds.warning("Could not connect: %s%s -> %s%s (%s)" % (
                src, out_attr,
                target, in_attr, e)
            )


def connect_transform(driver, driven, source=WorldSpace, compensate=False):
    """Connect translation, rotation and scale via decomposeMatrix

    Arguments:
        driver (str): Absolute path to driver
        driven (str): Absolute path to driven
        source (str, optional): Either WorldSpace or LocalSpace,
            default WorldSpace
        compensate (bool, optional): Whether or not to take into account
            the current transform, default False.

    Returns:
        output (list): Newly created nodes

    """

    outputattr = ".matrix" if source == LocalSpace else ".worldMatrix[0]"

    assert cmds.objExists(driver), "%s not found" % driver
    assert cmds.objExists(driven), "%s not found" % driven

    decompose = driver + "_decompose"
    output = [decompose]

    if not cmds.objExists(decompose):
        decompose = cmds.createNode("decomposeMatrix", name=decompose)

        if compensate:

            multMatrix = cmds.createNode(
                "multMatrix", name=driver + "_multMatrix")

            # Compensate for drivens parentMatrix.
            cmds.connectAttr(driver + outputattr,
                             multMatrix + ".matrixIn[0]")
            cmds.connectAttr(driven + ".parentInverseMatrix",
                             multMatrix + ".matrixIn[1]")
            cmds.connectAttr(multMatrix + ".matrixSum",
                             decompose + ".inputMatrix")

            output.append(multMatrix)
        else:
            cmds.connectAttr(driver + outputattr,
                             decompose + ".inputMatrix")

    # Drive driven with compensated driver.
    cmds.connectAttr(decompose + ".outputTranslate", driven + ".t")
    cmds.connectAttr(decompose + ".outputRotate", driven + ".r")
    cmds.connectAttr(decompose + ".outputScale", driven + ".s")

    return output


def clone(shape, worldspace=False):
    """Clone `shape`

    Arguments:
        shape (str): Absolute path to shape
        worldspace (bool, optional): Whether or not to consider worldspace

    Returns:
        node (str): Newly created clone

    """

    type = cmds.nodeType(shape)
    assert type in ("mesh", "nurbsSurface", "nurbsCurve"), (
        "clone() works on polygonal and nurbs surfaces")

    src, dst = {
        "mesh": (".outMesh", ".inMesh"),
        "nurbsSurface": (".local", ".create"),
        "nurbsCurve": (".local", ".create"),
    }[type]

    nodetype = cmds.nodeType(shape)

    name = lib.unique(name=shape.rsplit("|")[-1])
    clone = cmds.createNode(nodetype, name=name)

    cmds.connectAttr(shape + src, clone + dst, force=True)

    if worldspace:
        transform = cmds.createNode("transformGeometry",
                                    name=name + "_transformGeometry")

        cmds.connectAttr(shape + src,
                         transform + ".inputGeometry", force=True)
        cmds.connectAttr(shape + ".worldMatrix[0]",
                         transform + ".transform", force=True)
        cmds.connectAttr(transform + ".outputGeometry",
                         clone + dst, force=True)

    # Assign default shader
    cmds.sets(clone, addElement="initialShadingGroup")

    return clone


def combine(nodes):
    """Produce a new mesh with the contents of `nodes`

    Arguments:
        nodes (list): Path to shapes

    """

    unite = cmds.createNode("polyUnite", n=nodes[0] + "_polyUnite")

    count = 0
    for node in nodes:
        # Are we dealing with transforms, or shapes directly?
        shapes = cmds.listRelatives(node, shapes=True) or [node]

        for shape in shapes:
            try:
                cmds.connectAttr(shape + ".outMesh",
                                 unite + ".inputPoly[%s]" % count, force=True)
                cmds.connectAttr(shape + ".worldMatrix",
                                 unite + ".inputMat[%s]" % count, force=True)
                count += 1

            except Exception:
                cmds.warning("'%s' is not a polygonal mesh" % shape)

    if count:
        output = cmds.createNode("mesh", n=nodes[0] + "_combinedShape")
        cmds.connectAttr(unite + ".output", output + ".inMesh", force=True)
        return output

    else:
        cmds.delete(unite)
        return None


def transfer_outgoing_connections(src, dst):
    """Connect outgoing connections from `src` to `dst`

    Connections that cannot be made are ignored.

    Arguments:
        src (str): Absolute path to source node
        dst (str): Absolute path to destination node

    """

    for destination in cmds.listConnections(src,
                                            source=False,
                                            plugs=True) or []:
        for source in cmds.listConnections(destination,
                                           destination=False,
                                           plugs=True) or []:
            try:
                cmds.connectAttr(source.replace(src, dst),
                                 destination, force=True)
            except RuntimeError:
                continue


def parent_group(source, transferTransform=True):
    """Create and transfer transforms to parent group"""
    assert cmds.objExists(source), "%s does not exist" % source
    assert cmds.nodeType(source) == "transform", (
        "%s must be transform" % source)

    parent = cmds.listRelatives(source, parent=True)

    if transferTransform:
        group = cmds.createNode("transform", n="%s_parent" % source)
        match_transform(group, source)

        try:
            cmds.parent(source, group)
        except Exception:
            cmds.warning("Failed to parent child under new parent")
            cmds.delete(group)

        if parent:
            cmds.parent(group, parent[0])

    else:
        cmds.select(source)
        group = cmds.group(n="%s_parent" % source)

    return group


def _output_node(source, type, suffix):
    newname = lib.unique(name=source.rsplit("_", 1)[0] + suffix)

    node = cmds.createNode(type)
    node = [cmds.listRelatives(node, parent=True) or node][0]
    node = cmds.rename(node, newname)

    try:
        cmds.parent(node, source)
        match_transform(node, source)

    except Exception:
        cmds.warning("Could not create %s" % node)
        cmds.delete(node)

    return node


def output_locator(source, suffix="_LOC"):
    """Create child locator

    Arguments:
            source (str): Parent node
            suffix (str): Suffix of output

    """

    return _output_node(source, "locator", suffix)


def output_joint(source, suffix="_JNT"):
    """Create child joint

    Arguments:
            source (str): Parent node
            suffix (str): Suffix of output

    """

    return _output_node(source, "joint", suffix)


def follicle(shape, u=0, v=0, name=""):
    """Attach follicle to "shape" at specified "u" and "v" values"""

    type = cmds.nodeType(shape)
    assert type in ("mesh", "nurbsSurface"), (
        "follicle() works on polygonal meshes and nurbs")

    src, dst = {
        "mesh": (".outMesh", ".inputMesh"),
        "nurbsSurface": (".local", ".inputSurface")
    }[type]

    follicle = cmds.createNode("follicle", name=name + "Shape")
    transform = cmds.listRelatives(follicle, parent=True)[0]

    cmds.setAttr(follicle + ".parameterU", u)
    cmds.setAttr(follicle + ".parameterV", v)

    cmds.connectAttr(follicle + ".outTranslate", transform + ".translate")
    cmds.connectAttr(follicle + ".outRotate", transform + ".rotate")
    cmds.connectAttr(shape + ".worldMatrix[0]", follicle + ".inputWorldMatrix")
    cmds.connectAttr(shape + src, follicle + dst, force=True)

    return transform


def connect_matching_attributes(source, target):
    """Connect matching attributes from source to target

    Arguments:
        source (str): Absolute path to node from which to connect
        target (str): Target node

    Example:
        >>> # Select two matching nodes
        >>> source = cmds.createNode("transform", name="source")
        >>> target = cmds.createNode("transform", name="target")
        >>> cmds.select([source, target], replace=True)
        >>> source, target = cmds.ls(selection=True)
        >>> connect_matching_attributes(source, target)

    """

    dsts = cmds.listAttr(target, keyable=True)
    for src in cmds.listAttr(source, keyable=True):
        if src not in dsts:
            continue

        try:
            src = "." + src
            cmds.connectAttr(source + src,
                             target + src,
                             force=True)
        except RuntimeError as e:
            cmds.warning("Could not connect %s: %s" % (src, e))


def create_ncloth(input_mesh):
    """Replace Create nCloth menu item

    This performs the identical option of nCloth -> Create nCloth
    with the following changes.

    1. Input mesh not made intermediate
    2. Current mesh and shape named "currentMesh"

    Arguments:
        input_mesh (str): Path to shape

    """

    assert cmds.nodeType(input_mesh) == "mesh", (
        "%s was not of type mesh" % input_mesh)

    nucleus = cmds.createNode("nucleus", name="nucleus1")
    ncloth = cmds.createNode("nCloth", name="nClothShape1")
    current_mesh = cmds.createNode("mesh", name="currentMesh")

    cmds.connectAttr(input_mesh + ".worldMesh[0]", ncloth + ".inputMesh")
    cmds.connectAttr(ncloth + ".outputMesh", current_mesh + ".inMesh")
    cmds.connectAttr("time1.outTime", nucleus + ".currentTime")
    cmds.connectAttr("time1.outTime", ncloth + ".currentTime")
    cmds.connectAttr(ncloth + ".currentState", nucleus + ".inputActive[0]")
    cmds.connectAttr(ncloth + ".startState", nucleus + ".inputActiveStart[0]")
    cmds.connectAttr(nucleus + ".outputObjects[0]", ncloth + ".nextState")
    cmds.connectAttr(nucleus + ".startFrame", ncloth + ".startFrame")

    # Assign default shader
    cmds.sets(current_mesh, addElement="initialShadingGroup")

    return current_mesh


def enhanced_parent(child, parent):
    if "shape" in cmds.nodeType(child, inherited=True):
        cmds.parent(relative=True, shape=True)
    else:
        cmds.parent(child, parent)


def auto_connect_assets(src, dst):
    """Attempt to automatically two assets

    Arguments:
        src (str): Name of source reference node
        dst (str): Name of destination reference node

    Raises:
        StopIteration on missing in_SET

    """

    in_set = None

    for node in cmds.referenceQuery(dst, nodes=True):
        if node.endswith("in_SET"):
            in_set = node
            break

    for input_transform in cmds.sets(in_set, query=True):
        mbid = cmds.getAttr(input_transform + ".mbID")
        input_shape = cmds.listRelatives(input_transform, shapes=True)[0]

        for output_transform in lib.lsattr("mbID", value=mbid):

            ref = cmds.referenceQuery(output_transform, referenceNode=True)
            if ref != src:
                continue

            print("Connecting %s -> %s" % (output_transform, input_transform))
            output_shape = cmds.listRelatives(output_transform, shapes=True)[0]

            try:
                auto_connect(output_transform, input_transform)
            except RuntimeError:
                # Already connected
                pass

            try:
                auto_connect(output_shape, input_shape)
            except RuntimeError:
                # Already connected
                pass
