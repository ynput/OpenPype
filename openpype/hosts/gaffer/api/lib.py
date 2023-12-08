from typing import Tuple, List, Optional

import Gaffer
import GafferScene
import imath


def set_node_color(node: Gaffer.Node, color: Tuple[float, float, float]):
    """Set node color.

    Args:
        node (Gaffer.Node): Node to set the color for.
        color (tuple): 3 float values representing RGB between 0.0-1.0

    Returns:
        None

    """
    assert len(color) == 3, "Color must be three float values"
    Gaffer.Metadata.registerValue(node, "nodeGadget:color",
                                  imath.Color3f(*color))


def make_box(name: str,
             add_input: bool = True,
             add_output: bool = True,
             description: Optional[str] = None,
             hide_add_buttons: bool = True) -> Gaffer.Box:
    """Create a Box node with BoxIn and BoxOut nodes"""

    box = Gaffer.Box(name)

    if description:
        Gaffer.Metadata.registerValue(box, 'description', description)

    if add_input:
        box_in = Gaffer.BoxIn("BoxIn")
        box.addChild(box_in)
        box_in.setup(GafferScene.ScenePlug("out"))

    if add_output:
        box_out = Gaffer.BoxOut("BoxOut")
        box.addChild(box_out)
        box_out.setup(GafferScene.ScenePlug("in",))

    if hide_add_buttons:
        for key in [
            'noduleLayout:customGadget:addButtonTop:visible',
            'noduleLayout:customGadget:addButtonBottom:visible',
            'noduleLayout:customGadget:addButtonLeft:visible',
            'noduleLayout:customGadget:addButtonRight:visible',
        ]:
            Gaffer.Metadata.registerValue(box, key, False)

    return box


def arrange(nodes: List[Gaffer.Node], parent: Optional[Gaffer.Node] = None):
    """Layout the nodes in the graph.

    Args:
        nodes (list): The nodes to rearrange into a nice layout.
        parent (list[Gaffer.Node]): Optional. The parent node to layout in.
            If not provided the parent of the first node is taken. The
            assumption is made that all nodes reside within the same parent.

    Returns:
        None

    """
    import GafferUI

    if not nodes:
        return

    if parent is None:
        # Assume passed in nodes all belong to single parent
        parent = nodes[0]

    graph = GafferUI.GraphGadget(parent)
    graph.getLayout().layoutNodes(graph, Gaffer.StandardSet(nodes))


def find_camera_paths(out_plug, starting_path="/"):
    """Traverses the scene starting at `starting_path` collecting a list of paths
    to all the Camera objects it finds

    Args:
        out_plug (GafferScene.ScenePlug): Typically the `["out]` plug of a node to traverse
            the scene hierarchy from.
        starting_path (string): The path to the starting point of the traversal.

    Returns:
        list: List of found paths to cameras.

    """
    cameras = []
    find_paths(out_plug, starting_path, "Camera", cameras)
    return cameras


def find_paths(scene, path, object_type_name, found_paths_list):
    """The actual scene traversal function. Populates the passed `found_paths_list` wit found paths.

    Args:
        scene (GafferScene.ScenePlug): The plug whose scene we will traverse.
        path (string): Starting path of traversal.
        object_type_name (String): The name of the objec type we want to find paths for.
        found_paths_list (list): The list of paths that will are found.

    Returns:
        None

    """
    if scene.object(path).typeName() == object_type_name:
        found_paths_list.append(path)
    for childName in scene.childNames(path):
        find_paths(scene, path.rstrip("/") + "/" + str(childName), object_type_name, found_paths_list)
