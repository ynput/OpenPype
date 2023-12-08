from typing import Tuple, List, Optional
from queue import SimpleQueue

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


def traverse_scene(scene_plug: GafferScene.ScenePlug, root: str = "/"):
    """Yields breadth first all children from given `root`.

    Note: This also yields the root itself.
    This traverses down without the need for a recursive function.

    Args:
        scene_plug (GafferScene.ScenePlug): Plug scene to traverse.
            Typically, the out plug of a node (`node["out"]`).
        root (string): The root path as starting point of the traversal.

    Yields:
        str: Child path

    """
    queue = SimpleQueue()
    queue.put_nowait(root)
    while not queue.empty():
        path = queue.get_nowait()
        yield path

        for child_name in scene_plug.childNames(path):
            child_path = f"{path.rstrip('/')}/{child_name}"
            queue.put_nowait(child_path)


def find_camera_paths(scene_plug: GafferScene.ScenePlug,
                      root: str = "/"):
    """Traverses the scene plug starting at `root` returning all cameras.

    Args:
        scene_plug (GafferScene.ScenePlug): Plug scene to traverse.
            Typically, the out plug of a node (`node["out"]`).
        root (string): The root path as starting point of the traversal.

    Returns:
        list: List of found paths to cameras.

    """
    return find_paths_by_type(scene_plug, "Camera", root)


def find_paths_by_type(scene_plug: GafferScene.ScenePlug,
                       object_type_name: str,
                       root: str = "/") -> List[str]:
    """Return all paths in scene plug under `path` that match given type.

    Examples:
        >>> find_paths_by_type(plug, "MeshPrimitive")  # all meshes
        # ['/cube', '/nested/path/cube']
        >>> find_paths_by_type(plug, "NullObject")     # all nulls (groups)
        # ['/nested/path']
        >>> find_paths_by_type(plug, "Camera")     # all cameras
        # ['/nested/path']

    Args:
        scene_plug (GafferScene.ScenePlug): The plug whose scene we will traverse.
        object_type_name (String): The name of the object type we want to find.
        root (string): Starting root path of traversal.

    Returns:
        None

    """
    result = []
    for path in traverse_scene(scene_plug, root):
        if scene_plug.object(path).typeName() == object_type_name:
            result.append(path)
    return result
