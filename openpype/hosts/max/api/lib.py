# -*- coding: utf-8 -*-
"""Library of functions useful for 3dsmax pipeline."""
from pymxs import runtime as rt
from typing import Union


def imprint(node_name: str, data: dict) -> bool:
    node = rt.getNodeByName(node_name)
    if not node:
        return False

    for k, v in data.items():
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
    if not value:
        return [n for n in nodes if rt.getUserProp(n, attr)]

    return [n for n in nodes if rt.getUserProp(n, attr) == value]


def read(container) -> dict:
    data = {}
    props = rt.getUserPropBuffer(container)
    # this shouldn't happen but let's guard against it anyway
    if not props:
        return data

    for line in props.split("\r\n"):
        key, value = line.split("=")
        # if the line cannot be split we can't really parse it
        if not key:
            continue
        data[key.strip()] = value.strip()

    data["instance_node"] = container

    return data
