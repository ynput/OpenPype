import os
import json

from .constants import CUST_ATTR_GROUP


def default_custom_attributes_definition():
    json_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "custom_attributes.json"
    )
    with open(json_file_path, "r") as json_stream:
        data = json.load(json_stream)
    return data


def app_definitions_from_app_manager(app_manager):
    app_definitions = []
    for app_name, app in app_manager.applications.items():
        if app.enabled and app.is_host:
            app_definitions.append({
                app_name: app.full_label
            })

    if not app_definitions:
        app_definitions.append({"empty": "< Empty >"})
    return app_definitions


def tool_definitions_from_app_manager(app_manager):
    tools_data = []
    for tool_name, tool in app_manager.tools.items():
        tools_data.append({
            tool_name: tool.label
        })

    # Make sure there is at least one item
    if not tools_data:
        tools_data.append({"empty": "< Empty >"})
    return tools_data


def get_openpype_attr(session, split_hierarchical=True, query_keys=None):
    custom_attributes = []
    hier_custom_attributes = []
    if not query_keys:
        query_keys = [
            "id",
            "entity_type",
            "object_type_id",
            "is_hierarchical",
            "default"
        ]
    # TODO remove deprecated "pype" group from query
    cust_attrs_query = (
        "select {}"
        " from CustomAttributeConfiguration"
        # Kept `pype` for Backwards Compatiblity
        " where group.name in (\"pype\", \"{}\")"
    ).format(", ".join(query_keys), CUST_ATTR_GROUP)
    all_avalon_attr = session.query(cust_attrs_query).all()
    for cust_attr in all_avalon_attr:
        if split_hierarchical and cust_attr["is_hierarchical"]:
            hier_custom_attributes.append(cust_attr)
            continue

        custom_attributes.append(cust_attr)

    if split_hierarchical:
        # return tuple
        return custom_attributes, hier_custom_attributes

    return custom_attributes
