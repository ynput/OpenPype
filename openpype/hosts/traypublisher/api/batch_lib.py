# Helper functions to find matching asset for (multiple) processed source files
import os
import collections

from openpype.client import get_assets


def get_children_assets_by_name(project_name, top_asset_doc):
    """ Get all children for 'top_asset_doc' by theirs name

    Args:
        project_name (str)
        top_asset_doc (asset doc) (eg dict)
    Returns:
        (dict) {"shot1": shot1_asset_doc}
    """
    assets_by_parent_id = get_asset_docs_by_parent_id(project_name)
    _children_docs = get_children_docs(
        assets_by_parent_id, top_asset_doc
    )
    children_docs = {
        children_doc["name"].lower(): children_doc
        for children_doc in _children_docs
    }
    return children_docs


def get_asset_docs_by_parent_id(project_name):
    """ Query all assets for project and store them by parent's id to list

    Args:
         project_name (str)
    Returns:
        (dict) { _id of parent :[asset_doc1, asset_doc2]}
    """
    asset_docs_by_parent_id = collections.defaultdict(list)
    for asset_doc in get_assets(project_name):
        parent_id = asset_doc["data"]["visualParent"]
        asset_docs_by_parent_id[parent_id].append(asset_doc)
    return asset_docs_by_parent_id


def get_children_docs(documents_by_parent_id, parent_doc):
    """ Recursively find all children in reverse order

    Last children first.
    Args:
         documents_by_parent_id (dict)
         parent_doc (asset doc, eg dict)
    Returns
        (list) of asset docs
    """
    output = []
    children = documents_by_parent_id.get(parent_doc["_id"]) or tuple()
    for child in children:
        output.extend(
            get_children_docs(documents_by_parent_id, child)
        )
    output.append(parent_doc)
    return output

