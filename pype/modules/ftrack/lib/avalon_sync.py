import os
import re
import queue
import json
import collections
import copy

from avalon.api import AvalonMongoDB

import avalon
import avalon.api
from avalon.vendor import toml
from pype.api import Logger, Anatomy

from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo import UpdateOne
import ftrack_api


log = Logger().get_logger(__name__)


# Current schemas for avalon types
EntitySchemas = {
    "project": "avalon-core:project-2.0",
    "asset": "avalon-core:asset-3.0",
    "config": "avalon-core:config-1.0"
}

# Group name of custom attributes
CUST_ATTR_GROUP = "pype"

# name of Custom attribute that stores mongo_id from avalon db
CUST_ATTR_ID_KEY = "avalon_mongo_id"
CUST_ATTR_AUTO_SYNC = "avalon_auto_sync"


def default_custom_attributes_definition():
    json_file_path = os.path.join(
        os.path.dirname(__file__), "custom_attributes.json"
    )
    with open(json_file_path, "r") as json_stream:
        data = json.load(json_stream)
    return data


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
            name_pattern = (
                schema_obj
                .get("properties", {})
                .get("name", {})
                .get("pattern", default_pattern)
            )
        if schema_patterns is not None:
            schema_patterns[schema_name] = name_pattern

    if re.match(name_pattern, name):
        return True
    return False


def get_pype_attr(session, split_hierarchical=True):
    custom_attributes = []
    hier_custom_attributes = []
    # TODO remove deprecated "avalon" group from query
    cust_attrs_query = (
        "select id, entity_type, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where group.name in (\"avalon\", \"pype\")"
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


class SyncEntitiesFactory:
    dbcon = AvalonMongoDB()

    project_query = (
        "select full_name, name, custom_attributes"
        ", project_schema._task_type_schema.types.name"
        " from Project where full_name is \"{}\""
    )
    entities_query = (
        "select id, name, parent_id, link"
        " from TypedContext where project_id is \"{}\""
    )
    ignore_custom_attr_key = "avalon_ignore_sync"
    ignore_entity_types = ["milestone"]

    report_splitter = {"type": "label", "value": "---"}

    def __init__(self, log_obj, session):
        self.log = log_obj
        self._server_url = session.server_url
        self._api_key = session.api_key
        self._api_user = session.api_user

    def launch_setup(self, project_full_name):
        try:
            self.session.close()
        except Exception:
            pass

        self.session = ftrack_api.Session(
            server_url=self._server_url,
            api_key=self._api_key,
            api_user=self._api_user,
            auto_connect_event_hub=True
        )

        self.duplicates = {}
        self.failed_regex = {}
        self.tasks_failed_regex = collections.defaultdict(list)
        self.report_items = {
            "info": collections.defaultdict(list),
            "warning": collections.defaultdict(list),
            "error": collections.defaultdict(list)
        }

        self.create_list = []
        self.updates = collections.defaultdict(dict)

        self.avalon_project = None
        self.avalon_entities = None

        self._avalon_ents_by_id = None
        self._avalon_ents_by_ftrack_id = None
        self._avalon_ents_by_name = None
        self._avalon_ents_by_parent_id = None

        self._avalon_archived_ents = None
        self._avalon_archived_by_id = None
        self._avalon_archived_by_parent_id = None
        self._avalon_archived_by_name = None

        self._subsets_by_parent_id = None
        self._changeability_by_mongo_id = None

        self.all_filtered_entities = {}
        self.filtered_ids = []
        self.not_selected_ids = []

        self.hier_cust_attr_ids_by_key = {}

        self._ent_paths_by_ftrack_id = {}

        self.ftrack_avalon_mapper = None
        self.avalon_ftrack_mapper = None
        self.create_ftrack_ids = None
        self.update_ftrack_ids = None
        self.deleted_entities = None

        # Get Ftrack project
        ft_project = self.session.query(
            self.project_query.format(project_full_name)
        ).one()
        ft_project_id = ft_project["id"]

        # Skip if project is ignored
        if ft_project["custom_attributes"].get(
            self.ignore_custom_attr_key
        ) is True:
            msg = (
                "Project \"{}\" has set `Ignore Sync` custom attribute to True"
            ).format(project_full_name)
            self.log.warning(msg)
            return {"success": False, "message": msg}

        self.log.debug((
            "*** Synchronization initialization started <{}>."
        ).format(project_full_name))
        # Check if `avalon_mongo_id` custom attribute exist or is accessible
        if CUST_ATTR_ID_KEY not in ft_project["custom_attributes"]:
            items = []
            items.append({
                "type": "label",
                "value": "# Can't access Custom attribute <{}>".format(
                    CUST_ATTR_ID_KEY
                )
            })
            items.append({
                "type": "label",
                "value": (
                    "<p>- Check if user \"{}\" has permissions"
                    " to access the Custom attribute</p>"
                ).format(self._api_key)
            })
            items.append({
                "type": "label",
                "value": "<p>- Check if the Custom attribute exist</p>"
            })
            return {
                "items": items,
                "title": "Synchronization failed",
                "success": False,
                "message": "Synchronization failed"
            }

        # Find all entities in project
        all_project_entities = self.session.query(
            self.entities_query.format(ft_project_id)
        ).all()

        # Store entities by `id` and `parent_id`
        entities_dict = collections.defaultdict(lambda: {
            "children": list(),
            "parent_id": None,
            "entity": None,
            "entity_type": None,
            "name": None,
            "custom_attributes": {},
            "hier_attrs": {},
            "avalon_attrs": {},
            "tasks": []
        })

        for entity in all_project_entities:
            parent_id = entity["parent_id"]
            entity_type = entity.entity_type
            entity_type_low = entity_type.lower()
            if entity_type_low in self.ignore_entity_types:
                continue

            elif entity_type_low == "task":
                entities_dict[parent_id]["tasks"].append(entity["name"])
                continue

            entity_id = entity["id"]
            entities_dict[entity_id].update({
                "entity": entity,
                "parent_id": parent_id,
                "entity_type": entity_type_low,
                "entity_type_orig": entity_type,
                "name": entity["name"]
            })
            entities_dict[parent_id]["children"].append(entity_id)

        entities_dict[ft_project_id]["entity"] = ft_project
        entities_dict[ft_project_id]["entity_type"] = (
            ft_project.entity_type.lower()
        )
        entities_dict[ft_project_id]["entity_type_orig"] = (
            ft_project.entity_type
        )
        entities_dict[ft_project_id]["name"] = ft_project["full_name"]

        self.ft_project_id = ft_project_id
        self.entities_dict = entities_dict

    @property
    def avalon_ents_by_id(self):
        if self._avalon_ents_by_id is None:
            self._avalon_ents_by_id = {}
            for entity in self.avalon_entities:
                self._avalon_ents_by_id[str(entity["_id"])] = entity

        return self._avalon_ents_by_id

    @property
    def avalon_ents_by_ftrack_id(self):
        if self._avalon_ents_by_ftrack_id is None:
            self._avalon_ents_by_ftrack_id = {}
            for entity in self.avalon_entities:
                key = entity.get("data", {}).get("ftrackId")
                if not key:
                    continue
                self._avalon_ents_by_ftrack_id[key] = str(entity["_id"])

        return self._avalon_ents_by_ftrack_id

    @property
    def avalon_ents_by_name(self):
        if self._avalon_ents_by_name is None:
            self._avalon_ents_by_name = {}
            for entity in self.avalon_entities:
                self._avalon_ents_by_name[entity["name"]] = str(entity["_id"])

        return self._avalon_ents_by_name

    @property
    def avalon_ents_by_parent_id(self):
        if self._avalon_ents_by_parent_id is None:
            self._avalon_ents_by_parent_id = collections.defaultdict(list)
            for entity in self.avalon_entities:
                parent_id = entity["data"]["visualParent"]
                if parent_id is not None:
                    parent_id = str(parent_id)
                self._avalon_ents_by_parent_id[parent_id].append(entity)

        return self._avalon_ents_by_parent_id

    @property
    def avalon_archived_ents(self):
        if self._avalon_archived_ents is None:
            self._avalon_archived_ents = [
                ent for ent in self.dbcon.find({"type": "archived_asset"})
            ]
        return self._avalon_archived_ents

    @property
    def avalon_archived_by_name(self):
        if self._avalon_archived_by_name is None:
            self._avalon_archived_by_name = collections.defaultdict(list)
            for ent in self.avalon_archived_ents:
                self._avalon_archived_by_name[ent["name"]].append(ent)
        return self._avalon_archived_by_name

    @property
    def avalon_archived_by_id(self):
        if self._avalon_archived_by_id is None:
            self._avalon_archived_by_id = {
                str(ent["_id"]): ent for ent in self.avalon_archived_ents
            }
        return self._avalon_archived_by_id

    @property
    def avalon_archived_by_parent_id(self):
        if self._avalon_archived_by_parent_id is None:
            self._avalon_archived_by_parent_id = collections.defaultdict(list)
            for entity in self.avalon_archived_ents:
                parent_id = entity["data"]["visualParent"]
                if parent_id is not None:
                    parent_id = str(parent_id)
                self._avalon_archived_by_parent_id[parent_id].append(entity)

        return self._avalon_archived_by_parent_id

    @property
    def subsets_by_parent_id(self):
        if self._subsets_by_parent_id is None:
            self._subsets_by_parent_id = collections.defaultdict(list)
            for subset in self.dbcon.find({"type": "subset"}):
                self._subsets_by_parent_id[str(subset["parent"])].append(
                    subset
                )

        return self._subsets_by_parent_id

    @property
    def changeability_by_mongo_id(self):
        if self._changeability_by_mongo_id is None:
            self._changeability_by_mongo_id = collections.defaultdict(
                lambda: True
            )
            self._changeability_by_mongo_id[self.avalon_project_id] = False
            self._bubble_changeability(list(self.subsets_by_parent_id.keys()))
        return self._changeability_by_mongo_id

    @property
    def all_ftrack_names(self):
        return [
            ent_dict["name"] for ent_dict in self.entities_dict.values() if (
                ent_dict.get("name")
            )
        ]

    def duplicity_regex_check(self):
        self.log.debug("* Checking duplicities and invalid symbols")
        # Duplicity and regex check
        entity_ids_by_name = {}
        duplicates = []
        failed_regex = []
        task_names = {}
        _schema_patterns = {}
        for ftrack_id, entity_dict in self.entities_dict.items():
            regex_check = True
            name = entity_dict["name"]
            entity_type = entity_dict["entity_type"]
            # Tasks must be checked too
            for task_name in entity_dict["tasks"]:
                passed = task_names.get(task_name)
                if passed is None:
                    passed = check_regex(
                        task_name, "task", schema_patterns=_schema_patterns
                    )
                    task_names[task_name] = passed

                if not passed:
                    self.tasks_failed_regex[task_name].append(ftrack_id)

            if name in entity_ids_by_name:
                duplicates.append(name)
            else:
                entity_ids_by_name[name] = []
                regex_check = check_regex(
                    name, entity_type, schema_patterns=_schema_patterns
                )

            entity_ids_by_name[name].append(ftrack_id)
            if not regex_check:
                failed_regex.append(name)

        for name in failed_regex:
            self.failed_regex[name] = entity_ids_by_name[name]

        for name in duplicates:
            self.duplicates[name] = entity_ids_by_name[name]

        self.filter_by_duplicate_regex()

    def filter_by_duplicate_regex(self):
        filter_queue = queue.Queue()
        failed_regex_msg = "{} - Entity has invalid symbols in the name"
        duplicate_msg = "There are multiple entities with the name: \"{}\":"

        for ids in self.failed_regex.values():
            for id in ids:
                ent_path = self.get_ent_path(id)
                self.log.warning(failed_regex_msg.format(ent_path))
                filter_queue.put(id)

        for name, ids in self.duplicates.items():
            self.log.warning(duplicate_msg.format(name))
            for id in ids:
                ent_path = self.get_ent_path(id)
                self.log.warning(ent_path)
                filter_queue.put(id)

        filtered_ids = []
        while not filter_queue.empty():
            ftrack_id = filter_queue.get()
            if ftrack_id in filtered_ids:
                continue

            entity_dict = self.entities_dict.pop(ftrack_id, {})
            if not entity_dict:
                continue

            self.all_filtered_entities[ftrack_id] = entity_dict
            parent_id = entity_dict.get("parent_id")
            if parent_id and parent_id in self.entities_dict:
                if ftrack_id in self.entities_dict[parent_id]["children"]:
                    self.entities_dict[parent_id]["children"].remove(ftrack_id)

            filtered_ids.append(ftrack_id)
            for child_id in entity_dict.get("children", []):
                filter_queue.put(child_id)

        for name, ids in self.tasks_failed_regex.items():
            for id in ids:
                if id not in self.entities_dict:
                    continue
                self.entities_dict[id]["tasks"].remove(name)
                ent_path = self.get_ent_path(id)
                self.log.warning(failed_regex_msg.format(
                    "/".join([ent_path, name])
                ))

    def filter_by_ignore_sync(self):
        # skip filtering if `ignore_sync` attribute do not exist
        if self.entities_dict[self.ft_project_id]["avalon_attrs"].get(
            self.ignore_custom_attr_key, "_notset_"
        ) == "_notset_":
            return

        self.filter_queue = queue.Queue()
        self.filter_queue.put((self.ft_project_id, False))
        while not self.filter_queue.empty():
            parent_id, remove = self.filter_queue.get()
            if remove:
                parent_dict = self.entities_dict.pop(parent_id, {})
                self.all_filtered_entities[parent_id] = parent_dict
                self.filtered_ids.append(parent_id)
            else:
                parent_dict = self.entities_dict.get(parent_id, {})

            for child_id in parent_dict.get("children", []):
                # keep original `remove` value for all childs
                _remove = (remove is True)
                if not _remove:
                    if self.entities_dict[child_id]["avalon_attrs"].get(
                        self.ignore_custom_attr_key
                    ):
                        self.entities_dict[parent_id]["children"].remove(
                            child_id
                        )
                        _remove = True
                self.filter_queue.put((child_id, _remove))

    def filter_by_selection(self, event):
        # BUGGY!!!! cause that entities are in deleted list
        # TODO may be working when filtering happen after preparations
        # - But this part probably does not have any functional reason
        #   - Time of synchronization probably won't be changed much
        selected_ids = []
        for entity in event["data"]["selection"]:
            # Skip if project is in selection
            if entity["entityType"] == "show":
                return
            selected_ids.append(entity["entityId"])

        sync_ids = [self.ft_project_id]
        parents_queue = queue.Queue()
        children_queue = queue.Queue()
        for id in selected_ids:
            # skip if already filtered with ignore sync custom attribute
            if id in self.filtered_ids:
                continue

            parents_queue.put(id)
            children_queue.put(id)

        while not parents_queue.empty():
            id = parents_queue.get()
            while True:
                # Stops when parent is in sync_ids
                if id in self.filtered_ids or id in sync_ids or id is None:
                    break
                sync_ids.append(id)
                id = self.entities_dict[id]["parent_id"]

        while not children_queue.empty():
            parent_id = children_queue.get()
            for child_id in self.entities_dict[parent_id]["children"]:
                if child_id in sync_ids or child_id in self.filtered_ids:
                    continue
                sync_ids.append(child_id)
                children_queue.put(child_id)

        # separate not selected and to process entities
        for key, value in self.entities_dict.items():
            if key not in sync_ids:
                self.not_selected_ids.append(key)

        for id in self.not_selected_ids:
            # pop from entities
            value = self.entities_dict.pop(id)
            # remove entity from parent's children
            parent_id = value["parent_id"]
            if parent_id not in sync_ids:
                continue

            self.entities_dict[parent_id]["children"].remove(id)

    def set_cutom_attributes(self):
        self.log.debug("* Preparing custom attributes")
        # Get custom attributes and values
        custom_attrs, hier_attrs = get_pype_attr(self.session)
        ent_types = self.session.query("select id, name from ObjectType").all()
        ent_types_by_name = {
            ent_type["name"]: ent_type["id"] for ent_type in ent_types
        }

        # store default values per entity type
        attrs_per_entity_type = collections.defaultdict(dict)
        avalon_attrs = collections.defaultdict(dict)
        # store also custom attribute configuration id for future use (create)
        attrs_per_entity_type_ca_id = collections.defaultdict(dict)
        avalon_attrs_ca_id = collections.defaultdict(dict)

        attribute_key_by_id = {}
        for cust_attr in custom_attrs:
            key = cust_attr["key"]
            attribute_key_by_id[cust_attr["id"]] = key
            ca_ent_type = cust_attr["entity_type"]
            if key.startswith("avalon_"):
                if ca_ent_type == "show":
                    avalon_attrs[ca_ent_type][key] = cust_attr["default"]
                    avalon_attrs_ca_id[ca_ent_type][key] = cust_attr["id"]
                elif ca_ent_type == "task":
                    obj_id = cust_attr["object_type_id"]
                    avalon_attrs[obj_id][key] = cust_attr["default"]
                    avalon_attrs_ca_id[obj_id][key] = cust_attr["id"]
                continue

            if ca_ent_type == "show":
                attrs_per_entity_type[ca_ent_type][key] = cust_attr["default"]
                attrs_per_entity_type_ca_id[ca_ent_type][key] = cust_attr["id"]
            elif ca_ent_type == "task":
                obj_id = cust_attr["object_type_id"]
                attrs_per_entity_type[obj_id][key] = cust_attr["default"]
                attrs_per_entity_type_ca_id[obj_id][key] = cust_attr["id"]

        obj_id_ent_type_map = {}
        sync_ids = []
        for entity_id, entity_dict in self.entities_dict.items():
            sync_ids.append(entity_id)
            entity_type = entity_dict["entity_type"]
            entity_type_orig = entity_dict["entity_type_orig"]

            if entity_type == "project":
                attr_key = "show"
            else:
                map_key = obj_id_ent_type_map.get(entity_type_orig)
                if not map_key:
                    # Put space between capitals
                    # (e.g. 'AssetBuild' -> 'Asset Build')
                    map_key = re.sub(
                        r"(\w)([A-Z])", r"\1 \2", entity_type_orig
                    )
                    obj_id_ent_type_map[entity_type_orig] = map_key

                # Get object id of entity type
                attr_key = ent_types_by_name.get(map_key)

                # Backup soluction when id is not found by prequeried objects
                if not attr_key:
                    query = "ObjectType where name is \"{}\"".format(map_key)
                    attr_key = self.session.query(query).one()["id"]
                    ent_types_by_name[map_key] = attr_key

            prepared_attrs = attrs_per_entity_type.get(attr_key)
            prepared_avalon_attr = avalon_attrs.get(attr_key)
            prepared_attrs_ca_id = attrs_per_entity_type_ca_id.get(attr_key)
            prepared_avalon_attr_ca_id = avalon_attrs_ca_id.get(attr_key)
            if prepared_attrs:
                self.entities_dict[entity_id]["custom_attributes"] = (
                    copy.deepcopy(prepared_attrs)
                )
            if prepared_attrs_ca_id:
                self.entities_dict[entity_id]["custom_attributes_id"] = (
                    copy.deepcopy(prepared_attrs_ca_id)
                )
            if prepared_avalon_attr:
                self.entities_dict[entity_id]["avalon_attrs"] = (
                    copy.deepcopy(prepared_avalon_attr)
                )
            if prepared_avalon_attr_ca_id:
                self.entities_dict[entity_id]["avalon_attrs_id"] = (
                    copy.deepcopy(prepared_avalon_attr_ca_id)
                )

        # TODO query custom attributes by entity_id
        entity_ids_joined = ", ".join([
            "\"{}\"".format(id) for id in sync_ids
        ])
        attributes_joined = ", ".join([
            "\"{}\"".format(attr_id) for attr_id in attribute_key_by_id.keys()
        ])

        cust_attr_query = (
            "select value, entity_id from ContextCustomAttributeValue "
            "where entity_id in ({}) and configuration_id in ({})"
        )
        call_expr = [{
            "action": "query",
            "expression": cust_attr_query.format(
                entity_ids_joined, attributes_joined
            )
        }]
        if hasattr(self.session, "call"):
            [values] = self.session.call(call_expr)
        else:
            [values] = self.session._call(call_expr)

        for item in values["data"]:
            entity_id = item["entity_id"]
            key = attribute_key_by_id[item["configuration_id"]]
            store_key = "custom_attributes"
            if key.startswith("avalon_"):
                store_key = "avalon_attrs"
            self.entities_dict[entity_id][store_key][key] = item["value"]

        # process hierarchical attributes
        self.set_hierarchical_attribute(hier_attrs, sync_ids)

    def set_hierarchical_attribute(self, hier_attrs, sync_ids):
        # collect all hierarchical attribute keys
        # and prepare default values to project
        attributes_by_key = {}
        attribute_key_by_id = {}
        for attr in hier_attrs:
            key = attr["key"]
            attribute_key_by_id[attr["id"]] = key
            attributes_by_key[key] = attr
            self.hier_cust_attr_ids_by_key[key] = attr["id"]

            store_key = "hier_attrs"
            if key.startswith("avalon_"):
                store_key = "avalon_attrs"

            self.entities_dict[self.ft_project_id][store_key][key] = (
                attr["default"]
            )

        # Add attribute ids to entities dictionary
        avalon_attribute_id_by_key = {
            attr_key: attr_id
            for attr_id, attr_key in attribute_key_by_id.items()
            if attr_key.startswith("avalon_")
        }
        for entity_id in self.entities_dict.keys():
            if "avalon_attrs_id" not in self.entities_dict[entity_id]:
                self.entities_dict[entity_id]["avalon_attrs_id"] = {}

            for attr_key, attr_id in avalon_attribute_id_by_key.items():
                self.entities_dict[entity_id]["avalon_attrs_id"][attr_key] = (
                    attr_id
                )

        # Prepare dict with all hier keys and None values
        prepare_dict = {}
        prepare_dict_avalon = {}
        for key in attributes_by_key.keys():
            if key.startswith("avalon_"):
                prepare_dict_avalon[key] = None
            else:
                prepare_dict[key] = None

        for id, entity_dict in self.entities_dict.items():
            # Skip project because has stored defaults at the moment
            if entity_dict["entity_type"] == "project":
                continue
            entity_dict["hier_attrs"] = copy.deepcopy(prepare_dict)
            for key, val in prepare_dict_avalon.items():
                entity_dict["avalon_attrs"][key] = val

        # Prepare values to query
        entity_ids_joined = ", ".join([
            "\"{}\"".format(id) for id in sync_ids
        ])
        attributes_joined = ", ".join([
            "\"{}\"".format(attr_id) for attr_id in attribute_key_by_id.keys()
        ])
        avalon_hier = []
        call_expr = [{
            "action": "query",
            "expression": (
                "select value, entity_id from ContextCustomAttributeValue "
                "where entity_id in ({}) and configuration_id in ({})"
            ).format(entity_ids_joined, attributes_joined)
        }]
        if hasattr(self.session, "call"):
            [values] = self.session.call(call_expr)
        else:
            [values] = self.session._call(call_expr)

        for item in values["data"]:
            value = item["value"]
            # WARNING It is not possible to propage enumerate hierachical
            # attributes with multiselection 100% right. Unseting all values
            # will cause inheritance from parent.
            if (
                value is None
                or (isinstance(value, (tuple, list)) and not value)
            ):
                continue
            entity_id = item["entity_id"]
            key = attribute_key_by_id[item["configuration_id"]]
            if key.startswith("avalon_"):
                store_key = "avalon_attrs"
                avalon_hier.append(key)
            else:
                store_key = "hier_attrs"
            self.entities_dict[entity_id][store_key][key] = value

        # Get dictionary with not None hierarchical values to pull to childs
        top_id = self.ft_project_id
        project_values = {}
        for key, value in self.entities_dict[top_id]["hier_attrs"].items():
            if value is not None:
                project_values[key] = value

        for key in avalon_hier:
            if key == CUST_ATTR_ID_KEY:
                continue
            value = self.entities_dict[top_id]["avalon_attrs"][key]
            if value is not None:
                project_values[key] = value

        hier_down_queue = queue.Queue()
        hier_down_queue.put((project_values, top_id))

        while not hier_down_queue.empty():
            hier_values, parent_id = hier_down_queue.get()
            for child_id in self.entities_dict[parent_id]["children"]:
                _hier_values = copy.deepcopy(hier_values)
                for key in attributes_by_key.keys():
                    if key.startswith("avalon_"):
                        store_key = "avalon_attrs"
                    else:
                        store_key = "hier_attrs"
                    value = self.entities_dict[child_id][store_key][key]
                    if value is not None:
                        _hier_values[key] = value

                self.entities_dict[child_id]["hier_attrs"].update(_hier_values)
                hier_down_queue.put((_hier_values, child_id))

    def remove_from_archived(self, mongo_id):
        entity = self.avalon_archived_by_id.pop(mongo_id, None)
        if not entity:
            return

        if self._avalon_archived_ents is not None:
            if entity in self._avalon_archived_ents:
                self._avalon_archived_ents.remove(entity)

        if self._avalon_archived_by_name is not None:
            name = entity["name"]
            if name in self._avalon_archived_by_name:
                name_ents = self._avalon_archived_by_name[name]
                if entity in name_ents:
                    if len(name_ents) == 1:
                        self._avalon_archived_by_name.pop(name)
                    else:
                        self._avalon_archived_by_name[name].remove(entity)

        # TODO use custom None instead of __NOTSET__
        if self._avalon_archived_by_parent_id is not None:
            parent_id = entity.get("data", {}).get(
                "visualParent", "__NOTSET__"
            )
            if parent_id is not None:
                parent_id = str(parent_id)

            if parent_id in self._avalon_archived_by_parent_id:
                parent_list = self._avalon_archived_by_parent_id[parent_id]
                if entity not in parent_list:
                    self._avalon_archived_by_parent_id[parent_id].remove(
                        entity
                    )

    def prepare_ftrack_ent_data(self):
        not_set_ids = []
        for id, entity_dict in self.entities_dict.items():
            entity = entity_dict["entity"]
            if entity is None:
                not_set_ids.append(id)
                continue

            self.entities_dict[id]["final_entity"] = {}
            self.entities_dict[id]["final_entity"]["name"] = (
                entity_dict["name"]
            )
            data = {}
            data["ftrackId"] = entity["id"]
            data["entityType"] = entity_dict["entity_type_orig"]

            for key, val in entity_dict.get("custom_attributes", []).items():
                data[key] = val

            for key, val in entity_dict.get("hier_attrs", []).items():
                data[key] = val

            if id == self.ft_project_id:
                data["code"] = entity["name"]
                self.entities_dict[id]["final_entity"]["data"] = data
                self.entities_dict[id]["final_entity"]["type"] = "project"

                proj_schema = entity["project_schema"]
                task_types = proj_schema["_task_type_schema"]["types"]
                proj_apps, warnings = get_project_apps(
                    (data.get("applications") or [])
                )
                for msg, items in warnings.items():
                    if not msg or not items:
                        continue
                    self.report_items["warning"][msg] = items

                self.entities_dict[id]["final_entity"]["config"] = {
                    "tasks": [{"name": tt["name"]} for tt in task_types],
                    "apps": proj_apps
                }
                continue

            ent_path_items = [ent["name"] for ent in entity["link"]]
            parents = ent_path_items[1:len(ent_path_items)-1:]
            hierarchy = ""
            if len(parents) > 0:
                hierarchy = os.path.sep.join(parents)

            data["parents"] = parents
            data["hierarchy"] = hierarchy
            data["tasks"] = self.entities_dict[id].pop("tasks", [])
            self.entities_dict[id]["final_entity"]["data"] = data
            self.entities_dict[id]["final_entity"]["type"] = "asset"

        if not_set_ids:
            self.log.debug((
                "- Debug information: Filtering bug, there are empty dicts"
                "in entities dict (functionality should not be affected) <{}>"
            ).format("| ".join(not_set_ids)))
            for id in not_set_ids:
                self.entities_dict.pop(id)

    def get_ent_path(self, ftrack_id):
        ent_path = self._ent_paths_by_ftrack_id.get(ftrack_id)
        if not ent_path:
            entity = self.entities_dict[ftrack_id]["entity"]
            ent_path = "/".join(
                [ent["name"] for ent in entity["link"]]
            )
            self._ent_paths_by_ftrack_id[ftrack_id] = ent_path

        return ent_path

    def prepare_avalon_entities(self, ft_project_name):
        self.log.debug((
            "* Preparing avalon entities "
            "(separate to Create, Update and Deleted groups)"
        ))
        # Avalon entities
        self.dbcon.install()
        self.dbcon.Session["AVALON_PROJECT"] = ft_project_name
        avalon_project = self.dbcon.find_one({"type": "project"})
        avalon_entities = self.dbcon.find({"type": "asset"})
        self.avalon_project = avalon_project
        self.avalon_entities = avalon_entities

        ftrack_avalon_mapper = {}
        avalon_ftrack_mapper = {}
        create_ftrack_ids = []
        update_ftrack_ids = []

        same_mongo_id = []
        all_mongo_ids = {}
        for ftrack_id, entity_dict in self.entities_dict.items():
            mongo_id = entity_dict["avalon_attrs"].get(CUST_ATTR_ID_KEY)
            if not mongo_id:
                continue
            if mongo_id in all_mongo_ids:
                same_mongo_id.append(mongo_id)
            else:
                all_mongo_ids[mongo_id] = []
            all_mongo_ids[mongo_id].append(ftrack_id)

        if avalon_project:
            mongo_id = str(avalon_project["_id"])
            ftrack_avalon_mapper[self.ft_project_id] = mongo_id
            avalon_ftrack_mapper[mongo_id] = self.ft_project_id
            update_ftrack_ids.append(self.ft_project_id)
        else:
            create_ftrack_ids.append(self.ft_project_id)

        # make it go hierarchically
        prepare_queue = queue.Queue()

        for child_id in self.entities_dict[self.ft_project_id]["children"]:
            prepare_queue.put(child_id)

        while not prepare_queue.empty():
            ftrack_id = prepare_queue.get()
            for child_id in self.entities_dict[ftrack_id]["children"]:
                prepare_queue.put(child_id)

            entity_dict = self.entities_dict[ftrack_id]
            ent_path = self.get_ent_path(ftrack_id)

            mongo_id = entity_dict["avalon_attrs"].get(CUST_ATTR_ID_KEY)
            av_ent_by_mongo_id = self.avalon_ents_by_id.get(mongo_id)
            if av_ent_by_mongo_id:
                av_ent_ftrack_id = av_ent_by_mongo_id.get("data", {}).get(
                    "ftrackId"
                )
                is_right = False
                else_match_better = False
                if av_ent_ftrack_id and av_ent_ftrack_id == ftrack_id:
                    is_right = True

                elif mongo_id not in same_mongo_id:
                    is_right = True

                else:
                    ftrack_ids_with_same_mongo = all_mongo_ids[mongo_id]
                    for _ftrack_id in ftrack_ids_with_same_mongo:
                        if _ftrack_id == av_ent_ftrack_id:
                            continue

                        _entity_dict = self.entities_dict[_ftrack_id]
                        _mongo_id = (
                            _entity_dict["avalon_attrs"][CUST_ATTR_ID_KEY]
                        )
                        _av_ent_by_mongo_id = self.avalon_ents_by_id.get(
                            _mongo_id
                        )
                        _av_ent_ftrack_id = _av_ent_by_mongo_id.get(
                            "data", {}
                        ).get("ftrackId")
                        if _av_ent_ftrack_id == ftrack_id:
                            else_match_better = True
                            break

                if not is_right and not else_match_better:
                    entity = entity_dict["entity"]
                    ent_path_items = [ent["name"] for ent in entity["link"]]
                    parents = ent_path_items[1:len(ent_path_items)-1:]
                    av_parents = av_ent_by_mongo_id["data"]["parents"]
                    if av_parents == parents:
                        is_right = True
                    else:
                        name = entity_dict["name"]
                        av_name = av_ent_by_mongo_id["name"]
                        if name == av_name:
                            is_right = True

                if is_right:
                    self.log.debug(
                        "Existing (by MongoID) <{}>".format(ent_path)
                    )
                    ftrack_avalon_mapper[ftrack_id] = mongo_id
                    avalon_ftrack_mapper[mongo_id] = ftrack_id
                    update_ftrack_ids.append(ftrack_id)
                    continue

            mongo_id = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not mongo_id:
                mongo_id = self.avalon_ents_by_name.get(entity_dict["name"])
                if mongo_id:
                    self.log.debug(
                        "Existing (by matching name) <{}>".format(ent_path)
                    )
            else:
                self.log.debug(
                    "Existing (by FtrackID in mongo) <{}>".format(ent_path)
                )

            if mongo_id:
                ftrack_avalon_mapper[ftrack_id] = mongo_id
                avalon_ftrack_mapper[mongo_id] = ftrack_id
                update_ftrack_ids.append(ftrack_id)
                continue

            self.log.debug("New <{}>".format(ent_path))
            create_ftrack_ids.append(ftrack_id)

        deleted_entities = []
        for mongo_id in self.avalon_ents_by_id:
            if mongo_id in avalon_ftrack_mapper:
                continue
            deleted_entities.append(mongo_id)

            av_ent = self.avalon_ents_by_id[mongo_id]
            av_ent_path_items = [p for p in av_ent["data"]["parents"]]
            av_ent_path_items.append(av_ent["name"])
            self.log.debug("Deleted <{}>".format("/".join(av_ent_path_items)))

        self.ftrack_avalon_mapper = ftrack_avalon_mapper
        self.avalon_ftrack_mapper = avalon_ftrack_mapper
        self.create_ftrack_ids = create_ftrack_ids
        self.update_ftrack_ids = update_ftrack_ids
        self.deleted_entities = deleted_entities

        self.log.debug((
            "Ftrack -> Avalon comparison: New <{}> "
            "| Existing <{}> | Deleted <{}>"
        ).format(
            len(create_ftrack_ids),
            len(update_ftrack_ids),
            len(deleted_entities)
        ))

    def filter_with_children(self, ftrack_id):
        if ftrack_id not in self.entities_dict:
            return
        ent_dict = self.entities_dict[ftrack_id]
        parent_id = ent_dict["parent_id"]
        self.entities_dict[parent_id]["children"].remove(ftrack_id)

        children_queue = queue.Queue()
        children_queue.put(ftrack_id)
        while not children_queue.empty():
            _ftrack_id = children_queue.get()
            entity_dict = self.entities_dict.pop(_ftrack_id, {"children": []})
            for child_id in entity_dict["children"]:
                children_queue.put(child_id)

    def prepare_changes(self):
        self.log.debug("* Preparing changes for avalon/ftrack")
        hierarchy_changing_ids = []
        ignore_keys = collections.defaultdict(list)

        update_queue = queue.Queue()
        for ftrack_id in self.update_ftrack_ids:
            update_queue.put(ftrack_id)

        while not update_queue.empty():
            ftrack_id = update_queue.get()
            if ftrack_id == self.ft_project_id:
                changes = self.prepare_project_changes()
                if changes:
                    self.updates[self.avalon_project_id] = changes
                continue

            ftrack_ent_dict = self.entities_dict[ftrack_id]

            # *** check parents
            parent_check = False

            ftrack_parent_id = ftrack_ent_dict["parent_id"]
            avalon_id = self.ftrack_avalon_mapper[ftrack_id]
            avalon_entity = self.avalon_ents_by_id[avalon_id]
            avalon_parent_id = avalon_entity["data"]["visualParent"]
            if avalon_parent_id is not None:
                avalon_parent_id = str(avalon_parent_id)

            ftrack_parent_mongo_id = self.ftrack_avalon_mapper[
                ftrack_parent_id
            ]

            # if parent is project
            if (ftrack_parent_mongo_id == avalon_parent_id) or (
                ftrack_parent_id == self.ft_project_id and
                avalon_parent_id is None
            ):
                parent_check = True

            # check name
            ftrack_name = ftrack_ent_dict["name"]
            avalon_name = avalon_entity["name"]
            name_check = ftrack_name == avalon_name

            # IDEAL STATE: both parent and name check passed
            if parent_check and name_check:
                continue

            # If entity is changeable then change values of parent or name
            if self.changeability_by_mongo_id[avalon_id]:
                # TODO logging
                if not parent_check:
                    if ftrack_parent_mongo_id == str(self.avalon_project_id):
                        new_parent_name = self.entities_dict[
                            self.ft_project_id]["name"]
                        new_parent_id = None
                    else:
                        new_parent_name = self.avalon_ents_by_id[
                            ftrack_parent_mongo_id]["name"]
                        new_parent_id = ObjectId(ftrack_parent_mongo_id)

                    if avalon_parent_id == str(self.avalon_project_id):
                        old_parent_name = self.entities_dict[
                            self.ft_project_id]["name"]
                    else:
                        old_parent_name = self.avalon_ents_by_id[
                            ftrack_parent_mongo_id]["name"]

                    self.updates[avalon_id]["data"] = {
                        "visualParent": new_parent_id
                    }
                    ignore_keys[ftrack_id].append("data.visualParent")
                    self.log.debug((
                        "Avalon entity \"{}\" changed parent \"{}\" -> \"{}\""
                    ).format(avalon_name, old_parent_name, new_parent_name))

                if not name_check:
                    self.updates[avalon_id]["name"] = ftrack_name
                    ignore_keys[ftrack_id].append("name")
                    self.log.debug(
                        "Avalon entity \"{}\" was renamed to \"{}\"".format(
                            avalon_name, ftrack_name
                        )
                    )
                continue

            # parents and hierarchy must be recalculated
            hierarchy_changing_ids.append(ftrack_id)

            # Parent is project if avalon_parent_id is set to None
            if avalon_parent_id is None:
                avalon_parent_id = str(self.avalon_project_id)

            if not name_check:
                ent_path = self.get_ent_path(ftrack_id)
                # TODO report
                # TODO logging
                self.entities_dict[ftrack_id]["name"] = avalon_name
                self.entities_dict[ftrack_id]["entity"]["name"] = (
                    avalon_name
                )
                self.entities_dict[ftrack_id]["final_entity"]["name"] = (
                    avalon_name
                )
                self.log.warning("Name was changed back to {} <{}>".format(
                    avalon_name, ent_path
                ))
                self._ent_paths_by_ftrack_id.pop(ftrack_id, None)
                msg = (
                    "<Entity renamed back> It is not possible to change"
                    " the name of an entity or it's parents, "
                    " if it already contained published data."
                )
                self.report_items["warning"][msg].append(ent_path)

            # skip parent oricessing if hierarchy didn't change
            if parent_check:
                continue

            # Logic when parenting(hierarchy) has changed and should not
            old_ftrack_parent_id = self.avalon_ftrack_mapper.get(
                avalon_parent_id
            )

            # If last ftrack parent id from mongo entity exist then just
            # remap paren_id on entity
            if old_ftrack_parent_id:
                # TODO report
                # TODO logging
                ent_path = self.get_ent_path(ftrack_id)
                msg = (
                    "<Entity moved back in hierachy> It is not possible"
                    " to change the hierarchy of an entity or it's parents,"
                    " if it already contained published data."
                )
                self.report_items["warning"][msg].append(ent_path)
                self.log.warning((
                    " Entity contains published data so it was moved"
                    " back to it's original hierarchy <{}>"
                ).format(ent_path))
                self.entities_dict[ftrack_id]["entity"]["parent_id"] = (
                    old_ftrack_parent_id
                )
                self.entities_dict[ftrack_id]["parent_id"] = (
                    old_ftrack_parent_id
                )
                self.entities_dict[old_ftrack_parent_id][
                    "children"
                ].append(ftrack_id)

                continue

            old_parent_ent = self.avalon_ents_by_id.get(avalon_parent_id)
            if not old_parent_ent:
                old_parent_ent = self.avalon_archived_by_id.get(
                    avalon_parent_id
                )

            # TODO report
            # TODO logging
            if not old_parent_ent:
                self.log.warning((
                    "Parent entity was not found by id"
                    " - Trying to find by parent name"
                ))
                ent_path = self.get_ent_path(ftrack_id)

                parents = avalon_entity["data"]["parents"]
                parent_name = parents[-1]
                matching_entity_id = None
                for id, entity_dict in self.entities_dict.items():
                    if entity_dict["name"] == parent_name:
                        matching_entity_id = id
                        break

                if matching_entity_id is None:
                    # TODO logging
                    # TODO report (turn off auto-sync?)
                    self.log.error((
                        "The entity contains published data but it was moved"
                        " to a different place in the hierarchy and it's"
                        " previous parent cannot be found."
                        " It's impossible to solve this programmatically <{}>"
                    ).format(ent_path))
                    msg = (
                        "<Entity can't be synchronised> Hierarchy of an entity"
                        " can't be changed due to published data and missing"
                        " previous parent"
                    )
                    self.report_items["error"][msg].append(ent_path)
                    self.filter_with_children(ftrack_id)
                    continue

                matching_ent_dict = self.entities_dict.get(matching_entity_id)
                match_ent_parents = matching_ent_dict.get(
                    "final_entity", {}).get(
                    "data", {}).get(
                    "parents", ["__NOTSET__"]
                )
                # TODO logging
                # TODO report
                if (
                    len(match_ent_parents) >= len(parents) or
                    match_ent_parents[:-1] != parents
                ):
                    ent_path = self.get_ent_path(ftrack_id)
                    self.log.error((
                        "The entity contains published data but it was moved"
                        " to a different place in the hierarchy and it's"
                        " previous parents were moved too."
                        " It's impossible to solve this programmatically <{}>"
                    ).format(ent_path))
                    msg = (
                        "<Entity not synchronizable> Hierarchy of an entity"
                        " can't be changed due to published data and scrambled"
                        "hierarchy"
                    )
                    continue

                old_parent_ent = matching_ent_dict["final_entity"]

            parent_id = self.ft_project_id
            entities_to_create = []
            # TODO logging
            self.log.warning(
                "Ftrack entities must be recreated because they were deleted,"
                " but they contain published data."
            )

            _avalon_ent = old_parent_ent

            self.updates[avalon_parent_id] = {"type": "asset"}
            success = True
            while True:
                _vis_par = _avalon_ent["data"]["visualParent"]
                _name = _avalon_ent["name"]
                if _name in self.all_ftrack_names:
                    av_ent_path_items = _avalon_ent["data"]["parents"]
                    av_ent_path_items.append(_name)
                    av_ent_path = "/".join(av_ent_path_items)
                    # TODO report
                    # TODO logging
                    self.log.error((
                        "Can't recreate the entity in Ftrack because an entity"
                        " with the same name already exists in a different"
                        " place in the hierarchy <{}>"
                    ).format(av_ent_path))
                    msg = (
                        "<Entity not synchronizable> Hierarchy of an entity"
                        " can't be changed. I contains published data and it's"
                        " previous parent had a name, that is duplicated at a "
                        " different hierarchy level"
                    )
                    self.report_items["error"][msg].append(av_ent_path)
                    self.filter_with_children(ftrack_id)
                    success = False
                    break

                entities_to_create.append(_avalon_ent)
                if _vis_par is None:
                    break

                _vis_par = str(_vis_par)
                _mapped = self.avalon_ftrack_mapper.get(_vis_par)
                if _mapped:
                    parent_id = _mapped
                    break

                _avalon_ent = self.avalon_ents_by_id.get(_vis_par)
                if not _avalon_ent:
                    _avalon_ent = self.avalon_archived_by_id.get(_vis_par)

            if success is False:
                continue

            new_entity_id = None
            for av_entity in reversed(entities_to_create):
                new_entity_id = self.create_ftrack_ent_from_avalon_ent(
                    av_entity, parent_id
                )
                update_queue.put(new_entity_id)

            if new_entity_id:
                ftrack_ent_dict["entity"]["parent_id"] = new_entity_id

        if hierarchy_changing_ids:
            self.reload_parents(hierarchy_changing_ids)

        for ftrack_id in self.update_ftrack_ids:
            if ftrack_id == self.ft_project_id:
                continue

            avalon_id = self.ftrack_avalon_mapper[ftrack_id]
            avalon_entity = self.avalon_ents_by_id[avalon_id]

            avalon_attrs = self.entities_dict[ftrack_id]["avalon_attrs"]
            if (
                CUST_ATTR_ID_KEY not in avalon_attrs or
                avalon_attrs[CUST_ATTR_ID_KEY] != avalon_id
            ):
                configuration_id = self.entities_dict[ftrack_id][
                    "avalon_attrs_id"][CUST_ATTR_ID_KEY]

                _entity_key = collections.OrderedDict({
                    "configuration_id": configuration_id,
                    "entity_id": ftrack_id
                })

                self.session.recorded_operations.push(
                    ftrack_api.operation.UpdateEntityOperation(
                        "ContextCustomAttributeValue",
                        _entity_key,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        avalon_id
                    )
                )
            # check rest of data
            data_changes = self.compare_dict(
                self.entities_dict[ftrack_id]["final_entity"],
                avalon_entity,
                ignore_keys[ftrack_id]
            )
            if data_changes:
                self.updates[avalon_id] = self.merge_dicts(
                    data_changes,
                    self.updates[avalon_id]
                )

    def synchronize(self):
        self.log.debug("* Synchronization begins")
        avalon_project_id = self.ftrack_avalon_mapper.get(self.ft_project_id)
        if avalon_project_id:
            self.avalon_project_id = ObjectId(avalon_project_id)

        # remove filtered ftrack ids from create/update list
        for ftrack_id in self.all_filtered_entities:
            if ftrack_id in self.create_ftrack_ids:
                self.create_ftrack_ids.remove(ftrack_id)
            elif ftrack_id in self.update_ftrack_ids:
                self.update_ftrack_ids.remove(ftrack_id)

        self.log.debug("* Processing entities for archivation")
        self.delete_entities()

        self.log.debug("* Processing new entities")
        # Create not created entities
        for ftrack_id in self.create_ftrack_ids:
            # CHECK it is possible that entity was already created
            # because is parent of another entity which was processed first
            if ftrack_id in self.ftrack_avalon_mapper:
                continue
            self.create_avalon_entity(ftrack_id)

        if len(self.create_list) > 0:
            self.dbcon.insert_many(self.create_list)

        self.session.commit()

        self.log.debug("* Processing entities for update")
        self.prepare_changes()
        self.update_entities()
        self.session.commit()

    def create_avalon_entity(self, ftrack_id):
        if ftrack_id == self.ft_project_id:
            self.create_avalon_project()
            return

        entity_dict = self.entities_dict[ftrack_id]
        parent_ftrack_id = entity_dict["parent_id"]
        avalon_parent = None
        if parent_ftrack_id != self.ft_project_id:
            avalon_parent = self.ftrack_avalon_mapper.get(parent_ftrack_id)
            # if not avalon_parent:
            #     self.create_avalon_entity(parent_ftrack_id)
            #     avalon_parent = self.ftrack_avalon_mapper[parent_ftrack_id]
            avalon_parent = ObjectId(avalon_parent)

        # avalon_archived_by_id avalon_archived_by_name
        current_id = (
            entity_dict["avalon_attrs"].get(CUST_ATTR_ID_KEY) or ""
        ).strip()
        mongo_id = current_id
        name = entity_dict["name"]

        # Check if exist archived asset in mongo - by ID
        unarchive = False
        unarchive_id = self.check_unarchivation(ftrack_id, mongo_id, name)
        if unarchive_id is not None:
            unarchive = True
            mongo_id = unarchive_id

        item = entity_dict["final_entity"]
        try:
            new_id = ObjectId(mongo_id)
            if mongo_id in self.avalon_ftrack_mapper:
                new_id = ObjectId()
        except InvalidId:
            new_id = ObjectId()

        item["_id"] = new_id
        item["parent"] = self.avalon_project_id
        item["schema"] = EntitySchemas["asset"]
        item["data"]["visualParent"] = avalon_parent

        new_id_str = str(new_id)
        self.ftrack_avalon_mapper[ftrack_id] = new_id_str
        self.avalon_ftrack_mapper[new_id_str] = ftrack_id

        self._avalon_ents_by_id[new_id_str] = item
        self._avalon_ents_by_ftrack_id[ftrack_id] = new_id_str
        self._avalon_ents_by_name[item["name"]] = new_id_str

        if current_id != new_id_str:
            # store mongo id to ftrack entity
            configuration_id = self.hier_cust_attr_ids_by_key.get(
                CUST_ATTR_ID_KEY
            )
            if not configuration_id:
                # NOTE this is for cases when CUST_ATTR_ID_KEY key is not
                # hierarchical custom attribute but per entity type
                configuration_id = self.entities_dict[ftrack_id][
                    "avalon_attrs_id"
                ][CUST_ATTR_ID_KEY]

            _entity_key = collections.OrderedDict({
                "configuration_id": configuration_id,
                "entity_id": ftrack_id
            })

            self.session.recorded_operations.push(
                ftrack_api.operation.UpdateEntityOperation(
                    "ContextCustomAttributeValue",
                    _entity_key,
                    "value",
                    ftrack_api.symbol.NOT_SET,
                    new_id_str
                )
            )

        if unarchive is False:
            self.create_list.append(item)
            return
        # If unarchive then replace entity data in database
        self.dbcon.replace_one({"_id": new_id}, item)
        self.remove_from_archived(mongo_id)
        av_ent_path_items = item["data"]["parents"]
        av_ent_path_items.append(item["name"])
        av_ent_path = "/".join(av_ent_path_items)
        self.log.debug("Entity was unarchived <{}>".format(av_ent_path))

    def check_unarchivation(self, ftrack_id, mongo_id, name):
        archived_by_id = self.avalon_archived_by_id.get(mongo_id)
        archived_by_name = self.avalon_archived_by_name.get(name)

        # if not found in archived then skip
        if not archived_by_id and not archived_by_name:
            return None

        entity_dict = self.entities_dict[ftrack_id]

        if archived_by_id:
            # if is changeable then unarchive (nothing to check here)
            if self.changeability_by_mongo_id[mongo_id]:
                return mongo_id

            # TODO replace `__NOTSET__` with custom None constant
            archived_parent_id = archived_by_id["data"].get(
                "visualParent", "__NOTSET__"
            )
            archived_parents = archived_by_id["data"].get("parents")
            archived_name = archived_by_id["name"]

            if (
                archived_name != entity_dict["name"] or
                archived_parents != entity_dict["final_entity"]["data"][
                    "parents"
                ]
            ):
                return None

            return mongo_id

        # First check if there is any that have same parents
        for archived in archived_by_name:
            mongo_id = str(archived["_id"])
            archived_parents = archived.get("data", {}).get("parents")
            if (
                archived_parents == entity_dict["final_entity"]["data"][
                    "parents"
                ]
            ):
                return mongo_id

        # Secondly try to find more close to current ftrack entity
        first_changeable = None
        for archived in archived_by_name:
            mongo_id = str(archived["_id"])
            if not self.changeability_by_mongo_id[mongo_id]:
                continue

            if first_changeable is None:
                first_changeable = mongo_id

            ftrack_parent_id = entity_dict["parent_id"]
            map_ftrack_parent_id = self.ftrack_avalon_mapper.get(
                ftrack_parent_id
            )

            # TODO replace `__NOTSET__` with custom None constant
            archived_parent_id = archived.get("data", {}).get(
                "visualParent", "__NOTSET__"
            )
            if archived_parent_id is not None:
                archived_parent_id = str(archived_parent_id)

            # skip if parent is archived - How this should be possible?
            parent_entity = self.avalon_ents_by_id.get(archived_parent_id)
            if (
                parent_entity and (
                    map_ftrack_parent_id is not None and
                    map_ftrack_parent_id == str(parent_entity["_id"])
                )
            ):
                return mongo_id
        # Last return first changeable with same name (or None)
        return first_changeable

    def create_avalon_project(self):
        project_item = self.entities_dict[self.ft_project_id]["final_entity"]
        mongo_id = (
            self.entities_dict[self.ft_project_id]["avalon_attrs"].get(
                CUST_ATTR_ID_KEY
            ) or ""
        ).strip()

        try:
            new_id = ObjectId(mongo_id)
        except InvalidId:
            new_id = ObjectId()

        project_item["_id"] = new_id
        project_item["parent"] = None
        project_item["schema"] = EntitySchemas["project"]
        project_item["config"]["schema"] = EntitySchemas["config"]

        self.ftrack_avalon_mapper[self.ft_project_id] = new_id
        self.avalon_ftrack_mapper[new_id] = self.ft_project_id

        self.avalon_project_id = new_id

        self._avalon_ents_by_id[str(new_id)] = project_item
        if self._avalon_ents_by_ftrack_id is None:
            self._avalon_ents_by_ftrack_id = {}
        self._avalon_ents_by_ftrack_id[self.ft_project_id] = str(new_id)
        if self._avalon_ents_by_name is None:
            self._avalon_ents_by_name = {}
        self._avalon_ents_by_name[project_item["name"]] = str(new_id)

        self.create_list.append(project_item)

        # store mongo id to ftrack entity
        entity = self.entities_dict[self.ft_project_id]["entity"]
        entity["custom_attributes"][CUST_ATTR_ID_KEY] = str(new_id)

    def _bubble_changeability(self, unchangeable_ids):
        unchangeable_queue = queue.Queue()
        for entity_id in unchangeable_ids:
            unchangeable_queue.put((entity_id, False))

        processed_parents_ids = []
        subsets_to_remove = []
        while not unchangeable_queue.empty():
            entity_id, child_is_archived = unchangeable_queue.get()
            # skip if already processed
            if entity_id in processed_parents_ids:
                continue

            entity = self.avalon_ents_by_id.get(entity_id)
            # if entity is not archived but unchageable child was then skip
            # - archived entities should not affect not archived?
            if entity and child_is_archived:
                continue

            # set changeability of current entity to False
            self._changeability_by_mongo_id[entity_id] = False
            processed_parents_ids.append(entity_id)
            # if not entity then is probably archived
            if not entity:
                entity = self.avalon_archived_by_id.get(entity_id)
                child_is_archived = True

            if not entity:
                # if entity is not found then it is subset without parent
                if entity_id in unchangeable_ids:
                    subsets_to_remove.append(entity_id)
                else:
                    # TODO logging - What is happening here?
                    self.log.warning((
                        "Avalon contains entities without valid parents that"
                        " lead to Project (should not cause errors)"
                        " - MongoId <{}>"
                    ).format(str(entity_id)))
                continue

            # skip if parent is project
            parent_id = entity["data"]["visualParent"]
            if parent_id is None:
                continue
            unchangeable_queue.put((str(parent_id), child_is_archived))

        self._delete_subsets_without_asset(subsets_to_remove)

    def _delete_subsets_without_asset(self, not_existing_parents):
        subset_ids = []
        version_ids = []
        repre_ids = []
        to_delete = []

        for parent_id in not_existing_parents:
            subsets = self.subsets_by_parent_id.get(parent_id)
            if not subsets:
                continue
            for subset in subsets:
                if subset.get("type") != "subset":
                    continue
                subset_ids.append(subset["_id"])

        db_subsets = self.dbcon.find({
            "_id": {"$in": subset_ids},
            "type": "subset"
        })
        if not db_subsets:
            return

        db_versions = self.dbcon.find({
            "parent": {"$in": subset_ids},
            "type": "version"
        })
        if db_versions:
            version_ids = [ver["_id"] for ver in db_versions]

        db_repres = self.dbcon.find({
            "parent": {"$in": version_ids},
            "type": "representation"
        })
        if db_repres:
            repre_ids = [repre["_id"] for repre in db_repres]

        to_delete.extend(subset_ids)
        to_delete.extend(version_ids)
        to_delete.extend(repre_ids)

        self.dbcon.delete_many({"_id": {"$in": to_delete}})

    # Probably deprecated
    def _check_changeability(self, parent_id=None):
        for entity in self.avalon_ents_by_parent_id[parent_id]:
            mongo_id = str(entity["_id"])
            is_changeable = self._changeability_by_mongo_id.get(mongo_id)
            if is_changeable is not None:
                continue

            self._check_changeability(mongo_id)
            is_changeable = True
            for child in self.avalon_ents_by_parent_id[parent_id]:
                if not self._changeability_by_mongo_id[str(child["_id"])]:
                    is_changeable = False
                    break

            if is_changeable is True:
                is_changeable = (mongo_id in self.subsets_by_parent_id)
            self._changeability_by_mongo_id[mongo_id] = is_changeable

    def update_entities(self):
        mongo_changes_bulk = []
        for mongo_id, changes in self.updates.items():
            filter = {"_id": ObjectId(mongo_id)}
            change_data = from_dict_to_set(changes)
            mongo_changes_bulk.append(UpdateOne(filter, change_data))

        if not mongo_changes_bulk:
            # TODO LOG
            return
        self.dbcon.bulk_write(mongo_changes_bulk)

    def reload_parents(self, hierarchy_changing_ids):
        parents_queue = queue.Queue()
        parents_queue.put((self.ft_project_id, [], False))
        while not parents_queue.empty():
            ftrack_id, parent_parents, changed = parents_queue.get()
            _parents = copy.deepcopy(parent_parents)
            if ftrack_id not in hierarchy_changing_ids and not changed:
                if ftrack_id != self.ft_project_id:
                    _parents.append(self.entities_dict[ftrack_id]["name"])
                for child_id in self.entities_dict[ftrack_id]["children"]:
                    parents_queue.put((child_id, _parents, changed))
                continue

            changed = True
            parents = [par for par in _parents]
            hierarchy = "/".join(parents)
            self.entities_dict[ftrack_id][
                "final_entity"]["data"]["parents"] = parents
            self.entities_dict[ftrack_id][
                "final_entity"]["data"]["hierarchy"] = hierarchy

            _parents.append(self.entities_dict[ftrack_id]["name"])
            for child_id in self.entities_dict[ftrack_id]["children"]:
                parents_queue.put((child_id, _parents, changed))

            if ftrack_id in self.create_ftrack_ids:
                mongo_id = self.ftrack_avalon_mapper[ftrack_id]
                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}
                self.updates[mongo_id]["data"]["parents"] = parents
                self.updates[mongo_id]["data"]["hierarchy"] = hierarchy

    def prepare_project_changes(self):
        ftrack_ent_dict = self.entities_dict[self.ft_project_id]
        ftrack_entity = ftrack_ent_dict["entity"]
        avalon_code = self.avalon_project["data"]["code"]
        # TODO Is possible to sync if full name was changed?
        # if ftrack_ent_dict["name"] != self.avalon_project["name"]:
        #     ftrack_entity["full_name"] = avalon_name
        #     self.entities_dict[self.ft_project_id]["name"] = avalon_name
        #     self.entities_dict[self.ft_project_id]["final_entity"][
        #         "name"
        #     ] = avalon_name

        # TODO logging
        # TODO report
        # TODO May this happen? Is possible to change project code?
        if ftrack_entity["name"] != avalon_code:
            ftrack_entity["name"] = avalon_code
            self.entities_dict[self.ft_project_id]["final_entity"]["data"][
                "code"
            ] = avalon_code
            self.session.commit()
            sub_msg = (
                "Project code was changed back to \"{}\"".format(avalon_code)
            )
            msg = (
                "It is not possible to change"
                " project code after synchronization"
            )
            self.report_items["warning"][msg] = sub_msg
            self.log.warning(sub_msg)

        return self.compare_dict(
            self.entities_dict[self.ft_project_id]["final_entity"],
            self.avalon_project
        )

    def compare_dict(self, dict_new, dict_old, _ignore_keys=[]):
        # _ignore_keys may be used for keys nested dict like"data.visualParent"
        changes = {}
        ignore_keys = []
        for key_val in _ignore_keys:
            key_items = key_val.split(".")
            if len(key_items) == 1:
                ignore_keys.append(key_items[0])

        for key, value in dict_new.items():
            if key in ignore_keys:
                continue

            if key not in dict_old:
                changes[key] = value
                continue

            if isinstance(value, dict):
                if not isinstance(dict_old[key], dict):
                    changes[key] = value
                    continue

                _new_ignore_keys = []
                for key_val in _ignore_keys:
                    key_items = key_val.split(".")
                    if len(key_items) <= 1:
                        continue
                    _new_ignore_keys.append(".".join(key_items[1:]))

                _changes = self.compare_dict(
                    value, dict_old[key], _new_ignore_keys
                )
                if _changes:
                    changes[key] = _changes
                continue

            if value != dict_old[key]:
                changes[key] = value

        return changes

    def merge_dicts(self, dict_new, dict_old):
        for key, value in dict_new.items():
            if key not in dict_old:
                dict_old[key] = value
                continue

            if isinstance(value, dict):
                dict_old[key] = self.merge_dicts(value, dict_old[key])
                continue

            dict_old[key] = value

        return dict_old

    def delete_entities(self):
        if not self.deleted_entities:
            return
        # Try to order so child is not processed before parent
        deleted_entities = []
        _deleted_entities = [id for id in self.deleted_entities]

        while True:
            if not _deleted_entities:
                break
            _ready = []
            for mongo_id in _deleted_entities:
                ent = self.avalon_ents_by_id[mongo_id]
                vis_par = ent["data"]["visualParent"]
                if (
                    vis_par is not None and
                    str(vis_par) in _deleted_entities
                ):
                    continue
                _ready.append(mongo_id)

            for id in _ready:
                deleted_entities.append(id)
                _deleted_entities.remove(id)

        delete_ids = []
        for mongo_id in deleted_entities:
            # delete if they are deletable
            if self.changeability_by_mongo_id[mongo_id]:
                delete_ids.append(ObjectId(mongo_id))
                continue

            # check if any new created entity match same entity
            # - name and parents must match
            deleted_entity = self.avalon_ents_by_id[mongo_id]
            name = deleted_entity["name"]
            parents = deleted_entity["data"]["parents"]
            similar_ent_id = None
            for ftrack_id in self.create_ftrack_ids:
                _ent_final = self.entities_dict[ftrack_id]["final_entity"]
                if _ent_final["name"] != name:
                    continue
                if _ent_final["data"]["parents"] != parents:
                    continue

                # If in create is "same" then we can "archive" current
                # since will be unarchived in create method
                similar_ent_id = ftrack_id
                break

            # If similar entity(same name and parents) is in create
            # entities list then just change from create to update
            if similar_ent_id is not None:
                self.create_ftrack_ids.remove(similar_ent_id)
                self.update_ftrack_ids.append(similar_ent_id)
                self.avalon_ftrack_mapper[mongo_id] = similar_ent_id
                self.ftrack_avalon_mapper[similar_ent_id] = mongo_id
                continue

            found_by_name_id = None
            for ftrack_id, ent_dict in self.entities_dict.items():
                if not ent_dict.get("name"):
                    continue

                if name == ent_dict["name"]:
                    found_by_name_id = ftrack_id
                    break

            if found_by_name_id is not None:
                # * THESE conditins are too complex to implement in first stage
                # - probably not possible to solve if this happen
                # if found_by_name_id in self.create_ftrack_ids:
                #     # reparent entity of the new one create?
                #     pass
                #
                # elif found_by_name_id in self.update_ftrack_ids:
                #     found_mongo_id = self.ftrack_avalon_mapper[found_by_name_id]
                #
                # ent_dict = self.entities_dict[found_by_name_id]

                # TODO report - CRITICAL entity with same name alread exists in
                # different hierarchy - can't recreate entity
                continue

            _vis_parent = deleted_entity["data"]["visualParent"]
            if _vis_parent is None:
                _vis_parent = self.avalon_project_id
            _vis_parent = str(_vis_parent)
            ftrack_parent_id = self.avalon_ftrack_mapper[_vis_parent]
            self.create_ftrack_ent_from_avalon_ent(
                deleted_entity, ftrack_parent_id
            )

        filter = {"_id": {"$in": delete_ids}, "type": "asset"}
        self.dbcon.update_many(filter, {"$set": {"type": "archived_asset"}})

    def create_ftrack_ent_from_avalon_ent(self, av_entity, parent_id):
        new_entity = None
        parent_entity = self.entities_dict[parent_id]["entity"]

        _name = av_entity["name"]
        _type = av_entity["data"].get("entityType", "folder")

        self.log.debug((
            "Re-ceating deleted entity {} <{}>"
        ).format(_name, _type))

        new_entity = self.session.create(_type, {
            "name": _name,
            "parent": parent_entity
        })
        self.session.commit()

        final_entity = {}
        for k, v in av_entity.items():
            final_entity[k] = v

        if final_entity.get("type") != "asset":
            final_entity["type"] = "asset"

        new_entity_id = new_entity["id"]
        new_entity_data = {
            "entity": new_entity,
            "parent_id": parent_id,
            "entity_type": _type.lower(),
            "entity_type_orig": _type,
            "name": _name,
            "final_entity": final_entity
        }
        for k, v in new_entity_data.items():
            self.entities_dict[new_entity_id][k] = v

        p_chilren = self.entities_dict[parent_id]["children"]
        if new_entity_id not in p_chilren:
            self.entities_dict[parent_id]["children"].append(new_entity_id)

        cust_attr, hier_attrs = get_pype_attr(self.session)
        for _attr in cust_attr:
            key = _attr["key"]
            if key not in av_entity["data"]:
                continue

            if key not in new_entity["custom_attributes"]:
                continue

            value = av_entity["data"][key]
            if not value:
                continue

            new_entity["custom_attributes"][key] = value

        av_entity_id = str(av_entity["_id"])
        new_entity["custom_attributes"][CUST_ATTR_ID_KEY] = av_entity_id

        self.ftrack_avalon_mapper[new_entity_id] = av_entity_id
        self.avalon_ftrack_mapper[av_entity_id] = new_entity_id

        self.session.commit()

        ent_path = self.get_ent_path(new_entity_id)
        msg = (
            "Deleted entity was recreated because it or its children"
            " contain published data"
        )

        self.report_items["info"][msg].append(ent_path)

        return new_entity_id

    def regex_duplicate_interface(self):
        items = []
        if self.failed_regex or self.tasks_failed_regex:
            subtitle = "Entity names contain prohibited symbols:"
            items.append({
                "type": "label",
                "value": "# {}".format(subtitle)
            })
            items.append({
                "type": "label",
                "value": (
                    "<p><i>NOTE: You can use Letters( a-Z ),"
                    " Numbers( 0-9 ) and Underscore( _ )</i></p>"
                )
            })
            log_msgs = []
            for name, ids in self.failed_regex.items():
                error_title = {
                    "type": "label",
                    "value": "## {}".format(name)
                }
                items.append(error_title)
                paths = []
                for entity_id in ids:
                    ent_path = self.get_ent_path(entity_id)
                    paths.append(ent_path)

                error_message = {
                    "type": "label",
                    "value": '<p>{}</p>'.format("<br>".join(paths))
                }
                items.append(error_message)
                log_msgs.append("<{}> ({})".format(name, ",".join(paths)))

            for name, ids in self.tasks_failed_regex.items():
                error_title = {
                    "type": "label",
                    "value": "## Task: {}".format(name)
                }
                items.append(error_title)
                paths = []
                for entity_id in ids:
                    ent_path = self.get_ent_path(entity_id)
                    ent_path = "/".join([ent_path, name])
                    paths.append(ent_path)

                error_message = {
                    "type": "label",
                    "value": '<p>{}</p>'.format("<br>".join(paths))
                }
                items.append(error_message)
                log_msgs.append("<{}> ({})".format(name, ",".join(paths)))

            self.log.warning("{}{}".format(subtitle, ", ".join(log_msgs)))

        if self.duplicates:
            subtitle = "Duplicated entity names:"
            items.append({
                "type": "label",
                "value": "# {}".format(subtitle)
            })
            items.append({
                "type": "label",
                "value": (
                    "<p><i>NOTE: It is not allowed to use the same name"
                    " for multiple entities in the same project</i></p>"
                )
            })
            log_msgs = []
            for name, ids in self.duplicates.items():
                error_title = {
                    "type": "label",
                    "value": "## {}".format(name)
                }
                items.append(error_title)
                paths = []
                for entity_id in ids:
                    ent_path = self.get_ent_path(entity_id)
                    paths.append(ent_path)

                error_message = {
                    "type": "label",
                    "value": '<p>{}</p>'.format("<br>".join(paths))
                }
                items.append(error_message)
                log_msgs.append("<{}> ({})".format(name, ", ".join(paths)))

            self.log.warning("{}{}".format(subtitle, ", ".join(log_msgs)))

        return items

    def report(self):
        items = []
        project_name = self.entities_dict[self.ft_project_id]["name"]
        title = "Synchronization report ({}):".format(project_name)

        keys = ["error", "warning", "info"]
        for key in keys:
            subitems = []
            if key == "warning":
                for _item in self.regex_duplicate_interface():
                    subitems.append(_item)

            for msg, _items in self.report_items[key].items():
                if not _items:
                    continue

                subitems.append({
                    "type": "label",
                    "value": "# {}".format(msg)
                })
                if isinstance(_items, str):
                    _items = [_items]
                subitems.append({
                    "type": "label",
                    "value": '<p>{}</p>'.format("<br>".join(_items))
                })

            if items and subitems:
                items.append(self.report_splitter)

            items.extend(subitems)

        return {
            "items": items,
            "title": title,
            "success": False,
            "message": "Synchronization Finished"
        }
