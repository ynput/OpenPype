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
