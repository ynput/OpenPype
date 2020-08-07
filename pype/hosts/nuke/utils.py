import os
import nuke
from avalon.nuke import lib as anlib
from pype.api import resources


def set_context_favorites(favorites={}):
    """ Addig favorite folders to nuke's browser

    Argumets:
        favorites (dict): couples of {name:path}
    """
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


def bake_gizmos_recursively(in_group=nuke.Root()):
    """Converting a gizmo to group

    Argumets:
        is_group (nuke.Node)[optonal]: group node or all nodes
    """
    # preserve selection after all is done
    with anlib.maintained_selection():
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
