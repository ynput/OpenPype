def walk_hierarchy(node):
    """Recursively yield group node."""
    for child in node.children():
        if child.get("isGroupNode"):
            yield child

        for _child in walk_hierarchy(child):
            yield _child
