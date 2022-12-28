import Gaffer
import GafferScene
import imath


def set_node_color(node, color):
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


def make_box(name,
             add_input=True,
             add_output=True,
             description=None,
             hide_add_buttons=True):
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


def arrange(nodes, parent=None):
    """Layout the nodes in the graph.

    Args:
        nodes (list): The nodes to rearrange into a nice layout.
        parent (Gaffer.Node): Optional. The parent node to layout in.
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
