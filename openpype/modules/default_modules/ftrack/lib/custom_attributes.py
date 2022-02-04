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
    _app_definitions = []
    for app_name, app in app_manager.applications.items():
        if app.enabled:
            _app_definitions.append(
                (app_name, app.full_label)
            )

    # Sort items by label
    app_definitions = []
    for key, label in sorted(_app_definitions, key=lambda item: item[1]):
        app_definitions.append({key: label})

    if not app_definitions:
        app_definitions.append({"empty": "< Empty >"})
    return app_definitions


def tool_definitions_from_app_manager(app_manager):
    _tools_data = []
    for tool_name, tool in app_manager.tools.items():
        _tools_data.append(
            (tool_name, tool.label)
        )

    # Sort items by label
    tools_data = []
    for key, label in sorted(_tools_data, key=lambda item: item[1]):
        tools_data.append({key: label})

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


def join_query_keys(keys):
    """Helper to join keys to query."""
    return ",".join(["\"{}\"".format(key) for key in keys])


def query_custom_attributes(session, conf_ids, entity_ids, table_name=None):
    """Query custom attribute values from ftrack database.

    Using ftrack call method result may differ based on used table name and
    version of ftrack server.

    Args:
        session(ftrack_api.Session): Connected ftrack session.
        conf_id(list, set, tuple): Configuration(attribute) ids which are
            queried.
        entity_ids(list, set, tuple): Entity ids for which are values queried.
        table_name(str): Table nam from which values are queried. Not
            recommended to change until you know what it means.
    """
    output = []
    # Just skip
    if not conf_ids or not entity_ids:
        return output

    if table_name is None:
        table_name = "ContextCustomAttributeValue"

    # Prepare values to query
    attributes_joined = join_query_keys(conf_ids)
    attributes_len = len(conf_ids)

    # Query values in chunks
    chunk_size = int(5000 / attributes_len)
    # Make sure entity_ids is `list` for chunk selection
    entity_ids = list(entity_ids)
    for idx in range(0, len(entity_ids), chunk_size):
        entity_ids_joined = join_query_keys(
            entity_ids[idx:idx + chunk_size]
        )

        call_expr = [{
            "action": "query",
            "expression": (
                "select value, entity_id from {}"
                " where entity_id in ({}) and configuration_id in ({})"
            ).format(table_name, entity_ids_joined, attributes_joined)
        }]
        if hasattr(session, "call"):
            [result] = session.call(call_expr)
        else:
            [result] = session._call(call_expr)

        for item in result["data"]:
            output.append(item)
    return output
