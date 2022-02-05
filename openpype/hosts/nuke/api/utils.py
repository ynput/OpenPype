import os
import nuke

from openpype.api import resources
from .lib import maintained_selection


def set_context_favorites(favorites=None):
    """ Adding favorite folders to nuke's browser

    Arguments:
        favorites (dict): couples of {name:path}
    """
    favorites = favorites or {}
    icon_path = resources.get_resource("icons", "folder-favorite3.png")
    for name, path in favorites.items():
        nuke.addFavoriteDir(
            name,
            path,
            nuke.IMAGE | nuke.SCRIPT | nuke.GEO,
            icon=icon_path)


def get_node_outputs(node):
    '''
    Return a dictionary of the nodes and pipes that are connected to node
    '''
    dep_dict = {}
    dependencies = node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS)
    for d in dependencies:
        dep_dict[d] = []
        for i in range(d.inputs()):
            if d.input(i) == node:
                dep_dict[d].append(i)
    return dep_dict


def is_node_gizmo(node):
    '''
    return True if node is gizmo
    '''
    return 'gizmo_file' in node.knobs()


def gizmo_is_nuke_default(gizmo):
    '''Check if gizmo is in default install path'''
    plug_dir = os.path.join(os.path.dirname(
        nuke.env['ExecutablePath']), 'plugins')
    return gizmo.filename().startswith(plug_dir)


def bake_gizmos_recursively(in_group=None):
    """Converting a gizmo to group

    Arguments:
        is_group (nuke.Node)[optonal]: group node or all nodes
    """
    if in_group is None:
        in_group = nuke.Root()
    # preserve selection after all is done
    with maintained_selection():
        # jump to the group
        with in_group:
            for node in nuke.allNodes():
                if is_node_gizmo(node) and not gizmo_is_nuke_default(node):
                    with node:
                        outputs = get_node_outputs(node)
                        group = node.makeGroup()
                        # Reconnect inputs and outputs if any
                        if outputs:
                            for n, pipes in outputs.items():
                                for i in pipes:
                                    n.setInput(i, group)
                        for i in range(node.inputs()):
                            group.setInput(i, node.input(i))
                        # set node position and name
                        group.setXYpos(node.xpos(), node.ypos())
                        name = node.name()
                        nuke.delete(node)
                        group.setName(name)
                        node = group

                if node.Class() == "Group":
                    bake_gizmos_recursively(node)


def colorspace_exists_on_node(node, colorspace_name):
    """ Check if colorspace exists on node

    Look through all options in the colorpsace knob, and see if we have an
    exact match to one of the items.

    Args:
        node (nuke.Node): nuke node object
        colorspace_name (str): color profile name

    Returns:
        bool: True if exists
    """
    try:
        colorspace_knob = node['colorspace']
    except ValueError:
        # knob is not available on input node
        return False
    all_clrs = get_colorspace_list(colorspace_knob)

    return colorspace_name in all_clrs


def get_colorspace_list(colorspace_knob):
    """Get available colorspace profile names

    Args:
        colorspace_knob (nuke.Knob): nuke knob object

    Returns:
        list: list of strings names of profiles
    """

    all_clrs = list(colorspace_knob.values())
    reduced_clrs = []

    if not colorspace_knob.getFlag(nuke.STRIP_CASCADE_PREFIX):
        return all_clrs

    # strip colorspace with nested path
    for clrs in all_clrs:
        clrs = clrs.split('/')[-1]
        reduced_clrs.append(clrs)

    return reduced_clrs
