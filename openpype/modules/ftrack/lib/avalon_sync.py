import re
import json
import collections
import copy
import numbers

import six

from openpype.api import (
    Logger,
    get_anatomy_settings
)
from openpype.lib import ApplicationManager
from openpype.pipeline import AvalonMongoDB, schema

from .constants import CUST_ATTR_ID_KEY, FPS_KEYS
from .custom_attributes import get_openpype_attr, query_custom_attributes

from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo import UpdateOne, ReplaceOne
import ftrack_api

log = Logger.get_logger(__name__)


# Current schemas for avalon types
CURRENT_DOC_SCHEMAS = {
    "project": "openpype:project-3.0",
    "asset": "openpype:asset-3.0",
    "config": "openpype:config-2.0"
}


class InvalidFpsValue(Exception):
    pass


def is_string_number(value):
    """Can string value be converted to number (float)."""
    if not isinstance(value, six.string_types):
        raise TypeError("Expected {} got {}".format(
            ", ".join(str(t) for t in six.string_types), str(type(value))
        ))
    if value == ".":
        return False

    if value.startswith("."):
        value = "0" + value
    elif value.endswith("."):
        value = value + "0"

    if re.match(r"^\d+(\.\d+)?$", value) is None:
        return False
    return True


def convert_to_fps(source_value):
    """Convert value into fps value.

    Non string values are kept untouched. String is tried to convert.
    Valid values:
    "1000"
    "1000.05"
    "1000,05"
    ",05"
    ".05"
    "1000,"
    "1000."
    "1000/1000"
    "1000.05/1000"
    "1000/1000.05"
    "1000.05/1000.05"
    "1000,05/1000"
    "1000/1000,05"
    "1000,05/1000,05"

    Invalid values:
    "/"
    "/1000"
    "1000/"
    ","
    "."
    ...any other string

    Returns:
        float: Converted value.

    Raises:
        InvalidFpsValue: When value can't be converted to float.
    """
    if not isinstance(source_value, six.string_types):
        if isinstance(source_value, numbers.Number):
            return float(source_value)
        return source_value

    value = source_value.strip().replace(",", ".")
    if not value:
        raise InvalidFpsValue("Got empty value")

    subs = value.split("/")
    if len(subs) == 1:
        str_value = subs[0]
        if not is_string_number(str_value):
            raise InvalidFpsValue(
                "Value \"{}\" can't be converted to number.".format(value)
            )
        return float(str_value)

    elif len(subs) == 2:
        divident, divisor = subs
        if not divident or not is_string_number(divident):
            raise InvalidFpsValue(
                "Divident value \"{}\" can't be converted to number".format(
                    divident
                )
            )

        if not divisor or not is_string_number(divisor):
            raise InvalidFpsValue(
                "Divisor value \"{}\" can't be converted to number".format(
                    divident
                )
            )
        divisor_float = float(divisor)
        if divisor_float == 0.0:
            raise InvalidFpsValue("Can't divide by zero")
        return float(divident) / divisor_float

    raise InvalidFpsValue(
        "Value can't be converted to number \"{}\"".format(source_value)
    )


def create_chunks(iterable, chunk_size=None):
    """Separate iterable into multiple chunks by size.

    Args:
        iterable(list|tuple|set): Object that will be separated into chunks.
        chunk_size(int): Size of one chunk. Default value is 200.

    Returns:
        list<list>: Chunked items.
    """
    chunks = []
    if not iterable:
        return chunks

    tupled_iterable = tuple(iterable)
    iterable_size = len(tupled_iterable)
    if chunk_size is None:
        chunk_size = 200

    for idx in range(0, iterable_size, chunk_size):
        chunks.append(tupled_iterable[idx:idx + chunk_size])
    return chunks


def check_regex(name, entity_type, in_schema=None, schema_patterns=None):
    schema_name = "asset-3.0"
    if in_schema:
        schema_name = in_schema
    elif entity_type == "project":
        schema_name = "project-2.1"
    elif entity_type == "task":
        schema_name = "task"

    name_pattern = None
    if schema_patterns is not None:
        name_pattern = schema_patterns.get(schema_name)

    if not name_pattern:
        default_pattern = "^[a-zA-Z0-9_.]*$"
        schema_obj = schema._cache.get(schema_name + ".json")
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


def join_query_keys(keys):
    return ",".join(["\"{}\"".format(key) for key in keys])


def get_python_type_for_custom_attribute(cust_attr, cust_attr_type_name=None):
    """Python type that should value of custom attribute have.

    This function is mainly for number type which is always float from ftrack.

    Returns:
        type: Python type which call be called on object to convert the object
            to the type or None if can't figure out.
    """
    if cust_attr_type_name is None:
        cust_attr_type_name = cust_attr["type"]["name"]

    if cust_attr_type_name == "text":
        return str

    if cust_attr_type_name == "boolean":
        return bool

    if cust_attr_type_name in ("number", "enumerator"):
        cust_attr_config = json.loads(cust_attr["config"])
        if cust_attr_type_name == "number":
            if cust_attr_config["isdecimal"]:
                return float
            return int

        if cust_attr_type_name == "enumerator":
            if cust_attr_config["multiSelect"]:
                return list
            return str
    # "date", "expression", "notificationtype", "dynamic enumerator"
    return None


def from_dict_to_set(data, is_project):
    """
        Converts 'data' into $set part of MongoDB update command.
        Sets new or modified keys.
        Tasks are updated completely, not per task. (Eg. change in any of the
        tasks results in full update of "tasks" from Ftrack.
    Args:
        data (dictionary): up-to-date data from Ftrack
        is_project (boolean): true for project

    Returns:
        (dictionary) - { "$set" : "{..}"}
    """
    not_set = object()
    task_changes = not_set
    if (
        is_project
        and "config" in data
        and "tasks" in data["config"]
    ):
        task_changes = data["config"].pop("tasks")
        task_changes_key = "config.tasks"
        if not data["config"]:
            data.pop("config")
    elif (
        not is_project
        and "data" in data
        and "tasks" in data["data"]
    ):
        task_changes = data["data"].pop("tasks")
        task_changes_key = "data.tasks"
        if not data["data"]:
            data.pop("data")

    result = {"$set": {}}
    dict_queue = collections.deque()
    dict_queue.append((None, data))

    while dict_queue:
        _key, _data = dict_queue.popleft()
        for key, value in _data.items():
            new_key = key
            if _key is not None:
                new_key = "{}.{}".format(_key, key)

            if not isinstance(value, dict) or \
                    (isinstance(value, dict) and not bool(value)):  # empty dic
                result["$set"][new_key] = value
                continue
            dict_queue.append((new_key, value))

    if task_changes is not not_set and task_changes_key:
        result["$set"][task_changes_key] = task_changes
    return result


def get_project_apps(in_app_list):
    """ Application definitions for app name.

    Args:
        in_app_list: (list) - names of applications

    Returns:
        tuple (list, dictionary) - list of dictionaries with apps definitions
            dictionary of warnings
    """
    apps = []
    warnings = collections.defaultdict(list)

    if not in_app_list:
        return apps, warnings

    missing_app_msg = "Missing definition of application"
    application_manager = ApplicationManager()
    for app_name in in_app_list:
        if application_manager.applications.get(app_name):
            apps.append({"name": app_name})
        else:
            warnings[missing_app_msg].append(app_name)
    return apps, warnings


def get_hierarchical_attributes_values(
    session, entity, hier_attrs, cust_attr_types=None
):
    if not cust_attr_types:
        cust_attr_types = session.query(
            "select id, name from CustomAttributeType"
        ).all()

    cust_attr_name_by_id = {
        cust_attr_type["id"]: cust_attr_type["name"]
        for cust_attr_type in cust_attr_types
    }
    # Hierarchical cust attrs
    attr_key_by_id = {}
    convert_types_by_attr_id = {}
    defaults = {}
    for attr in hier_attrs:
        attr_id = attr["id"]
        key = attr["key"]
        type_id = attr["type_id"]

        attr_key_by_id[attr_id] = key
        defaults[key] = attr["default"]

        cust_attr_type_name = cust_attr_name_by_id[type_id]
        convert_type = get_python_type_for_custom_attribute(
            attr, cust_attr_type_name
        )
        convert_types_by_attr_id[attr_id] = convert_type

    entity_ids = [item["id"] for item in entity["link"]]

    values = query_custom_attributes(
        session, list(attr_key_by_id.keys()), entity_ids, True
    )

    hier_values = {}
    for key, val in defaults.items():
        hier_values[key] = val

    if not values:
        return hier_values

    values_by_entity_id = collections.defaultdict(dict)
    for item in values:
        value = item["value"]
        if value is None:
            continue

        attr_id = item["configuration_id"]

        convert_type = convert_types_by_attr_id[attr_id]
        if convert_type:
            value = convert_type(value)

        key = attr_key_by_id[attr_id]
        entity_id = item["entity_id"]
        values_by_entity_id[entity_id][key] = value

    for entity_id in entity_ids:
        for key in attr_key_by_id.values():
            value = values_by_entity_id[entity_id].get(key)
            if value is not None:
                hier_values[key] = value

    return hier_values


class SyncEntitiesFactory:
    dbcon = AvalonMongoDB()

    cust_attr_query_keys = [
        "id",
        "key",
        "entity_type",
        "object_type_id",
        "is_hierarchical",
        "config",
        "default"
    ]

    project_query = (
        "select full_name, name, custom_attributes"
        ", project_schema._task_type_schema.types.name"
        " from Project where full_name is \"{}\""
    )
    entities_query = (
        "select id, name, type_id, parent_id, link, description"
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
            auto_connect_event_hub=False
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
        self.unarchive_list = []
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

        self._object_types_by_name = None

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
                "value": (
                    "# Can't access Custom attribute: <b>\"{}\"</b>"
                ).format(CUST_ATTR_ID_KEY)
            })
            items.append({
                "type": "label",
                "value": (
                    "<p>- Check if your User and API key has permissions"
                    " to access the Custom attribute."
                    "<br>Username:\"{}\""
                    "<br>API key:\"{}\"</p>"
                ).format(self._api_user, self._api_key)
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
            "tasks": {}
        })

        # Find all entities in project
        all_project_entities = self.session.query(
            self.entities_query.format(ft_project_id)
        ).all()
        task_types = self.session.query("select id, name from Type").all()
        task_type_names_by_id = {
            task_type["id"]: task_type["name"]
            for task_type in task_types
        }
        for entity in all_project_entities:
            parent_id = entity["parent_id"]
            entity_type = entity.entity_type
            entity_type_low = entity_type.lower()
            if entity_type_low in self.ignore_entity_types:
                continue

            elif entity_type_low == "task":
                # enrich task info with additional metadata
                task_type_name = task_type_names_by_id[entity["type_id"]]
                task = {"type": task_type_name}
                entities_dict[parent_id]["tasks"][entity["name"]] = task
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
        """
            Returns dictionary of avalon tracked entities (assets stored in
            MongoDB) accessible by its '_id'
            (mongo intenal ID - example ObjectId("5f48de5830a9467b34b69798"))
        Returns:
            (dictionary) - {"(_id)": whole entity asset}
        """
        if self._avalon_ents_by_id is None:
            self._avalon_ents_by_id = {}
            for entity in self.avalon_entities:
                self._avalon_ents_by_id[str(entity["_id"])] = entity

        return self._avalon_ents_by_id

    @property
    def avalon_ents_by_ftrack_id(self):
        """
            Returns dictionary of Mongo ids of avalon tracked entities
            (assets stored in MongoDB) accessible by its 'ftrackId'
            (id from ftrack)
            (example '431ee3f2-e91a-11ea-bfa4-92591a5b5e3e')
            Returns:
                (dictionary) - {"(ftrackId)": "_id"}
        """
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
        """
            Returns dictionary of Mongo ids of avalon tracked entities
            (assets stored in MongoDB) accessible by its 'name'
            (example 'Hero')
            Returns:
                (dictionary) - {"(name)": "_id"}
        """
        if self._avalon_ents_by_name is None:
            self._avalon_ents_by_name = {}
            for entity in self.avalon_entities:
                self._avalon_ents_by_name[entity["name"]] = str(entity["_id"])

        return self._avalon_ents_by_name

    @property
    def avalon_ents_by_parent_id(self):
        """
            Returns dictionary of avalon tracked entities
            (assets stored in MongoDB) accessible by its 'visualParent'
            (example ObjectId("5f48de5830a9467b34b69798"))

            Fills 'self._avalon_archived_ents' for performance
            Returns:
                (dictionary) - {"(_id)": whole entity}
        """
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
        """
            Returns list of archived assets from DB
            (their "type" == 'archived_asset')

            Fills 'self._avalon_archived_ents' for performance
        Returns:
            (list) of assets
        """
        if self._avalon_archived_ents is None:
            self._avalon_archived_ents = [
                ent for ent in self.dbcon.find({"type": "archived_asset"})
            ]
        return self._avalon_archived_ents

    @property
    def avalon_archived_by_name(self):
        """
            Returns list of archived assets from DB
            (their "type" == 'archived_asset')

            Fills 'self._avalon_archived_by_name' for performance
        Returns:
            (dictionary of lists) of assets accessible by asset name
        """
        if self._avalon_archived_by_name is None:
            self._avalon_archived_by_name = collections.defaultdict(list)
            for ent in self.avalon_archived_ents:
                self._avalon_archived_by_name[ent["name"]].append(ent)
        return self._avalon_archived_by_name

    @property
    def avalon_archived_by_id(self):
        """
            Returns dictionary of archived assets from DB
            (their "type" == 'archived_asset')

            Fills 'self._avalon_archived_by_id' for performance
        Returns:
            (dictionary) of assets accessible by asset mongo _id
        """
        if self._avalon_archived_by_id is None:
            self._avalon_archived_by_id = {
                str(ent["_id"]): ent for ent in self.avalon_archived_ents
            }
        return self._avalon_archived_by_id

    @property
    def avalon_archived_by_parent_id(self):
        """
            Returns dictionary of archived assets from DB per their's parent
            (their "type" == 'archived_asset')

            Fills 'self._avalon_archived_by_parent_id' for performance
        Returns:
            (dictionary of lists) of assets accessible by asset parent
                                     mongo _id
        """
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
        """
            Returns dictionary of subsets from Mongo ("type": "subset")
            grouped by their parent.

            Fills 'self._subsets_by_parent_id' for performance
        Returns:
            (dictionary of lists)
        """
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
    def object_types_by_name(self):
        if self._object_types_by_name is None:
            object_types_by_name = self.session.query(
                "select id, name from ObjectType"
            ).all()
            self._object_types_by_name = {
                object_type["name"]: object_type
                for object_type in object_types_by_name
            }
        return self._object_types_by_name

    @property
    def all_ftrack_names(self):
        """
            Returns lists of names of all entities in Ftrack
        Returns:
            (list)
        """
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
            for task in entity_dict["tasks"].items():
                task_name, task = task
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
        filter_queue = collections.deque()
        failed_regex_msg = "{} - Entity has invalid symbols in the name"
        duplicate_msg = "There are multiple entities with the name: \"{}\":"

        for ids in self.failed_regex.values():
            for id in ids:
                ent_path = self.get_ent_path(id)
                self.log.warning(failed_regex_msg.format(ent_path))
                filter_queue.append(id)

        for name, ids in self.duplicates.items():
            self.log.warning(duplicate_msg.format(name))
            for id in ids:
                ent_path = self.get_ent_path(id)
                self.log.warning(ent_path)
                filter_queue.append(id)

        filtered_ids = []
        while filter_queue:
            ftrack_id = filter_queue.popleft()
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
                filter_queue.append(child_id)

        for name, ids in self.tasks_failed_regex.items():
            for id in ids:
                if id not in self.entities_dict:
                    continue
                self.entities_dict[id]["tasks"].pop(name)
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

        filter_queue = collections.deque()
        filter_queue.append((self.ft_project_id, False))
        while filter_queue:
            parent_id, remove = filter_queue.popleft()
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
                filter_queue.append((child_id, _remove))

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
        parents_queue = collections.deque()
        children_queue = collections.deque()
        for selected_id in selected_ids:
            # skip if already filtered with ignore sync custom attribute
            if selected_id in self.filtered_ids:
                continue

            parents_queue.append(selected_id)
            children_queue.append(selected_id)

        while parents_queue:
            ftrack_id = parents_queue.popleft()
            while True:
                # Stops when parent is in sync_ids
                if (
                    ftrack_id in self.filtered_ids
                    or ftrack_id in sync_ids
                    or ftrack_id is None
                ):
                    break
                sync_ids.append(ftrack_id)
                ftrack_id = self.entities_dict[ftrack_id]["parent_id"]

        while children_queue:
            parent_id = children_queue.popleft()
            for child_id in self.entities_dict[parent_id]["children"]:
                if child_id in sync_ids or child_id in self.filtered_ids:
                    continue
                sync_ids.append(child_id)
                children_queue.append(child_id)

        # separate not selected and to process entities
        for key, value in self.entities_dict.items():
            if key not in sync_ids:
                self.not_selected_ids.append(key)

        for ftrack_id in self.not_selected_ids:
            # pop from entities
            value = self.entities_dict.pop(ftrack_id)
            # remove entity from parent's children
            parent_id = value["parent_id"]
            if parent_id not in sync_ids:
                continue

            self.entities_dict[parent_id]["children"].remove(ftrack_id)

    def set_cutom_attributes(self):
        self.log.debug("* Preparing custom attributes")
        # Get custom attributes and values
        custom_attrs, hier_attrs = get_openpype_attr(
            self.session, query_keys=self.cust_attr_query_keys
        )
        ent_types_by_name = self.object_types_by_name
        # Custom attribute types
        cust_attr_types = self.session.query(
            "select id, name from CustomAttributeType"
        ).all()
        cust_attr_type_name_by_id = {
            cust_attr_type["id"]: cust_attr_type["name"]
            for cust_attr_type in cust_attr_types
        }

        # store default values per entity type
        attrs_per_entity_type = collections.defaultdict(dict)
        avalon_attrs = collections.defaultdict(dict)
        # store also custom attribute configuration id for future use (create)
        attrs_per_entity_type_ca_id = collections.defaultdict(dict)
        avalon_attrs_ca_id = collections.defaultdict(dict)

        attribute_key_by_id = {}
        convert_types_by_attr_id = {}
        for cust_attr in custom_attrs:
            key = cust_attr["key"]
            attr_id = cust_attr["id"]
            type_id = cust_attr["type_id"]

            attribute_key_by_id[attr_id] = key
            cust_attr_type_name = cust_attr_type_name_by_id[type_id]

            convert_type = get_python_type_for_custom_attribute(
                cust_attr, cust_attr_type_name
            )
            convert_types_by_attr_id[attr_id] = convert_type

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

        items = query_custom_attributes(
            self.session,
            list(attribute_key_by_id.keys()),
            sync_ids
        )

        invalid_fps_items = []
        for item in items:
            entity_id = item["entity_id"]
            attr_id = item["configuration_id"]
            key = attribute_key_by_id[attr_id]
            store_key = "custom_attributes"
            if key.startswith("avalon_"):
                store_key = "avalon_attrs"

            convert_type = convert_types_by_attr_id[attr_id]
            value = item["value"]
            if convert_type:
                value = convert_type(value)

            if key in FPS_KEYS:
                try:
                    value = convert_to_fps(value)
                except InvalidFpsValue:
                    invalid_fps_items.append((entity_id, value))
            self.entities_dict[entity_id][store_key][key] = value

        if invalid_fps_items:
            fps_msg = (
                "These entities have invalid fps value in custom attributes"
            )
            items = []
            for entity_id, value in invalid_fps_items:
                ent_path = self.get_ent_path(entity_id)
                items.append("{} - \"{}\"".format(ent_path, value))
            self.report_items["error"][fps_msg] = items

        # process hierarchical attributes
        self.set_hierarchical_attribute(
            hier_attrs, sync_ids, cust_attr_type_name_by_id
        )

    def set_hierarchical_attribute(
        self, hier_attrs, sync_ids, cust_attr_type_name_by_id
    ):
        # collect all hierarchical attribute keys
        # and prepare default values to project
        attributes_by_key = {}
        attribute_key_by_id = {}
        convert_types_by_attr_id = {}
        for attr in hier_attrs:
            key = attr["key"]
            attr_id = attr["id"]
            type_id = attr["type_id"]
            attribute_key_by_id[attr_id] = key
            attributes_by_key[key] = attr

            cust_attr_type_name = cust_attr_type_name_by_id[type_id]
            convert_type = get_python_type_for_custom_attribute(
                attr, cust_attr_type_name
            )
            convert_types_by_attr_id[attr_id] = convert_type

            self.hier_cust_attr_ids_by_key[key] = attr["id"]

            store_key = "hier_attrs"
            if key.startswith("avalon_"):
                store_key = "avalon_attrs"

            default_value = attr["default"]
            if key in FPS_KEYS:
                try:
                    default_value = convert_to_fps(default_value)
                except InvalidFpsValue:
                    pass

            self.entities_dict[self.ft_project_id][store_key][key] = (
                default_value
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

        for entity_dict in self.entities_dict.values():
            # Skip project because has stored defaults at the moment
            if entity_dict["entity_type"] == "project":
                continue
            entity_dict["hier_attrs"] = copy.deepcopy(prepare_dict)
            for key, val in prepare_dict_avalon.items():
                entity_dict["avalon_attrs"][key] = val

        items = query_custom_attributes(
            self.session,
            list(attribute_key_by_id.keys()),
            sync_ids,
            True
        )

        invalid_fps_items = []
        avalon_hier = []
        for item in items:
            value = item["value"]
            # WARNING It is not possible to propage enumerate hierachical
            # attributes with multiselection 100% right. Unseting all values
            # will cause inheritance from parent.
            if (
                value is None
                or (isinstance(value, (tuple, list)) and not value)
            ):
                continue

            attr_id = item["configuration_id"]
            convert_type = convert_types_by_attr_id[attr_id]
            if convert_type:
                value = convert_type(value)

            entity_id = item["entity_id"]
            key = attribute_key_by_id[attr_id]
            if key in FPS_KEYS:
                try:
                    value = convert_to_fps(value)
                except InvalidFpsValue:
                    invalid_fps_items.append((entity_id, value))
                    continue

            if key.startswith("avalon_"):
                store_key = "avalon_attrs"
                avalon_hier.append(key)
            else:
                store_key = "hier_attrs"
            self.entities_dict[entity_id][store_key][key] = value

        if invalid_fps_items:
            fps_msg = (
                "These entities have invalid fps value in custom attributes"
            )
            items = []
            for entity_id, value in invalid_fps_items:
                ent_path = self.get_ent_path(entity_id)
                items.append("{} - \"{}\"".format(ent_path, value))
            self.report_items["error"][fps_msg] = items

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

        hier_down_queue = collections.deque()
        hier_down_queue.append((project_values, top_id))

        while hier_down_queue:
            hier_values, parent_id = hier_down_queue.popleft()
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
                hier_down_queue.append((_hier_values, child_id))

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

    def _get_input_links(self, ftrack_ids):
        tupled_ids = tuple(ftrack_ids)
        mapping_by_to_id = {
            ftrack_id: set()
            for ftrack_id in tupled_ids
        }
        ids_len = len(tupled_ids)
        chunk_size = int(5000 / ids_len)
        all_links = []
        for chunk in create_chunks(ftrack_ids, chunk_size):
            entity_ids_joined = join_query_keys(chunk)

            all_links.extend(self.session.query((
                "select from_id, to_id from"
                " TypedContextLink where to_id in ({})"
            ).format(entity_ids_joined)).all())

        for context_link in all_links:
            to_id = context_link["to_id"]
            from_id = context_link["from_id"]
            if from_id == to_id:
                continue
            mapping_by_to_id[to_id].add(from_id)
        return mapping_by_to_id

    def prepare_ftrack_ent_data(self):
        not_set_ids = []
        for ftrack_id, entity_dict in self.entities_dict.items():
            entity = entity_dict["entity"]
            if entity is None:
                not_set_ids.append(ftrack_id)
                continue

            self.entities_dict[ftrack_id]["final_entity"] = {}
            self.entities_dict[ftrack_id]["final_entity"]["name"] = (
                entity_dict["name"]
            )
            data = {}
            data["ftrackId"] = entity["id"]
            data["entityType"] = entity_dict["entity_type_orig"]

            for key, val in entity_dict.get("custom_attributes", []).items():
                data[key] = val

            for key, val in entity_dict.get("hier_attrs", []).items():
                data[key] = val

            if ftrack_id != self.ft_project_id:
                data["description"] = entity["description"]

                ent_path_items = [ent["name"] for ent in entity["link"]]
                parents = ent_path_items[1:len(ent_path_items) - 1:]

                data["parents"] = parents
                data["tasks"] = self.entities_dict[ftrack_id].pop("tasks", {})
                self.entities_dict[ftrack_id]["final_entity"]["data"] = data
                self.entities_dict[ftrack_id]["final_entity"]["type"] = "asset"
                continue
            project_name = entity["full_name"]
            data["code"] = entity["name"]
            self.entities_dict[ftrack_id]["final_entity"]["data"] = data
            self.entities_dict[ftrack_id]["final_entity"]["type"] = (
                "project"
            )

            proj_schema = entity["project_schema"]
            task_types = proj_schema["_task_type_schema"]["types"]
            proj_apps, warnings = get_project_apps(
                data.pop("applications", [])
            )
            for msg, items in warnings.items():
                if not msg or not items:
                    continue
                self.report_items["warning"][msg] = items

            current_project_anatomy_data = get_anatomy_settings(
                project_name, exclude_locals=True
            )
            anatomy_tasks = current_project_anatomy_data["tasks"]
            tasks = {}
            default_type_data = {
                "short_name": ""
            }
            for task_type in task_types:
                task_type_name = task_type["name"]
                tasks[task_type_name] = copy.deepcopy(
                    anatomy_tasks.get(task_type_name)
                    or default_type_data
                )

            project_config = {
                "tasks": tasks,
                "apps": proj_apps
            }
            for key, value in current_project_anatomy_data.items():
                if key in project_config or key == "attributes":
                    continue
                project_config[key] = value

            self.entities_dict[ftrack_id]["final_entity"]["config"] = (
                project_config
            )

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
        prepare_queue = collections.deque()

        for child_id in self.entities_dict[self.ft_project_id]["children"]:
            prepare_queue.append(child_id)

        while prepare_queue:
            ftrack_id = prepare_queue.popleft()
            for child_id in self.entities_dict[ftrack_id]["children"]:
                prepare_queue.append(child_id)

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
                    parents = ent_path_items[1:len(ent_path_items) - 1:]
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

        children_queue = collections.deque()
        children_queue.append(ftrack_id)
        while children_queue:
            _ftrack_id = children_queue.popleft()
            entity_dict = self.entities_dict.pop(_ftrack_id, {"children": []})
            for child_id in entity_dict["children"]:
                children_queue.append(child_id)

    def set_input_links(self):
        ftrack_ids = set(self.create_ftrack_ids) | set(self.update_ftrack_ids)

        input_links_by_ftrack_id = self._get_input_links(ftrack_ids)

        for ftrack_id in ftrack_ids:
            input_links = []
            final_entity = self.entities_dict[ftrack_id]["final_entity"]
            final_entity["data"]["inputLinks"] = input_links
            link_ids = input_links_by_ftrack_id[ftrack_id]
            if not link_ids:
                continue

            for ftrack_link_id in link_ids:
                mongo_id = self.ftrack_avalon_mapper.get(ftrack_link_id)
                if mongo_id is not None:
                    input_links.append({
                        "id": ObjectId(mongo_id),
                        "linkedBy": "ftrack",
                        "type": "breakdown"
                    })

    def prepare_changes(self):
        self.log.debug("* Preparing changes for avalon/ftrack")
        hierarchy_changing_ids = []
        ignore_keys = collections.defaultdict(list)

        update_queue = collections.deque()
        for ftrack_id in self.update_ftrack_ids:
            update_queue.append(ftrack_id)

        while update_queue:
            ftrack_id = update_queue.popleft()
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
                        old_parent_name = "N/A"
                        if ftrack_parent_mongo_id in self.avalon_ents_by_id:
                            old_parent_name = (
                                self.avalon_ents_by_id
                                [ftrack_parent_mongo_id]
                                ["name"]
                            )

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
                update_queue.append(new_entity_id)

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

                _entity_key = collections.OrderedDict([
                    ("configuration_id", configuration_id),
                    ("entity_id", ftrack_id)
                ])

                self.session.recorded_operations.push(
                    ftrack_api.operation.UpdateEntityOperation(
                        "ContextCustomAttributeValue",
                        _entity_key,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        avalon_id
                    )
                )
            # Prepare task changes as they have to be stored as one key
            final_doc = self.entities_dict[ftrack_id]["final_entity"]
            final_doc_tasks = final_doc["data"].pop("tasks", None) or {}
            current_doc_tasks = avalon_entity["data"].get("tasks") or {}
            if not final_doc_tasks:
                update_tasks = True
            else:
                update_tasks = final_doc_tasks != current_doc_tasks

            # check rest of data
            data_changes = self.compare_dict(
                final_doc,
                avalon_entity,
                ignore_keys[ftrack_id]
            )
            if data_changes:
                self.updates[avalon_id] = self.merge_dicts(
                    data_changes,
                    self.updates[avalon_id]
                )

            # Add tasks back to final doc object
            final_doc["data"]["tasks"] = final_doc_tasks
            # Add tasks to updates if there are different
            if update_tasks:
                if "data" not in self.updates[avalon_id]:
                    self.updates[avalon_id]["data"] = {}
                self.updates[avalon_id]["data"]["tasks"] = final_doc_tasks

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
            if ftrack_id not in self.ftrack_avalon_mapper:
                self.create_avalon_entity(ftrack_id)

        self.set_input_links()

        unarchive_writes = []
        for item in self.unarchive_list:
            mongo_id = item["_id"]
            unarchive_writes.append(ReplaceOne(
                {"_id": mongo_id},
                item
            ))
            av_ent_path_items = item["data"]["parents"]
            av_ent_path_items.append(item["name"])
            av_ent_path = "/".join(av_ent_path_items)
            self.log.debug(
                "Entity was unarchived <{}>".format(av_ent_path)
            )
            self.remove_from_archived(mongo_id)

        if unarchive_writes:
            self.dbcon.bulk_write(unarchive_writes)

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
        item["schema"] = CURRENT_DOC_SCHEMAS["asset"]
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
        else:
            self.unarchive_list.append(item)

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
        project_item["schema"] = CURRENT_DOC_SCHEMAS["project"]
        project_item["config"]["schema"] = CURRENT_DOC_SCHEMAS["config"]

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
        unchangeable_queue = collections.deque()
        for entity_id in unchangeable_ids:
            unchangeable_queue.append((entity_id, False))

        processed_parents_ids = []
        subsets_to_remove = []
        while unchangeable_queue:
            entity_id, child_is_archived = unchangeable_queue.popleft()
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
            unchangeable_queue.append(
                (str(parent_id), child_is_archived)
            )

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
        """
            Runs changes converted to "$set" queries in bulk.
        """
        mongo_changes_bulk = []
        for mongo_id, changes in self.updates.items():
            mongo_id = ObjectId(mongo_id)
            is_project = mongo_id == self.avalon_project_id
            change_data = from_dict_to_set(changes, is_project)

            filter = {"_id": mongo_id}
            mongo_changes_bulk.append(UpdateOne(filter, change_data))
        if not mongo_changes_bulk:
            # TODO LOG
            return
        self.dbcon.bulk_write(mongo_changes_bulk)

    def reload_parents(self, hierarchy_changing_ids):
        parents_queue = collections.deque()
        parents_queue.append((self.ft_project_id, [], False))
        while parents_queue:
            ftrack_id, parent_parents, changed = parents_queue.popleft()
            _parents = copy.deepcopy(parent_parents)
            if ftrack_id not in hierarchy_changing_ids and not changed:
                if ftrack_id != self.ft_project_id:
                    _parents.append(self.entities_dict[ftrack_id]["name"])
                for child_id in self.entities_dict[ftrack_id]["children"]:
                    parents_queue.append(
                        (child_id, _parents, changed)
                    )
                continue

            changed = True
            parents = [par for par in _parents]
            hierarchy = "/".join(parents)
            self.entities_dict[ftrack_id][
                "final_entity"]["data"]["parents"] = parents

            _parents.append(self.entities_dict[ftrack_id]["name"])
            for child_id in self.entities_dict[ftrack_id]["children"]:
                parents_queue.append(
                    (child_id, _parents, changed)
                )

            if ftrack_id in self.create_ftrack_ids:
                mongo_id = self.ftrack_avalon_mapper[ftrack_id]
                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}
                self.updates[mongo_id]["data"]["parents"] = parents

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

        # Compare tasks from current project schema and previous project schema
        final_doc_data = self.entities_dict[self.ft_project_id]["final_entity"]
        final_doc_tasks = final_doc_data["config"].pop("tasks")
        current_doc_tasks = self.avalon_project.get("config", {}).get("tasks")
        # Update project's task types
        if not current_doc_tasks:
            update_tasks = True
        else:
            # Check if task types are same
            update_tasks = False
            for task_type in final_doc_tasks:
                if task_type not in current_doc_tasks:
                    update_tasks = True
                    break

            # Update new task types
            #   - but keep data about existing types and only add new one
            if update_tasks:
                for task_type, type_data in current_doc_tasks.items():
                    final_doc_tasks[task_type] = type_data

        changes = self.compare_dict(final_doc_data, self.avalon_project)

        # Put back tasks data to final entity object
        final_doc_data["config"]["tasks"] = final_doc_tasks

        # Add tasks updates if tasks changed
        if update_tasks:
            if "config" not in changes:
                changes["config"] = {}
            changes["config"]["tasks"] = final_doc_tasks
        return changes

    def compare_dict(self, dict_new, dict_old, _ignore_keys=[]):
        """
            Recursively compares and list changes between dictionaries
            'dict_new' and 'dict_old'.
            Keys in '_ignore_keys' are skipped and not compared.
        Args:
            dict_new (dictionary):
            dict_old (dictionary):
            _ignore_keys (list):

        Returns:
            (dictionary) of new or updated keys and theirs values
        """
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
        """
            Apply all new or updated keys from 'dict_new' on 'dict_old'.
            Recursively.
            Doesn't recognise that 'dict_new' doesn't contain some keys
            anymore.
        Args:
            dict_new (dictionary): from Ftrack most likely
            dict_old (dictionary): current in DB

        Returns:
            (dictionary) of applied changes to original dictionary
        """
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
        _type = av_entity["data"].get("entityType")
        # Check existence of object type
        if _type and _type not in self.object_types_by_name:
            _type = None

        if not _type:
            _type = "Folder"

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

        cust_attr, _ = get_openpype_attr(self.session)
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
