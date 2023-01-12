# -*- coding: utf-8 -*-
"""Library of functions useful for 3dsmax pipeline."""
import json
import six
from pymxs import runtime as rt
from typing import Union
import contextlib


JSON_PREFIX = "JSON::"


def imprint(node_name: str, data: dict) -> bool:
    node = rt.getNodeByName(node_name)
    if not node:
        return False

    for k, v in data.items():
        if isinstance(v, (dict, list)):
            rt.setUserProp(node, k, f'{JSON_PREFIX}{json.dumps(v)}')
        else:
            rt.setUserProp(node, k, v)

    return True


def lsattr(
        attr: str,
        value: Union[str, None] = None,
        root: Union[str, None] = None) -> list:
    """List nodes having attribute with specified value.

    Args:
        attr (str): Attribute name to match.
        value (str, Optional): Value to match, of omitted, all nodes
            with specified attribute are returned no matter of value.
        root (str, Optional): Root node name. If omitted, scene root is used.

    Returns:
        list of nodes.
    """
    root = rt.rootnode if root is None else rt.getNodeByName(root)

    def output_node(node, nodes):
        nodes.append(node)
        for child in node.Children:
            output_node(child, nodes)

    nodes = []
    output_node(root, nodes)
    return [
        n for n in nodes
        if rt.getUserProp(n, attr) == value
    ] if value else [
        n for n in nodes
        if rt.getUserProp(n, attr)
    ]


def read(container) -> dict:
    data = {}
    props = rt.getUserPropBuffer(container)
    # this shouldn't happen but let's guard against it anyway
    if not props:
        return data

    for line in props.split("\r\n"):
        try:
            key, value = line.split("=")
        except ValueError:
            # if the line cannot be split we can't really parse it
            continue

        value = value.strip()
        if isinstance(value.strip(), six.string_types) and \
                value.startswith(JSON_PREFIX):
            try:
                value = json.loads(value[len(JSON_PREFIX):])
            except json.JSONDecodeError:
                # not a json
                pass

        data[key.strip()] = value

    data["instance_node"] = container.name

    return data


@contextlib.contextmanager
def maintained_selection():
    previous_selection = rt.getCurrentSelection()
    try:
        yield
    finally:
        if previous_selection:
            rt.select(previous_selection)
        else:
            rt.select()


def get_all_children(parent, node_type=None):
    """Handy function to get all the children of a given node

    Args:
        parent (3dsmax Node1): Node to get all children of.
        node_type (None, runtime.class): give class to check for
            e.g. rt.FFDBox/rt.GeometryClass etc.

    Returns:
        list: list of all children of the parent node
    """
    def list_children(node):
        children = []
        for c in node.Children:
            children.append(c)
            children = children + list_children(c)
        return children
    child_list = list_children(parent)

    return ([x for x in child_list if rt.superClassOf(x) == node_type]
            if node_type else child_list)
