from avalon import harmony


class CreateRender(harmony.Creator):
    """Composite node for publishing renders."""

    name = "renderDefault"
    label = "Render"
    family = "render"
    node_type = "WRITE"

    def __init__(self, *args, **kwargs):
        super(CreateRender, self).__init__(*args, **kwargs)

    def setup_node(self, node):
        func = """function func(args)
        {
            node.setTextAttr(args[0], "DRAWING_TYPE", 1, "PNG4");
            node.setTextAttr(args[0], "DRAWING_NAME", 1, args[1]);
            node.setTextAttr(args[0], "MOVIE_PATH", 1, args[1]);
        }
        func
        """
        path = "{0}/{0}".format(node.split("/")[-1])
        harmony.send({"function": func, "args": [node, path]})
