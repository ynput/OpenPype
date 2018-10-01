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

    valid_types = ["geometry"]
    nodes = {n for n in hou.node("/out").children() if
             n.type().name() in valid_types}

    return list(nodes)


def get_additional_data(container):
    """Not implemented yet!"""
    return container


def set_parameter_callback(node, parameter, language, callback):
    """Link a callback to a parameter of a node

    Args:
        node(hou.Node): instance of the nodee
        parameter(str): name of the parameter
        language(str): name of the language, e.g.: python
        callback(str): command which needs to be triggered

    Returns:
        None

    """

    template_grp = node.parmTemplateGroup()
    template = template_grp.find(parameter)
    if not template:
        return

    script_language = (hou.scriptLanguage.Python if language == "python" else
                       hou.scriptLanguage.Hscript)

    template.setScriptCallbackLanguage(script_language)
    template.setScriptCallback(callback)

    template.setTags({"script_callback": callback,
                      "script_callback_language": language.lower()})

    # Replace the existing template with the adjusted one
    template_grp.replace(parameter, template)

    node.setParmTemplateGroup(template_grp)


def set_parameter_callbacks(node, parameter_callbacks):
    """Set callbacks for multiple parameters of a node

    Args:
        node(hou.Node): instance of a hou.Node
        parameter_callbacks(dict): collection of parameter and callback data
            example:  {"active" :
                        {"language": "python",
                         "callback": "print('hello world)'"}
                     }
    Returns:
        None
    """
    for parameter, data in parameter_callbacks.items():
        language = data["language"]
        callback = data["callback"]

        set_parameter_callback(node, parameter, language, callback)

@contextmanager
def attribute_values(node, data):

    previous_attrs = {key: node.parm(key).eval() for key in data.keys()}
    try:
        node.setParms(data)
        yield
    except Exception as exc:
        pass
    finally:
        node.setParms(previous_attrs)
