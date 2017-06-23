"""Interactive functionality

These depend on user selection in Maya, and may be used as-is. They
implement the functionality in :mod:`commands.py`.

Each of these functions take `*args` as argument, because when used
in a Maya menu an additional argument is passed with metadata about
what state the button was pressed in. None of this data is used here.

"""

from maya import cmds, mel
from . import commands, lib


def connect_shapes(*args):
    """Connect the first selection to the last selection(s)"""
    selection = cmds.ls(selection=True)

    src = selection.pop(0)
    commands.connect_shapes(src, dst=selection)


def combine(*args):
    """Combine currently selected meshes

    This differs from the default Maya combine in that it
    retains the original mesh and produces a new mesh with the result.

    """

    commands.combine(cmds.ls(sl=1))


def read_selected_channels(*args):
    """Return a list of selected channels in the Channel Box"""
    channelbox = mel.eval("global string $gChannelBoxName; "
                          "$temp=$gChannelBoxName;")
    return cmds.channelBox(channelbox,
                           query=True,
                           selectedMainAttributes=True) or []


def set_defaults(*args):
    """Set currently selected values from channel box to their default value

    If no channel is selected, default all keyable attributes.

    """

    for node in cmds.ls(selection=True):
        selected_channels = read_selected_channels()
        for channel in (selected_channels or
                        cmds.listAttr(node, keyable=True)):
            try:
                default = cmds.attributeQuery(channel,
                                              node=node,
                                              listDefault=True)[0]
            except Exception:
                continue

            else:
                cmds.setAttr(node + "." + channel, default)


def transfer_outgoing_connections(*args):
    """Connect outgoing connections from first to second selected node"""

    try:
        src, dst = cmds.ls(selection=True)
    except ValueError:
        return cmds.warning("Select source and destination nodes")

    commands.transfer_outgoing_connections(src, dst)


def clone_special(*args):
    """Clone in localspace, and preserve user-defined attributes"""

    for transform in cmds.ls(selection=True, long=True):
        if cmds.nodeType(transform) != "transform":
            cmds.warning("Skipping '%s', not a `transform`" % transform)
            continue

        shape = _find_shape(transform)
        type = cmds.nodeType(shape)

        if type not in ("mesh", "nurbsSurface", "nurbsCurve"):
            cmds.warning("Skipping '{transform}': cannot clone nodes "
                         "of type '{type}'".format(**locals()))
            continue

        cloned = commands.clone(shape, worldspace=False)
        new_transform = cmds.listRelatives(cloned,
                                           parent=True,
                                           fullPath=True)[0]

        new_transform = cmds.rename(new_transform,
                                    new_transform.rsplit(":", 1)[-1])

        for attr in cmds.listAttr(transform,
                                  userDefined=True) or list():
            try:
                cmds.addAttr(new_transform, longName=attr, dataType="string")
            except Exception:
                continue

            value = cmds.getAttr(transform + "." + attr)
            cmds.setAttr(new_transform + "." + attr, value, type="string")

        # Connect visibility
        cmds.connectAttr(transform + ".visibility",
                         new_transform + ".visibility")


def clone_worldspace(*args):
    return _clone(worldspace=True)


def clone_localspace(*args):
    return _clone(worldspace=False)


def _clone(worldspace=False):
    """Clone selected objects in viewport

    Arguments:
        worldspace (bool): Whether or not to append a transformGeometry to
            resulting clone.

    """

    clones = list()

    for node in cmds.ls(selection=True, long=True):
        shape = _find_shape(node)
        type = cmds.nodeType(shape)

        if type not in ("mesh", "nurbsSurface", "nurbsCurve"):
            cmds.warning("Skipping '{node}': cannot clone nodes "
                         "of type '{type}'".format(**locals()))
            continue

        cloned = commands.clone(shape, worldspace=worldspace)
        clones.append(cloned)

    if not clones:
        return

    # Select newly created transform nodes in the viewport
    transforms = list()

    for clone in clones:
        transform = cmds.listRelatives(clone, parent=True, fullPath=True)[0]
        transforms.append(transform)

    cmds.select(transforms, replace=True)


def _find_shape(element):
    """Return shape of given 'element'

    Supports components, meshes, and surfaces

    Arguments:
        element (str): Path to component, mesh or surface

    Returns:
        str of path if found, None otherwise

    """

    # Get either shape or transform, based on element-type
    node = cmds.ls(element, objectsOnly=True, long=True)[0]

    if cmds.nodeType(node) == "transform":
        try:
            return cmds.listRelatives(node, shapes=True, fullPath=True)[0]
        except IndexError:
            return cmds.warning("Could not find shape in %s" % element)
    else:
        return node


def connect_matching_attributes_from_selection(*args):
    try:
        source, target = cmds.ls(sl=True)
    except ValueError:
        raise ValueError("Select (1) source and (2) target nodes only.")

    return commands.connect_matching_attributes(source, target)


def auto_connect(*args):
    """Connect `src` to `dst` via the most likely input and output"""
    try:
        commands.auto_connect(*cmds.ls(selection=True))
    except TypeError:
        cmds.warning("Select only source and destination nodes.")


def create_ncloth():
    selection = cmds.ls(selection=True)[0]

    input_mesh = cmds.listRelatives(selection, shapes=True)[0]
    current_mesh = commands.create_ncloth(input_mesh)

    # Optionally append suffix
    comp = selection.rsplit("_", 1)
    suffix = ("_" + comp[-1]) if len(comp) > 1 else ""

    cmds.rename(current_mesh, "currentMesh%sShape" % suffix)

    # Mimic default nCloth command
    cmds.hide(selection)


def follicle(*args):
    supported = ["mesh", "nurbsSurface"]
    selection = cmds.ls(sl=1)

    new_follicles = []
    for sel in selection:
        uv = lib.uv_from_element(sel)

        geometry_shape = lib.shape_from_element(sel)
        geometry_transform = cmds.listRelatives(geometry_shape, parent=True)[0]

        # Figure out output connection
        inputs = [".inputMesh", ".inputSurface"]
        outputs = [".outMesh", ".local"]

        failed = False
        type = cmds.nodeType(geometry_shape)
        if type not in supported:
            failed = True
            shapes = cmds.listRelatives(geometry_shape, shapes=True)

            if shapes:
                geometry_shape = shapes[0]
                type = cmds.nodeType(geometry_shape)
                if type in supported:
                    failed = False

        if failed:
            cmds.error("Skipping '%s': Type not accepted" % type)
            return

        input = inputs[supported.index(type)]
        output = outputs[supported.index(type)]

        # Make follicle
        follicle = cmds.createNode("follicle",
                                   name=geometry_transform + "_follicleShape1")
        follicle_transform = cmds.listRelatives(follicle, parent=True)[0]
        follicle_transform = cmds.rename(follicle_transform,
                                         geometry_transform + "_follicle1")

        # Set U and V value
        cmds.setAttr(follicle + ".parameterU", uv[0])
        cmds.setAttr(follicle + ".parameterV", uv[1])

        # Make the connections
        cmds.connectAttr(follicle + ".outTranslate",
                         follicle_transform + ".translate")
        cmds.connectAttr(follicle + ".outRotate",
                         follicle_transform + ".rotate")
        cmds.connectAttr(geometry_shape + output,
                         follicle + input)

        # Select last
        new_follicles.append(follicle_transform)

    # Select newly created follicles
    if new_follicles:
        cmds.select(new_follicles, r=1)

    return new_follicles


def auto_connect_assets(*args):
    references = cmds.ls(selection=True, type="reference")

    if not len(references) == 2:
        raise RuntimeError("Select source and destination "
                           "reference nodes, in that order.")

    return commands.auto_connect_assets(*references)
