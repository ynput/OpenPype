import contextlib

import rv


@contextlib.contextmanager
def maintained_selection():
    return


@contextlib.contextmanager
def command_batch(name):
    return


@contextlib.contextmanager
def active_view(node):
    """Set active view during contet"""
    original = rv.commands.viewNode()
    try:
        rv.commands.setViewNode(node)
        yield
    finally:
        rv.commands.setViewNode(original)


def group_member_of_type(group_node, member_type):
    """Return first member of group that is of the given node type.

    This is similar to `rv.extra_commands.nodesInGroupOfType` but only
    returns the first entry directly if it has any match.

    Args:
        group_node (str): The group node to search in.
        member_type (str): The node type to search for.

    Returns:
        str or None: The first member found of given type or None
    """
    for node in rv.commands.nodesInGroup(group_node):
        if rv.commands.nodeType(node) == member_type:
            return node
