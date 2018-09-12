import uuid

from contextlib import contextmanager

import hou

from avalon import api, io
from avalon.houdini import lib


def set_id(node, unique_id, overwrite=False):

    exists = node.parm("id")
    if not exists:
        lib.imprint(node, {"id": unique_id})

    if not exists and overwrite:
        node.setParm("id", unique_id)


def get_id(node):
    """
    Get the `cbId` attribute of the given node
    Args:
        node (hou.Node): the name of the node to retrieve the attribute from

    Returns:
        str

    """

    if node is None:
        return

    id = node.parm("id")
    if node is None:
        return
    return id


def generate_ids(nodes, asset_id=None):
    """Returns new unique ids for the given nodes.

    Note: This does not assign the new ids, it only generates the values.

    To assign new ids using this method:
    >>> nodes = ["a", "b", "c"]
    >>> for node, id in generate_ids(nodes):
    >>>     set_id(node, id)

    To also override any existing values (and assign regenerated ids):
    >>> nodes = ["a", "b", "c"]
    >>> for node, id in generate_ids(nodes):
    >>>     set_id(node, id, overwrite=True)

    Args:
        nodes (list): List of nodes.
        asset_id (str or bson.ObjectId): The database id for the *asset* to
            generate for. When None provided the current asset in the
            active session is used.

    Returns:
        list: A list of (node, id) tuples.

    """

    if asset_id is None:
        # Get the asset ID from the database for the asset of current context
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]},
                                 projection={"_id": True})
        assert asset_data, "No current asset found in Session"
        asset_id = asset_data['_id']

    node_ids = []
    for node in nodes:
        _, uid = str(uuid.uuid4()).rsplit("-", 1)
        unique_id = "{}:{}".format(asset_id, uid)
        node_ids.append((node, unique_id))

    return node_ids


def get_id_required_nodes():

    valid_types = ["geometry", "geometry"]
    nodes = {n for n in hou.node("/out").children() if
             n.type().name() in valid_types}

    return list(nodes)


def get_additional_data(container):
    """Not implemented yet!"""
    return container


@contextmanager
def attribute_values(node, data):

    previous_attrs = {key: node.parm(key).eval() for key in data.keys()}
    print("before", previous_attrs)
    try:
        node.setParms(data)
        during_attrs = {key: node.parm(key).eval() for key in data.keys()}
        print("during", during_attrs)
        yield
    except Exception as exc:
        print(exc)
        pass
    finally:
        print("reset")
        node.setParms(previous_attrs)
