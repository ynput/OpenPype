import re
import queue
import collections

import avalon
import avalon.api
from avalon.vendor import toml
from pypeapp import Logger, Anatomy


log = Logger().get_logger(__name__)


# Current schemas for avalon types
entity_schemas = {
    "project": "avalon-core:project-2.0",
    "asset": "avalon-core:asset-3.0",
    "config": "avalon-core:config-1.0"
}

# name of Custom attribute that stores mongo_id from avalon db
cust_attr_id_key = "avalon_mongo_id"
cust_attr_auto_sync = "avalon_auto_sync"


def check_regex(name, entity_type, in_schema=None, schema_patterns=None):
    schema_name = "asset-3.0"
    if in_schema:
        schema_name = in_schema
    elif entity_type == "project":
        schema_name = "project-2.0"
    elif entity_type == "task":
        schema_name = "task"

    name_pattern = None
    if schema_patterns is not None:
        name_pattern = schema_patterns.get(schema_name)

    if not name_pattern:
        default_pattern = "^[a-zA-Z0-9_.]*$"
        schema_obj = avalon.schema._cache.get(schema_name + ".json")
        if not schema_obj:
            name_pattern = default_pattern
        else:
            name_pattern = schema_obj.get(
                "properties", {}).get(
                "name", {}).get(
                "pattern", default_pattern
            )
        if schema_patterns is not None:
            schema_patterns[schema_name] = name_pattern

    if re.match(name_pattern, name):
        return True
    return False


def get_avalon_attr(session, split_hierarchical=True):
    custom_attributes = []
    hier_custom_attributes = []
    cust_attrs_query = (
        "select id, entity_type, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where group.name = \"avalon\""
    )
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


def from_dict_to_set(data):
    result = {"$set": {}}
    dict_queue = queue.Queue()
    dict_queue.put((None, data))

    while not dict_queue.empty():
        _key, _data = dict_queue.get()
        for key, value in _data.items():
            new_key = key
            if _key is not None:
                new_key = "{}.{}".format(_key, key)

            if not isinstance(value, dict):
                result["$set"][new_key] = value
                continue
            dict_queue.put((new_key, value))
    return result


def get_avalon_project_template(project_name):
    """Get avalon template
    Returns:
        dictionary with templates
    """
    templates = Anatomy(project_name).templates
    return {
        "workfile": templates["avalon"]["workfile"],
        "work": templates["avalon"]["work"],
        "publish": templates["avalon"]["publish"]
    }


def get_project_apps(in_app_list):
    apps = []
    # TODO report
    missing_toml_msg = "Missing config file for application"
    error_msg = (
        "Unexpected error happend during preparation of application"
    )
    warnings = collections.defaultdict(list)
    for app in in_app_list:
        try:
            toml_path = avalon.lib.which_app(app)
            if not toml_path:
                log.warning(missing_toml_msg + ' "{}"'.format(app))
                warnings[missing_toml_msg].append(app)
                continue

            apps.append({
                "name": app,
                "label": toml.load(toml_path)["label"]
            })
        except Exception:
            warnings[error_msg].append(app)
            log.warning((
                "Error has happened during preparing application \"{}\""
            ).format(app), exc_info=True)
    return apps, warnings


def get_hierarchical_attributes(session, entity, attr_names, attr_defaults={}):
    entity_ids = []
    if entity.entity_type.lower() == "project":
        entity_ids.append(entity["id"])
    else:
        typed_context = session.query((
            "select ancestors.id, project from TypedContext where id is \"{}\""
        ).format(entity["id"])).one()
        entity_ids.append(typed_context["id"])
        entity_ids.extend(
            [ent["id"] for ent in reversed(typed_context["ancestors"])]
        )
        entity_ids.append(typed_context["project"]["id"])

    missing_defaults = []
    for attr_name in attr_names:
        if attr_name not in attr_defaults:
            missing_defaults.append(attr_name)

    join_ent_ids = ", ".join(
        ["\"{}\"".format(entity_id) for entity_id in entity_ids]
    )
    join_attribute_names = ", ".join(
        ["\"{}\"".format(key) for key in attr_names]
    )
    queries = []
    queries.append({
        "action": "query",
        "expression": (
            "select value, entity_id from CustomAttributeValue "
            "where entity_id in ({}) and configuration.key in ({})"
        ).format(join_ent_ids, join_attribute_names)
    })

    if not missing_defaults:
        if hasattr(session, "call"):
            [values] = session.call(queries)
        else:
            [values] = session._call(queries)
    else:
        join_missing_names = ", ".join(
            ["\"{}\"".format(key) for key in missing_defaults]
        )
        queries.append({
            "action": "query",
            "expression": (
                "select default from CustomAttributeConfiguration "
                "where key in ({})"
            ).format(join_missing_names)
        })

        [values, default_values] = session.call(queries)
        for default_value in default_values:
            key = default_value["data"][0]["key"]
            attr_defaults[key] = default_value["data"][0]["default"]

    hier_values = {}
    for key, val in attr_defaults.items():
        hier_values[key] = val

    if not values["data"]:
        return hier_values

    _hier_values = collections.defaultdict(list)
    for value in values["data"]:
        key = value["configuration"]["key"]
        _hier_values[key].append(value)

    for key, values in _hier_values.items():
        value = sorted(
            values, key=lambda value: entity_ids.index(value["entity_id"])
        )[0]
        hier_values[key] = value["value"]

    return hier_values
