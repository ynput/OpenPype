import contextlib


@contextlib.contextmanager
def maintained_selection():
    return


@contextlib.contextmanager
def command_batch(name):
    return


def group_member_of_type(group_node, member_type):
    """
    usage layout_stack = group_member_of_type(sequence_layout, "RVStack")
    :param group_node:
    :param member_type:
    :return:
    """
    for node in rv.commands.nodesInGroup(group_node):
        if rv.commands.nodeType(node) == member_type:
            return node

