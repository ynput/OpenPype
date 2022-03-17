import collections
import copy
import json
import time
import datetime
import atexit
import traceback

from bson.objectid import ObjectId
from pymongo import UpdateOne

import arrow
import ftrack_api

from avalon import schema
from avalon.api import AvalonMongoDB

from openpype_modules.ftrack.lib import (
    get_openpype_attr,
    query_custom_attributes,
    CUST_ATTR_ID_KEY,
    CUST_ATTR_AUTO_SYNC,
    FPS_KEYS,

    avalon_sync,

    BaseEvent
)
from openpype_modules.ftrack.lib.avalon_sync import (
    convert_to_fps,
    InvalidFpsValue
)
from openpype.lib import CURRENT_DOC_SCHEMAS


class SyncToAvalonEvent(BaseEvent):
    interest_entTypes = ["show", "task"]
    ignore_ent_types = ["Milestone"]
    ignore_keys = ["statusid", "thumbid"]

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
        " from Project where id is \"{}\""
    )

    entities_query_by_id = (
        "select id, name, parent_id, link, custom_attributes, description"
        " from TypedContext where project_id is \"{}\" and id in ({})"
    )

    # useful for getting all tasks for asset
    task_entities_query_by_parent_id = (
        "select id, name, parent_id, type_id from Task"
        " where project_id is \"{}\" and parent_id in ({})"
    )
    task_types_query = (
        "select id, name from Type"
    )
    entities_name_query_by_name = (
        "select id, name from TypedContext"
        " where project_id is \"{}\" and name in ({})"
    )
    created_entities = []
    report_splitter = {"type": "label", "value": "---"}

    def __init__(self, session):
        '''Expects a ftrack_api.Session instance'''
        # Debug settings
        # - time expiration in seconds
        self.debug_print_time_expiration = 5 * 60
        # - store current time
        self.debug_print_time = datetime.datetime.now()
        # - store synchronize entity types to be able to use
        #   only entityTypes in interest instead of filtering by ignored
        self.debug_sync_types = collections.defaultdict(list)

        self.dbcon = AvalonMongoDB()
        # Set processing session to not use global
        self.set_process_session(session)
        super().__init__(session)

    def debug_logs(self):
        """This is debug method for printing small debugs messages. """
        now_datetime = datetime.datetime.now()
        delta = now_datetime - self.debug_print_time
        if delta.total_seconds() < self.debug_print_time_expiration:
            return

        self.debug_print_time = now_datetime
        known_types_items = []
        for entityType, entity_type in self.debug_sync_types.items():
            ent_types_msg = ", ".join(entity_type)
            known_types_items.append(
                "<{}> ({})".format(entityType, ent_types_msg)
            )

        known_entityTypes = ", ".join(known_types_items)
        self.log.debug(
            "DEBUG MESSAGE: Known types {}".format(known_entityTypes)
        )

    @property
    def cur_project(self):
        if self._cur_project is None:
            found_id = None
            for ent_info in self._cur_event["data"]["entities"]:
                if found_id is not None:
                    break
                parents = ent_info.get("parents") or []
                for parent in parents:
                    if parent.get("entityType") == "show":
                        found_id = parent.get("entityId")
                        break
            if found_id:
                self._cur_project = self.process_session.query(
                    self.project_query.format(found_id)
                ).one()
        return self._cur_project

    @property
    def avalon_cust_attrs(self):
        if self._avalon_cust_attrs is None:
            self._avalon_cust_attrs = get_openpype_attr(
                self.process_session, query_keys=self.cust_attr_query_keys
            )
        return self._avalon_cust_attrs

    @property
    def cust_attr_types_by_id(self):
        if self._cust_attr_types_by_id is None:
            cust_attr_types = self.process_session.query(
                "select id, name from CustomAttributeType"
            ).all()
            self._cust_attr_types_by_id = {
                cust_attr_type["id"]: cust_attr_type
                for cust_attr_type in cust_attr_types
            }
        return self._cust_attr_types_by_id

    @property
    def avalon_entities(self):
        if self._avalon_ents is None:
            self.dbcon.install()
            self.dbcon.Session["AVALON_PROJECT"] = (
                self.cur_project["full_name"]
            )
            avalon_project = self.dbcon.find_one({"type": "project"})
            avalon_entities = list(self.dbcon.find({"type": "asset"}))
            self._avalon_ents = (avalon_project, avalon_entities)
        return self._avalon_ents

    @property
    def avalon_ents_by_name(self):
        if self._avalon_ents_by_name is None:
            self._avalon_ents_by_name = {}
            proj, ents = self.avalon_entities
            for ent in ents:
                self._avalon_ents_by_name[ent["name"]] = ent
        return self._avalon_ents_by_name

    @property
    def avalon_ents_by_id(self):
        if self._avalon_ents_by_id is None:
            self._avalon_ents_by_id = {}
            proj, ents = self.avalon_entities
            if proj:
                self._avalon_ents_by_id[proj["_id"]] = proj
                for ent in ents:
                    self._avalon_ents_by_id[ent["_id"]] = ent
        return self._avalon_ents_by_id

    @property
    def avalon_ents_by_parent_id(self):
        if self._avalon_ents_by_parent_id is None:
            self._avalon_ents_by_parent_id = collections.defaultdict(list)
            proj, ents = self.avalon_entities
            for ent in ents:
                vis_par = ent["data"]["visualParent"]
                if vis_par is None:
                    vis_par = proj["_id"]
                self._avalon_ents_by_parent_id[vis_par].append(ent)
        return self._avalon_ents_by_parent_id

    @property
    def avalon_ents_by_ftrack_id(self):
        if self._avalon_ents_by_ftrack_id is None:
            self._avalon_ents_by_ftrack_id = {}
            proj, ents = self.avalon_entities
            if proj:
                ftrack_id = proj["data"].get("ftrackId")
                if ftrack_id is None:
                    self.handle_missing_ftrack_id(proj)
                    ftrack_id = proj["data"]["ftrackId"]
                self._avalon_ents_by_ftrack_id[ftrack_id] = proj

                self._avalon_ents_by_ftrack_id[ftrack_id] = proj
                for ent in ents:
                    ftrack_id = ent["data"].get("ftrackId")
                    if ftrack_id is None:
                        continue
                    self._avalon_ents_by_ftrack_id[ftrack_id] = ent
        return self._avalon_ents_by_ftrack_id

    def handle_missing_ftrack_id(self, doc):
        ftrack_id = doc["data"].get("ftrackId")
        if ftrack_id is not None:
            return

        if doc["type"] == "project":
            ftrack_id = self.cur_project["id"]

            self.dbcon.update_one(
                {"type": "project"},
                {"$set": {"data.ftrackId": ftrack_id}}
            )

            doc["data"]["ftrackId"] = ftrack_id
            return

        if doc["type"] != "asset":
            return

        doc_parents = doc.get("data", {}).get("parents")
        if doc_parents is None:
            return

        entities = self.process_session.query((
            "select id, link from TypedContext"
            " where project_id is \"{}\" and name is \"{}\""
        ).format(self.cur_project["id"], doc["name"])).all()
        matching_entity = None
        for entity in entities:
            parents = []
            for item in entity["link"]:
                if item["id"] == entity["id"]:
                    break
                low_type = item["type"].lower()
                if low_type == "typedcontext":
                    parents.append(item["name"])
            if doc_parents == parents:
                matching_entity = entity
                break

        if matching_entity is None:
            return

        ftrack_id = matching_entity["id"]
        self.dbcon.update_one(
            {"_id": doc["_id"]},
            {"$set": {"data.ftrackId": ftrack_id}}
        )

        self._avalon_ents_by_ftrack_id[ftrack_id] = doc

    @property
    def avalon_subsets_by_parents(self):
        if self._avalon_subsets_by_parents is None:
            self._avalon_subsets_by_parents = collections.defaultdict(list)
            self.dbcon.install()
            self.dbcon.Session["AVALON_PROJECT"] = (
                self.cur_project["full_name"]
            )
            for subset in self.dbcon.find({"type": "subset"}):
                self._avalon_subsets_by_parents[subset["parent"]].append(
                    subset
                )
        return self._avalon_subsets_by_parents

    @property
    def avalon_archived_by_id(self):
        if self._avalon_archived_by_id is None:
            self._avalon_archived_by_id = {}
            self.dbcon.install()
            self.dbcon.Session["AVALON_PROJECT"] = (
                self.cur_project["full_name"]
            )
            for asset in self.dbcon.find({"type": "archived_asset"}):
                self._avalon_archived_by_id[asset["_id"]] = asset
        return self._avalon_archived_by_id

    @property
    def avalon_archived_by_name(self):
        if self._avalon_archived_by_name is None:
            self._avalon_archived_by_name = {}
            for asset in self.avalon_archived_by_id.values():
                self._avalon_archived_by_name[asset["name"]] = asset
        return self._avalon_archived_by_name

    @property
    def changeability_by_mongo_id(self):
        """Return info about changeability of entity and it's parents."""
        if self._changeability_by_mongo_id is None:
            self._changeability_by_mongo_id = collections.defaultdict(
                lambda: True
            )
            avalon_project, avalon_entities = self.avalon_entities
            self._changeability_by_mongo_id[avalon_project["_id"]] = False
            self._bubble_changeability(
                list(self.avalon_subsets_by_parents.keys())
            )

        return self._changeability_by_mongo_id

    def remove_cached_by_key(self, key, values):
        if self._avalon_ents is None:
            return

        if not isinstance(values, (list, tuple)):
            values = [values]

        def get_found_data(entity):
            if not entity:
                return None
            return {
                "ftrack_id": entity["data"]["ftrackId"],
                "parent_id": entity["data"]["visualParent"],
                "_id": entity["_id"],
                "name": entity["name"],
                "entity": entity
            }

        if key == "id":
            key = "_id"
        elif key == "ftrack_id":
            key = "data.ftrackId"

        found_data = {}
        project, entities = self._avalon_ents
        key_items = key.split(".")
        for value in values:
            ent = None
            if key == "_id":
                if self._avalon_ents_by_id is not None:
                    ent = self._avalon_ents_by_id.get(value)

            elif key == "name":
                if self._avalon_ents_by_name is not None:
                    ent = self._avalon_ents_by_name.get(value)

            elif key == "data.ftrackId":
                if self._avalon_ents_by_ftrack_id is not None:
                    ent = self._avalon_ents_by_ftrack_id.get(value)

            if ent is None:
                for _ent in entities:
                    _temp = _ent
                    for item in key_items:
                        _temp = _temp[item]

                    if _temp == value:
                        ent = _ent
                        break

            found_data[value] = get_found_data(ent)

        for value in values:
            data = found_data[value]
            if not data:
                # TODO logging
                self.log.warning(
                    "Didn't found entity by key/value \"{}\" / \"{}\"".format(
                        key, value
                    )
                )
                continue

            ftrack_id = data["ftrack_id"]
            parent_id = data["parent_id"]
            mongo_id = data["_id"]
            name = data["name"]
            entity = data["entity"]

            project, ents = self._avalon_ents
            ents.remove(entity)
            self._avalon_ents = project, ents

            if self._avalon_ents_by_ftrack_id is not None:
                self._avalon_ents_by_ftrack_id.pop(ftrack_id, None)

            if self._avalon_ents_by_parent_id is not None:
                self._avalon_ents_by_parent_id[parent_id].remove(entity)

            if self._avalon_ents_by_id is not None:
                self._avalon_ents_by_id.pop(mongo_id, None)

            if self._avalon_ents_by_name is not None:
                self._avalon_ents_by_name.pop(name, None)

            if self._avalon_archived_by_id is not None:
                self._avalon_archived_by_id[mongo_id] = entity

    def _bubble_changeability(self, unchangeable_ids):
        unchangeable_queue = collections.deque()
        for entity_id in unchangeable_ids:
            unchangeable_queue.append((entity_id, False))

        processed_parents_ids = []
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
                    _subset_ids = [
                        str(sub["_id"]) for sub in
                        self.avalon_subsets_by_parents[entity_id]
                    ]
                    joined_subset_ids = "| ".join(_subset_ids)
                    self.log.warning((
                        "Parent <{}> for subsets <{}> does not exist"
                    ).format(str(entity_id), joined_subset_ids))
                else:
                    self.log.warning((
                        "In avalon are entities without valid parents that"
                        " lead to Project (should not cause errors)"
                        " - MongoId <{}>"
                    ).format(str(entity_id)))
                continue

            # skip if parent is project
            parent_id = entity["data"]["visualParent"]
            if parent_id is None:
                continue
            unchangeable_queue.append((parent_id, child_is_archived))

    def reset_variables(self):
        """Reset variables so each event callback has clear env."""
        self._cur_project = None

        self._avalon_cust_attrs = None
        self._cust_attr_types_by_id = None

        self._avalon_ents = None
        self._avalon_ents_by_id = None
        self._avalon_ents_by_parent_id = None
        self._avalon_ents_by_ftrack_id = None
        self._avalon_ents_by_name = None
        self._avalon_subsets_by_parents = None
        self._changeability_by_mongo_id = None
        self._avalon_archived_by_id = None
        self._avalon_archived_by_name = None

        self._ent_types_by_name = None

        self.ftrack_ents_by_id = {}
        self.obj_id_ent_type_map = {}
        self.ftrack_recreated_mapping = {}

        self.ftrack_added = {}
        self.ftrack_moved = {}
        self.ftrack_renamed = {}
        self.ftrack_updated = {}
        self.ftrack_removed = {}

        # set of ftrack ids with modified tasks
        # handled separately by full wipeout and replace from FTrack
        self.modified_tasks_ftrackids = set()

        self.moved_in_avalon = []
        self.renamed_in_avalon = []
        self.hier_cust_attrs_changes = collections.defaultdict(list)

        self.duplicated = []
        self.regex_failed = []

        self.regex_schemas = {}
        self.updates = collections.defaultdict(dict)

        self.report_items = {
            "info": collections.defaultdict(list),
            "warning": collections.defaultdict(list),
            "error": collections.defaultdict(list)
        }

    def set_process_session(self, session):
        try:
            self.process_session.close()
        except Exception:
            pass
        self.process_session = ftrack_api.Session(
            server_url=session.server_url,
            api_key=session.api_key,
            api_user=session.api_user,
            auto_connect_event_hub=True
        )
        atexit.register(lambda: self.process_session.close())

    def filter_updated(self, updates):
        filtered_updates = {}
        for ftrack_id, ent_info in updates.items():
            changed_keys = [k for k in (ent_info.get("keys") or [])]
            changes = {
                k: v for k, v in (ent_info.get("changes") or {}).items()
            }

            entity_type = ent_info["entity_type"]
            if entity_type == "Task":
                if "name" in changed_keys:
                    ent_info["keys"] = ["name"]
                    ent_info["changes"] = {"name": changes.pop("name")}
                    filtered_updates[ftrack_id] = ent_info
                continue

            for _key in self.ignore_keys:
                if _key in changed_keys:
                    changed_keys.remove(_key)
                    changes.pop(_key, None)

            if not changed_keys:
                continue

            # Remove custom attributes starting with `avalon_` from changes
            # - these custom attributes are not synchronized
            avalon_keys = []
            for key in changes:
                if key.startswith("avalon_"):
                    avalon_keys.append(key)

            for _key in avalon_keys:
                changed_keys.remove(_key)
                changes.pop(_key, None)

            if not changed_keys:
                continue

            ent_info["keys"] = changed_keys
            ent_info["changes"] = changes
            filtered_updates[ftrack_id] = ent_info

        return filtered_updates

    def get_ent_path(self, ftrack_id):
        """
            Looks for entity in FTrack with 'ftrack_id'. If found returns
            concatenated paths from its 'link' elemenent's names. Describes
            location of entity in tree.
        Args:
            ftrack_id (string): entityId of FTrack entity

        Returns:
            (string) - example : "/test_project/assets/my_asset"
        """
        entity = self.ftrack_ents_by_id.get(ftrack_id)
        if not entity:
            entity = self.process_session.query(
                self.entities_query_by_id.format(
                    self.cur_project["id"], ftrack_id
                )
            ).first()
            if entity:
                self.ftrack_ents_by_id[ftrack_id] = entity
            else:
                return "unknown hierarchy"
        return "/".join([ent["name"] for ent in entity["link"]])

    def launch(self, session, event):
        """
            Main entry port for synchronization.
            Goes through event (can contain multiple changes) and decides if
            the event is interesting for us (interest_entTypes).
            It separates changes into add|remove|update.
            All task changes are handled together by refresh from Ftrack.
        Args:
            session (object): session to Ftrack
            event (dictionary): event content

        Returns:
            (boolean or None)
        """
        # Try to commit and if any error happen then recreate session
        try:
            self.process_session.commit()
        except Exception:
            self.set_process_session(session)
        # Reset object values for each launch
        self.reset_variables()
        self._cur_event = event

        entities_by_action = {
            "remove": {},
            "update": {},
            "move": {},
            "add": {}
        }

        entities_info = event["data"]["entities"]
        found_actions = set()
        for ent_info in entities_info:
            entityType = ent_info["entityType"]
            if entityType not in self.interest_entTypes:
                continue

            entity_type = ent_info.get("entity_type")
            if not entity_type or entity_type in self.ignore_ent_types:
                continue

            if entity_type not in self.debug_sync_types[entityType]:
                self.debug_sync_types[entityType].append(entity_type)

            action = ent_info["action"]
            ftrack_id = ent_info["entityId"]
            if isinstance(ftrack_id, list):
                self.log.warning((
                    "BUG REPORT: Entity info has `entityId` as `list` \"{}\""
                ).format(ent_info))
                if len(ftrack_id) == 0:
                    continue
                ftrack_id = ftrack_id[0]

            # Skip deleted projects
            if action == "remove" and entityType == "show":
                return True

            # task modified, collect parent id of task, handle separately
            if entity_type.lower() == "task":
                changes = ent_info.get("changes") or {}
                if action == "move":
                    parent_changes = changes["parent_id"]
                    self.modified_tasks_ftrackids.add(parent_changes["new"])
                    self.modified_tasks_ftrackids.add(parent_changes["old"])

                elif "typeid" in changes or "name" in changes:
                    self.modified_tasks_ftrackids.add(ent_info["parentId"])
                continue

            if action == "move":
                ent_keys = ent_info["keys"]
                # Separate update info from move action
                if len(ent_keys) > 1:
                    _ent_info = ent_info.copy()
                    for ent_key in ent_keys:
                        if ent_key == "parent_id":
                            _ent_info["changes"].pop(ent_key, None)
                            _ent_info["keys"].remove(ent_key)
                        else:
                            ent_info["changes"].pop(ent_key, None)
                            ent_info["keys"].remove(ent_key)
                    entities_by_action["update"][ftrack_id] = _ent_info
            # regular change process handles all other than Tasks
            found_actions.add(action)
            entities_by_action[action][ftrack_id] = ent_info

        found_actions = list(found_actions)
        if not found_actions and not self.modified_tasks_ftrackids:
            return True

        # Check if auto sync was turned on/off
        updated = entities_by_action["update"]
        for ftrack_id, ent_info in updated.items():
            # filter project
            if ent_info["entityType"] != "show":
                continue

            changes = ent_info["changes"]
            if CUST_ATTR_AUTO_SYNC not in changes:
                continue

            auto_sync = changes[CUST_ATTR_AUTO_SYNC]["new"]
            if auto_sync == "1":
                # Trigger sync to avalon action if auto sync was turned on
                ft_project = self.cur_project
                self.log.debug((
                    "Auto sync was turned on for project <{}>."
                    " Triggering syncToAvalon action."
                ).format(ft_project["full_name"]))
                selection = [{
                    "entityId": ft_project["id"],
                    "entityType": "show"
                }]
                self.trigger_action(
                    action_name="sync.to.avalon.server",
                    event=event,
                    selection=selection
                )
            # Exit for both cases
            return True

        # Filter updated data by changed keys
        updated = self.filter_updated(updated)

        # skip most of events where nothing has changed for avalon
        if (
            len(found_actions) == 1
            and found_actions[0] == "update"
            and not updated
            and not self.modified_tasks_ftrackids
        ):
            return True

        ft_project = self.cur_project
        # Check if auto-sync custom attribute exists
        if CUST_ATTR_AUTO_SYNC not in ft_project["custom_attributes"]:
            # TODO should we sent message to someone?
            self.log.error((
                "Custom attribute \"{}\" is not created or user \"{}\" used"
                " for Event server don't have permissions to access it!"
            ).format(CUST_ATTR_AUTO_SYNC, self.session.api_user))
            return True

        # Skip if auto-sync is not set
        auto_sync = ft_project["custom_attributes"][CUST_ATTR_AUTO_SYNC]
        if auto_sync is not True:
            return True

        debug_msg = "Updated: {}".format(len(updated))
        debug_action_map = {
            "add": "Created",
            "remove": "Removed",
            "move": "Moved"
        }
        for action, infos in entities_by_action.items():
            if action == "update":
                continue
            _action = debug_action_map[action]
            debug_msg += "| {}: {}".format(_action, len(infos))

        self.log.debug("Project changes <{}>: {}".format(
            ft_project["full_name"], debug_msg
        ))
        # Get ftrack entities - find all ftrack ids first
        ftrack_ids = set(updated.keys())

        for action, _ftrack_ids in entities_by_action.items():
            # skip updated (already prepared) and removed (not exist in ftrack)
            if action not in ("remove", "update"):
                ftrack_ids |= set(_ftrack_ids)

        # collect entity records data which might not be in event
        if ftrack_ids:
            joined_ids = ", ".join(["\"{}\"".format(id) for id in ftrack_ids])
            ftrack_entities = self.process_session.query(
                self.entities_query_by_id.format(ft_project["id"], joined_ids)
            ).all()
            for entity in ftrack_entities:
                self.ftrack_ents_by_id[entity["id"]] = entity

        # Filter updates where name is changing
        for ftrack_id, ent_info in updated.items():
            ent_keys = ent_info["keys"]
            # Seprate update info from rename
            if "name" not in ent_keys:
                continue

            _ent_info = copy.deepcopy(ent_info)
            for ent_key in ent_keys:
                if ent_key == "name":
                    ent_info["changes"].pop(ent_key, None)
                    ent_info["keys"].remove(ent_key)
                else:
                    _ent_info["changes"].pop(ent_key, None)
                    _ent_info["keys"].remove(ent_key)

            self.ftrack_renamed[ftrack_id] = _ent_info

        self.ftrack_removed = entities_by_action["remove"]
        self.ftrack_moved = entities_by_action["move"]
        self.ftrack_added = entities_by_action["add"]
        self.ftrack_updated = updated

        self.debug_logs()

        self.log.debug("Synchronization begins")
        try:
            time_1 = time.time()
            # 1.) Process removed - may affect all other actions
            self.process_removed()
            time_2 = time.time()
            # 2.) Process renamed - may affect added
            self.process_renamed()
            time_3 = time.time()
            # 3.) Process added - moved entity may be moved to new entity
            self.process_added()
            time_4 = time.time()
            # 4.) Process moved
            self.process_moved()
            time_5 = time.time()
            # 5.) Process updated
            self.process_updated()
            time_6 = time.time()
            # 6.) Process changes in hierarchy or hier custom attribues
            self.process_hier_cleanup()
            time_7 = time.time()
            self.process_task_updates()
            if self.updates:
                self.update_entities()
            time_8 = time.time()

            time_removed = time_2 - time_1
            time_renamed = time_3 - time_2
            time_added = time_4 - time_3
            time_moved = time_5 - time_4
            time_updated = time_6 - time_5
            time_cleanup = time_7 - time_6
            time_task_updates = time_8 - time_7
            time_total = time_8 - time_1
            self.log.debug((
                "Process time: {:.2f} <{:.2f}, {:.2f}, {:.2f}, "
                "{:.2f}, {:.2f}, {:.2f}, {:.2f}>"
            ).format(
                time_total, time_removed, time_renamed, time_added,
                time_moved, time_updated, time_cleanup, time_task_updates
            ))

        except Exception:
            msg = "An error has happened during synchronization"
            self.report_items["error"][msg].append((
                str(traceback.format_exc()).replace("\n", "<br>")
            ).replace(" ", "&nbsp;"))

        self.report()
        return True

    def process_removed(self):
        """
            Handles removed entities (not removed tasks - handle separately).
        """
        if not self.ftrack_removed:
            return
        ent_infos = self.ftrack_removed
        self.log.debug(
            "Processing removed entities: {}".format(str(ent_infos))
        )
        removable_ids = []
        recreate_ents = []
        removed_names = []
        for ftrack_id, removed in ent_infos.items():
            entity_type = removed["entity_type"]
            if entity_type.lower() == "task":
                continue

            removed_name = removed["changes"]["name"]["old"]

            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                continue
            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                removable_ids.append(mongo_id)
                removed_names.append(removed_name)
            else:
                recreate_ents.append(avalon_ent)

        if removable_ids:
            # TODO logging
            self.log.debug("Assets marked as archived <{}>".format(
                ", ".join(removed_names)
            ))
            self.dbcon.update_many(
                {"_id": {"$in": removable_ids}, "type": "asset"},
                {"$set": {"type": "archived_asset"}}
            )
            self.remove_cached_by_key("id", removable_ids)

        if recreate_ents:
            # sort removed entities by parents len
            # - length of parents determine hierarchy level
            recreate_ents = sorted(
                recreate_ents,
                key=(lambda item: len(
                    (item.get("data", {}).get("parents") or [])
                ))
            )
            # TODO logging
            # TODO report
            recreate_msg = (
                "Deleted entity was recreated||Entity was recreated because"
                " it or its children contain published data"
            )
            proj, ents = self.avalon_entities
            for avalon_entity in recreate_ents:
                old_ftrack_id = avalon_entity["data"]["ftrackId"]
                vis_par = avalon_entity["data"]["visualParent"]
                if vis_par is None:
                    vis_par = proj["_id"]
                parent_ent = self.avalon_ents_by_id[vis_par]

                parent_ftrack_id = parent_ent["data"].get("ftrackId")
                if parent_ftrack_id is None:
                    self.handle_missing_ftrack_id(parent_ent)
                    parent_ftrack_id = parent_ent["data"].get("ftrackId")
                    if parent_ftrack_id is None:
                        continue

                parent_ftrack_ent = self.ftrack_ents_by_id.get(
                    parent_ftrack_id
                )
                if not parent_ftrack_ent:
                    if parent_ent["type"].lower() == "project":
                        parent_ftrack_ent = self.cur_project
                    else:
                        parent_ftrack_ent = self.process_session.query(
                            self.entities_query_by_id.format(
                                self.cur_project["id"], parent_ftrack_id
                            )
                        ).one()
                entity_type = avalon_entity["data"]["entityType"]
                new_entity = self.process_session.create(entity_type, {
                    "name": avalon_entity["name"],
                    "parent": parent_ftrack_ent
                })
                try:
                    self.process_session.commit()
                except Exception:
                    # TODO logging
                    # TODO report
                    self.process_session.rolback()
                    ent_path_items = [self.cur_project["full_name"]]
                    ent_path_items.extend([
                        par for par in avalon_entity["data"]["parents"]
                    ])
                    ent_path_items.append(avalon_entity["name"])
                    ent_path = "/".join(ent_path_items)

                    error_msg = "Couldn't recreate entity in Ftrack"
                    report_msg = (
                        "{}||Trying to recreate because it or its children"
                        " contain published data"
                    ).format(error_msg)
                    self.report_items["warning"][report_msg].append(ent_path)
                    self.log.warning(
                        "{}. Process session commit failed! <{}>".format(
                            error_msg, ent_path
                        ),
                        exc_info=True
                    )
                    continue

                new_entity_id = new_entity["id"]
                avalon_entity["data"]["ftrackId"] = new_entity_id

                for key, val in avalon_entity["data"].items():
                    if not val:
                        continue
                    if key not in new_entity["custom_attributes"]:
                        continue

                    new_entity["custom_attributes"][key] = val

                new_entity["custom_attributes"][CUST_ATTR_ID_KEY] = (
                    str(avalon_entity["_id"])
                )
                ent_path = self.get_ent_path(new_entity_id)

                try:
                    self.process_session.commit()
                except Exception:
                    # TODO logging
                    # TODO report
                    self.process_session.rolback()
                    error_msg = (
                        "Couldn't update custom attributes after recreation"
                        " of entity in Ftrack"
                    )
                    report_msg = (
                        "{}||Entity was recreated because it or its children"
                        " contain published data"
                    ).format(error_msg)
                    self.report_items["warning"][report_msg].append(ent_path)
                    self.log.warning(
                        "{}. Process session commit failed! <{}>".format(
                            error_msg, ent_path
                        ),
                        exc_info=True
                    )
                    continue

                self.report_items["info"][recreate_msg].append(ent_path)

                self.ftrack_recreated_mapping[old_ftrack_id] = new_entity_id
                self.process_session.commit()

                found_idx = None
                proj_doc, asset_docs = self._avalon_ents
                for idx, asset_doc in enumerate(asset_docs):
                    if asset_doc["_id"] == avalon_entity["_id"]:
                        found_idx = idx
                        break

                if found_idx is None:
                    continue

                # Prepare updates dict for mongo update
                if "data" not in self.updates[avalon_entity["_id"]]:
                    self.updates[avalon_entity["_id"]]["data"] = {}

                self.updates[avalon_entity["_id"]]["data"]["ftrackId"] = (
                    new_entity_id
                )
                # Update cached entities
                asset_docs[found_idx] = avalon_entity
                self._avalon_ents = proj_doc, asset_docs

                if self._avalon_ents_by_id is not None:
                    mongo_id = avalon_entity["_id"]
                    self._avalon_ents_by_id[mongo_id] = avalon_entity

                if self._avalon_ents_by_parent_id is not None:
                    vis_par = avalon_entity["data"]["visualParent"]
                    children = self._avalon_ents_by_parent_id[vis_par]
                    found_idx = None
                    for idx, _entity in enumerate(children):
                        if _entity["_id"] == avalon_entity["_id"]:
                            found_idx = idx
                            break
                    children[found_idx] = avalon_entity
                    self._avalon_ents_by_parent_id[vis_par] = children

                if self._avalon_ents_by_ftrack_id is not None:
                    self._avalon_ents_by_ftrack_id.pop(old_ftrack_id)
                    self._avalon_ents_by_ftrack_id[new_entity_id] = (
                        avalon_entity
                    )

                if self._avalon_ents_by_name is not None:
                    name = avalon_entity["name"]
                    self._avalon_ents_by_name[name] = avalon_entity

        # Check if entities with same name can be synchronized
        if not removed_names:
            return

        self.check_names_synchronizable(removed_names)

    def check_names_synchronizable(self, names):
        """Check if entities with specific names are importable.

        This check should happend after removing entity or renaming entity.
        When entity was removed or renamed then it's name is possible to sync.
        """
        joined_passed_names = ", ".join(
            ["\"{}\"".format(name) for name in names]
        )
        same_name_entities = self.process_session.query(
            self.entities_name_query_by_name.format(
                self.cur_project["id"], joined_passed_names
            )
        ).all()
        if not same_name_entities:
            return

        entities_by_name = collections.defaultdict(list)
        for entity in same_name_entities:
            entities_by_name[entity["name"]].append(entity)

        synchronizable_ents = []
        self.log.debug((
            "Deleting of entities should allow to synchronize another entities"
            " with same name."
        ))
        for name, ents in entities_by_name.items():
            if len(ents) != 1:
                self.log.debug((
                    "Name \"{}\" still have more than one entity <{}>"
                ).format(
                    name, "| ".join(
                        [self.get_ent_path(ent["id"]) for ent in ents]
                    )
                ))
                continue

            entity = ents[0]
            ent_path = self.get_ent_path(entity["id"])
            # TODO logging
            self.log.debug(
                "Checking if can synchronize entity <{}>".format(ent_path)
            )
            # skip if already synchronized
            ftrack_id = entity["id"]
            if ftrack_id in self.avalon_ents_by_ftrack_id:
                # TODO logging
                self.log.debug(
                    "- Entity is already synchronized (skipping) <{}>".format(
                        ent_path
                    )
                )
                continue

            parent_id = entity["parent_id"]
            if parent_id not in self.avalon_ents_by_ftrack_id:
                # TODO logging
                self.log.debug((
                    "- Entity's parent entity doesn't seems to"
                    " be synchronized (skipping) <{}>"
                ).format(ent_path))
                continue

            synchronizable_ents.append(entity)

        if not synchronizable_ents:
            return

        synchronizable_ents = sorted(
            synchronizable_ents,
            key=(lambda entity: len(entity["link"]))
        )

        children_queue = collections.deque()
        for entity in synchronizable_ents:
            parent_avalon_ent = self.avalon_ents_by_ftrack_id[
                entity["parent_id"]
            ]
            self.create_entity_in_avalon(entity, parent_avalon_ent)

            for child in entity["children"]:
                if child.entity_type.lower() != "task":
                    children_queue.append(child)

        while children_queue:
            entity = children_queue.popleft()
            ftrack_id = entity["id"]
            name = entity["name"]
            ent_by_ftrack_id = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if ent_by_ftrack_id:
                raise Exception((
                    "This is bug, parent was just synchronized to avalon"
                    " but entity is already in database {}"
                ).format(dict(entity)))

            # Entity has duplicated name with another entity
            # - may be renamed: in that case renaming method will handle that
            duplicate_ent = self.avalon_ents_by_name.get(name)
            if duplicate_ent:
                continue

            passed_regex = avalon_sync.check_regex(
                name, "asset", schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                continue

            parent_id = entity["parent_id"]
            parent_avalon_ent = self.avalon_ents_by_ftrack_id[parent_id]

            self.create_entity_in_avalon(entity, parent_avalon_ent)

            for child in entity["children"]:
                if child.entity_type.lower() == "task":
                    continue
                children_queue.append(child)

    def create_entity_in_avalon(self, ftrack_ent, parent_avalon):
        proj, ents = self.avalon_entities

        # Parents, Hierarchy
        ent_path_items = [ent["name"] for ent in ftrack_ent["link"]]
        parents = ent_path_items[1:len(ent_path_items)-1:]

        # TODO logging
        self.log.debug(
            "Trying to synchronize entity <{}>".format(
                "/".join(ent_path_items)
            )
        )

        # Add entity to modified so tasks are added at the end
        self.modified_tasks_ftrackids.add(ftrack_ent["id"])

        # Visual Parent
        vis_par = None
        if parent_avalon["type"].lower() != "project":
            vis_par = parent_avalon["_id"]

        mongo_id = ObjectId()
        name = ftrack_ent["name"]
        final_entity = {
            "_id": mongo_id,
            "name": name,
            "type": "asset",
            "schema": CURRENT_DOC_SCHEMAS["asset"],
            "parent": proj["_id"],
            "data": {
                "ftrackId": ftrack_ent["id"],
                "entityType": ftrack_ent.entity_type,
                "parents": parents,
                "tasks": {},
                "visualParent": vis_par,
                "description": ftrack_ent["description"]
            }
        }
        invalid_fps_items = []
        cust_attrs = self.get_cust_attr_values(ftrack_ent)
        for key, val in cust_attrs.items():
            if key.startswith("avalon_"):
                continue

            if key in FPS_KEYS:
                try:
                    val = convert_to_fps(val)
                except InvalidFpsValue:
                    invalid_fps_items.append((ftrack_ent["id"], val))
                    continue

            final_entity["data"][key] = val

        if invalid_fps_items:
            fps_msg = (
                "These entities have invalid fps value in custom attributes"
            )
            items = []
            for entity_id, value in invalid_fps_items:
                ent_path = self.get_ent_path(entity_id)
                items.append("{} - \"{}\"".format(ent_path, value))
            self.report_items["error"][fps_msg] = items

        _mongo_id_str = cust_attrs.get(CUST_ATTR_ID_KEY)
        if _mongo_id_str:
            try:
                _mongo_id = ObjectId(_mongo_id_str)
                if _mongo_id not in self.avalon_ents_by_id:
                    mongo_id = _mongo_id
                    final_entity["_id"] = mongo_id

            except Exception:
                pass

        ent_path_items = [self.cur_project["full_name"]]
        ent_path_items.extend([par for par in parents])
        ent_path_items.append(name)
        ent_path = "/".join(ent_path_items)

        try:
            schema.validate(final_entity)
        except Exception:
            # TODO logging
            # TODO report
            error_msg = (
                "Schema validation failed for new entity (This is a bug)"
            )
            error_traceback = (
                str(traceback.format_exc()).replace("\n", "<br>")
            ).replace(" ", "&nbsp;")

            item_msg = ent_path + "<br>" + error_traceback
            self.report_items["error"][error_msg].append(item_msg)
            self.log.error(
                "{}: \"{}\"".format(error_msg, str(final_entity)),
                exc_info=True
            )
            return None

        replaced = False
        archived = self.avalon_archived_by_name.get(name)
        if archived:
            archived_id = archived["_id"]
            if (
                archived["data"]["parents"] == parents or
                self.changeability_by_mongo_id[archived_id]
            ):
                # TODO logging
                self.log.debug(
                    "Entity was unarchived instead of creation <{}>".format(
                        ent_path
                    )
                )
                mongo_id = archived_id
                final_entity["_id"] = mongo_id
                self.dbcon.replace_one({"_id": mongo_id}, final_entity)
                replaced = True

        if not replaced:
            self.dbcon.insert_one(final_entity)
            # TODO logging
            self.log.debug("Entity was synchronized <{}>".format(ent_path))

        mongo_id_str = str(mongo_id)
        if mongo_id_str != ftrack_ent["custom_attributes"][CUST_ATTR_ID_KEY]:
            ftrack_ent["custom_attributes"][CUST_ATTR_ID_KEY] = mongo_id_str
            try:
                self.process_session.commit()
            except Exception:
                self.process_session.rolback()
                # TODO logging
                # TODO report
                error_msg = (
                    "Failed to store MongoID to entity's custom attribute"
                )
                report_msg = (
                    "{}||SyncToAvalon action may solve this issue"
                ).format(error_msg)

                self.report_items["warning"][report_msg].append(ent_path)
                self.log.error(
                    "{}: \"{}\"".format(error_msg, ent_path),
                    exc_info=True
                )

        # modify cached data
        # Skip if self._avalon_ents is not set(maybe never happen)
        if self._avalon_ents is None:
            return final_entity

        if self._avalon_ents is not None:
            proj, ents = self._avalon_ents
            ents.append(final_entity)
            self._avalon_ents = (proj, ents)

        if self._avalon_ents_by_id is not None:
            self._avalon_ents_by_id[mongo_id] = final_entity

        if self._avalon_ents_by_parent_id is not None:
            self._avalon_ents_by_parent_id[vis_par].append(final_entity)

        if self._avalon_ents_by_ftrack_id is not None:
            self._avalon_ents_by_ftrack_id[ftrack_ent["id"]] = final_entity

        if self._avalon_ents_by_name is not None:
            self._avalon_ents_by_name[ftrack_ent["name"]] = final_entity

        return final_entity

    def get_cust_attr_values(self, entity):
        output = {}
        custom_attrs, hier_attrs = self.avalon_cust_attrs

        # Notmal custom attributes
        for attr in custom_attrs:
            key = attr["key"]
            if key in entity["custom_attributes"]:
                output[key] = entity["custom_attributes"][key]

        hier_values = avalon_sync.get_hierarchical_attributes_values(
            self.process_session,
            entity,
            hier_attrs,
            self.cust_attr_types_by_id.values()
        )
        for key, val in hier_values.items():
            output[key] = val

        # Make sure mongo id is not set
        output.pop(CUST_ATTR_ID_KEY, None)

        return output

    def process_renamed(self):
        ent_infos = self.ftrack_renamed
        if not ent_infos:
            return

        self.log.debug(
            "Processing renamed entities: {}".format(str(ent_infos))
        )

        changeable_queue = collections.deque()
        for ftrack_id, ent_info in ent_infos.items():
            entity_type = ent_info["entity_type"]
            if entity_type == "Task":
                continue

            new_name = ent_info["changes"]["name"]["new"]
            old_name = ent_info["changes"]["name"]["old"]

            ent_path = self.get_ent_path(ftrack_id)
            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                # TODO logging
                self.log.debug((
                    "Entity is not is avalon. Moving to \"add\" process. <{}>"
                ).format(ent_path))
                self.ftrack_added[ftrack_id] = ent_info
                continue

            if new_name == avalon_ent["name"]:
                # TODO logging
                self.log.debug((
                    "Avalon entity already has the same name <{}>"
                ).format(ent_path))
                continue

            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                changeable_queue.append((ftrack_id, avalon_ent, new_name))
            else:
                ftrack_ent = self.ftrack_ents_by_id[ftrack_id]
                ftrack_ent["name"] = avalon_ent["name"]
                try:
                    self.process_session.commit()
                    # TODO logging
                    # TODO report
                    error_msg = "Entity renamed back"
                    report_msg = (
                        "{}||It is not possible to change"
                        " the name of an entity or it's parents, "
                        " if it already contained published data."
                    ).format(error_msg)
                    self.report_items["info"][report_msg].append(ent_path)
                    self.log.warning("{} <{}>".format(error_msg, ent_path))

                except Exception:
                    self.process_session.rollback()
                    # TODO report
                    # TODO logging
                    error_msg = (
                        "Couldn't rename the entity back to its original name"
                    )
                    report_msg = (
                        "{}||Renamed because it is not possible to"
                        " change the name of an entity or it's parents, "
                        " if it already contained published data."
                    ).format(error_msg)
                    error_traceback = (
                        str(traceback.format_exc()).replace("\n", "<br>")
                    ).replace(" ", "&nbsp;")

                    item_msg = ent_path + "<br>" + error_traceback
                    self.report_items["warning"][report_msg].append(item_msg)
                    self.log.warning(
                        "{}: \"{}\"".format(error_msg, ent_path),
                        exc_info=True
                    )

        old_names = []
        # Process renaming in Avalon DB
        while changeable_queue:
            ftrack_id, avalon_ent, new_name = changeable_queue.popleft()
            mongo_id = avalon_ent["_id"]
            old_name = avalon_ent["name"]

            _entity_type = "asset"
            if entity_type == "Project":
                _entity_type = "project"

            passed_regex = avalon_sync.check_regex(
                new_name, _entity_type, schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                self.regex_failed.append(ftrack_id)
                continue

            # if avalon does not have same name then can be changed
            same_name_avalon_ent = self.avalon_ents_by_name.get(new_name)
            if not same_name_avalon_ent:
                old_val = self._avalon_ents_by_name.pop(old_name)
                old_val["name"] = new_name
                self._avalon_ents_by_name[new_name] = old_val
                self.updates[mongo_id] = {"name": new_name}
                self.renamed_in_avalon.append(mongo_id)

                old_names.append(old_name)
                if new_name in old_names:
                    old_names.remove(new_name)

                # TODO logging
                ent_path = self.get_ent_path(ftrack_id)
                self.log.debug(
                    "Name of entity will be changed to \"{}\" <{}>".format(
                        new_name, ent_path
                    )
                )
                continue

            # Check if same name is in changable_queue
            # - it's name may be changed in next iteration
            same_name_ftrack_id = same_name_avalon_ent["data"]["ftrackId"]
            same_is_unprocessed = False
            for item in changeable_queue:
                if same_name_ftrack_id == item[0]:
                    same_is_unprocessed = True
                    break

            if same_is_unprocessed:
                changeable_queue.append((ftrack_id, avalon_ent, new_name))
                continue

            self.duplicated.append(ftrack_id)

        if old_names:
            self.check_names_synchronizable(old_names)

        # not_found are not processed since all not found are
        # not found because they are not synchronizable

    def process_added(self):
        ent_infos = self.ftrack_added
        if not ent_infos:
            return

        self.log.debug(
            "Processing added entities: {}".format(str(ent_infos))
        )

        cust_attrs, hier_attrs = self.avalon_cust_attrs
        entity_type_conf_ids = {}
        # Skip if already exit in avalon db or tasks entities
        # - happen when was created by any sync event/action
        pop_out_ents = []
        for ftrack_id, ent_info in ent_infos.items():
            if self.avalon_ents_by_ftrack_id.get(ftrack_id):
                pop_out_ents.append(ftrack_id)
                self.log.warning(
                    "Added entity is already synchronized <{}>".format(
                        self.get_ent_path(ftrack_id)
                    )
                )
                continue

            entity_type = ent_info["entity_type"]
            if entity_type == "Task":
                continue

            name = (
                ent_info
                .get("changes", {})
                .get("name", {})
                .get("new")
            )
            avalon_ent_by_name = self.avalon_ents_by_name.get(name) or {}
            avalon_ent_by_name_ftrack_id = (
                avalon_ent_by_name
                .get("data", {})
                .get("ftrackId")
            )
            if avalon_ent_by_name and avalon_ent_by_name_ftrack_id is None:
                ftrack_ent = self.ftrack_ents_by_id.get(ftrack_id)
                if not ftrack_ent:
                    ftrack_ent = self.process_session.query(
                        self.entities_query_by_id.format(
                            self.cur_project["id"], ftrack_id
                        )
                    ).one()
                    self.ftrack_ents_by_id[ftrack_id] = ftrack_ent

                ent_path_items = [ent["name"] for ent in ftrack_ent["link"]]
                parents = ent_path_items[1:len(ent_path_items)-1:]

                avalon_ent_parents = (
                    avalon_ent_by_name.get("data", {}).get("parents")
                )
                if parents == avalon_ent_parents:
                    self.dbcon.update_one({
                        "_id": avalon_ent_by_name["_id"]
                    }, {
                        "$set": {
                            "data.ftrackId": ftrack_id,
                            "data.entityType": entity_type
                        }
                    })

                    avalon_ent_by_name["data"]["ftrackId"] = ftrack_id
                    avalon_ent_by_name["data"]["entityType"] = entity_type

                    self._avalon_ents_by_ftrack_id[ftrack_id] = (
                        avalon_ent_by_name
                    )
                    if self._avalon_ents_by_parent_id:
                        found = None
                        for _parent_id_, _entities_ in (
                            self._avalon_ents_by_parent_id.items()
                        ):
                            for _idx_, entity in enumerate(_entities_):
                                if entity["_id"] == avalon_ent_by_name["_id"]:
                                    found = (_parent_id_, _idx_)
                                    break

                            if found:
                                break

                        if found:
                            _parent_id_, _idx_ = found
                            self._avalon_ents_by_parent_id[_parent_id_][
                                _idx_] = avalon_ent_by_name

                    if self._avalon_ents_by_id:
                        self._avalon_ents_by_id[avalon_ent_by_name["_id"]] = (
                            avalon_ent_by_name
                        )

                    if self._avalon_ents_by_name:
                        self._avalon_ents_by_name[name] = avalon_ent_by_name

                    if self._avalon_ents:
                        found = None
                        project, entities = self._avalon_ents
                        for _idx_, _ent_ in enumerate(entities):
                            if _ent_["_id"] != avalon_ent_by_name["_id"]:
                                continue
                            found = _idx_
                            break

                        if found is not None:
                            entities[found] = avalon_ent_by_name
                            self._avalon_ents = project, entities

                    pop_out_ents.append(ftrack_id)
                    continue

            mongo_id_configuration_id = self._mongo_id_configuration(
                ent_info,
                cust_attrs,
                hier_attrs,
                entity_type_conf_ids
            )
            if not mongo_id_configuration_id:
                self.log.warning((
                    "BUG REPORT: Missing MongoID configuration for `{} < {} >`"
                ).format(entity_type, ent_info["entityType"]))
                continue

            _entity_key = collections.OrderedDict()
            _entity_key["configuration_id"] = mongo_id_configuration_id
            _entity_key["entity_id"] = ftrack_id

            self.process_session.recorded_operations.push(
                ftrack_api.operation.UpdateEntityOperation(
                    "ContextCustomAttributeValue",
                    _entity_key,
                    "value",
                    ftrack_api.symbol.NOT_SET,
                    ""
                )
            )

        try:
            # Commit changes of mongo_id to empty string
            self.process_session.commit()
            self.log.debug("Committing unsetting")
        except Exception:
            self.process_session.rollback()
            # TODO logging
            msg = (
                "Could not set value of Custom attribute, where mongo id"
                " is stored, to empty string. Ftrack ids: \"{}\""
            ).format(", ".join(ent_infos.keys()))
            self.log.warning(msg, exc_info=True)

        for ftrack_id in pop_out_ents:
            ent_infos.pop(ftrack_id)

        # sort by parents length (same as by hierarchy level)
        _ent_infos = sorted(
            ent_infos.values(),
            key=(lambda ent_info: len(ent_info.get("parents", [])))
        )
        to_sync_by_id = collections.OrderedDict()
        for ent_info in _ent_infos:
            ft_id = ent_info["entityId"]
            to_sync_by_id[ft_id] = self.ftrack_ents_by_id[ft_id]

        # cache regex success (for tasks)
        for ftrack_id, entity in to_sync_by_id.items():
            if entity.entity_type.lower() == "project":
                raise Exception((
                    "Project can't be created with event handler!"
                    "This is a bug"
                ))
            parent_id = entity["parent_id"]
            parent_avalon = self.avalon_ents_by_ftrack_id.get(parent_id)
            if not parent_avalon:
                # TODO logging
                self.log.debug((
                    "Skipping synchronization of entity"
                    " because parent was not found in Avalon DB <{}>"
                ).format(self.get_ent_path(ftrack_id)))
                continue

            is_synchonizable = True
            name = entity["name"]
            passed_regex = avalon_sync.check_regex(
                name, "asset", schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                self.regex_failed.append(ftrack_id)
                is_synchonizable = False

            if name in self.avalon_ents_by_name:
                self.duplicated.append(ftrack_id)
                is_synchonizable = False

            if not is_synchonizable:
                continue

            self.create_entity_in_avalon(entity, parent_avalon)

    def process_moved(self):
        """
            Handles moved entities to different place in hiearchy.
            (Not tasks - handled separately.)
        """
        if not self.ftrack_moved:
            return

        self.log.debug(
            "Processing moved entities: {}".format(str(self.ftrack_moved))
        )

        ftrack_moved = {k: v for k, v in sorted(
            self.ftrack_moved.items(),
            key=(lambda line: len(
                (line[1].get("data", {}).get("parents") or [])
            ))
        )}

        for ftrack_id, ent_info in ftrack_moved.items():
            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                continue

            new_parent_id = ent_info["changes"]["parent_id"]["new"]
            old_parent_id = ent_info["changes"]["parent_id"]["old"]

            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                par_av_ent = self.avalon_ents_by_ftrack_id.get(new_parent_id)
                if not par_av_ent:
                    # TODO logging
                    # TODO report
                    ent_path_items = [self.cur_project["full_name"]]
                    ent_path_items.extend(avalon_ent["data"]["parents"])
                    ent_path_items.append(avalon_ent["name"])
                    ent_path = "/".join(ent_path_items)

                    error_msg = (
                        "New parent of entity is not synchronized to avalon"
                    )
                    report_msg = (
                        "{}||Parent in Avalon can't be changed. That"
                        " may cause issues. Please fix parent or move entity"
                        " under valid entity."
                    ).format(error_msg)

                    self.report_items["warning"][report_msg].append(ent_path)
                    self.log.warning("{} <{}>".format(error_msg, ent_path))
                    continue

                # THIS MUST HAPPEND AFTER CREATING NEW ENTITIES !!!!
                # - because may be moved to new created entity
                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}

                vis_par_id = None
                ent_path_items = [self.cur_project["full_name"]]
                if par_av_ent["type"].lower() != "project":
                    vis_par_id = par_av_ent["_id"]
                    ent_path_items.extend(par_av_ent["data"]["parents"])
                    ent_path_items.append(par_av_ent["name"])

                self.updates[mongo_id]["data"]["visualParent"] = vis_par_id
                self.moved_in_avalon.append(mongo_id)

                ent_path_items.append(avalon_ent["name"])
                ent_path = "/".join(ent_path_items)
                self.log.debug((
                    "Parent of entity ({}) was changed in avalon <{}>"
                    ).format(str(mongo_id), ent_path)
                )

            else:
                avalon_ent = self.avalon_ents_by_id[mongo_id]
                avalon_parent_id = avalon_ent["data"]["visualParent"]
                if avalon_parent_id is None:
                    avalon_parent_id = avalon_ent["parent"]

                avalon_parent = self.avalon_ents_by_id[avalon_parent_id]
                parent_id = avalon_parent["data"]["ftrackId"]

                # For cases when parent was deleted at the same time
                if parent_id in self.ftrack_recreated_mapping:
                    parent_id = (
                        self.ftrack_recreated_mapping[parent_id]
                    )

                ftrack_ent = self.ftrack_ents_by_id.get(ftrack_id)
                if not ftrack_ent:
                    ftrack_ent = self.process_session.query(
                        self.entities_query_by_id.format(
                            self.cur_project["id"], ftrack_id
                        )
                    ).one()
                    self.ftrack_ents_by_id[ftrack_id] = ftrack_ent

                if parent_id == ftrack_ent["parent_id"]:
                    continue

                ftrack_ent["parent_id"] = parent_id
                try:
                    self.process_session.commit()
                    # TODO logging
                    # TODO report
                    msg = "Entity was moved back"
                    report_msg = (
                        "{}||Entity can't be moved when"
                        " it or its children contain published data"
                    ).format(msg)
                    ent_path = self.get_ent_path(ftrack_id)
                    self.report_items["info"][report_msg].append(ent_path)
                    self.log.warning("{} <{}>".format(msg, ent_path))

                except Exception:
                    self.process_session.rollback()
                    # TODO logging
                    # TODO report
                    error_msg = (
                        "Couldn't moved the entity back to its original parent"
                    )
                    report_msg = (
                        "{}||Moved back because it is not possible to"
                        " move with an entity or it's parents, "
                        " if it already contained published data."
                    ).format(error_msg)
                    error_traceback = (
                        str(traceback.format_exc()).replace("\n", "<br>")
                    ).replace(" ", "&nbsp;")

                    item_msg = ent_path + "<br>" + error_traceback
                    self.report_items["warning"][report_msg].append(item_msg)
                    self.log.warning(
                        "{}: \"{}\"".format(error_msg, ent_path),
                        exc_info=True
                    )

    def process_updated(self):
        """
            Only custom attributes changes should get here
        """
        if not self.ftrack_updated:
            return

        self.log.debug(
            "Processing updated entities: {}".format(str(self.ftrack_updated))
        )

        ent_infos = self.ftrack_updated
        ftrack_mongo_mapping = {}
        not_found_ids = []
        for ftrack_id, ent_info in ent_infos.items():
            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                not_found_ids.append(ftrack_id)
                continue

            ftrack_mongo_mapping[ftrack_id] = avalon_ent["_id"]

        for ftrack_id in not_found_ids:
            ent_infos.pop(ftrack_id)

        if not ent_infos:
            return

        cust_attrs, hier_attrs = self.avalon_cust_attrs
        hier_attrs_by_key = {
            attr["key"]: attr
            for attr in hier_attrs
        }
        cust_attrs_by_obj_id = collections.defaultdict(dict)
        for cust_attr in cust_attrs:
            key = cust_attr["key"]
            if key.startswith("avalon_"):
                continue

            ca_ent_type = cust_attr["entity_type"]

            if ca_ent_type == "show":
                cust_attrs_by_obj_id[ca_ent_type][key] = cust_attr

            elif ca_ent_type == "task":
                obj_id = cust_attr["object_type_id"]
                cust_attrs_by_obj_id[obj_id][key] = cust_attr

        for ftrack_id, ent_info in ent_infos.items():
            mongo_id = ftrack_mongo_mapping[ftrack_id]
            entType = ent_info["entityType"]
            ent_path = self.get_ent_path(ftrack_id)
            if entType == "show":
                ent_cust_attrs = cust_attrs_by_obj_id.get("show")
            else:
                obj_type_id = ent_info["objectTypeId"]
                ent_cust_attrs = cust_attrs_by_obj_id.get(obj_type_id)

            # Ftrack's entity_type does not have defined custom attributes
            if ent_cust_attrs is None:
                ent_cust_attrs = {}

            ent_changes = ent_info["changes"]
            if "description" in ent_changes:
                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}
                self.updates[mongo_id]["data"]["description"] = (
                    ent_changes["description"]["new"] or ""
                )

            for key, values in ent_changes.items():
                if key in hier_attrs_by_key:
                    self.hier_cust_attrs_changes[key].append(ftrack_id)
                    continue

                if key not in ent_cust_attrs:
                    continue

                value = values["new"]
                new_value = self.convert_value_by_cust_attr_conf(
                    value, ent_cust_attrs[key]
                )

                if entType == "show" and key == "applications":
                    # Store apps to project't config
                    proj_apps, warnings = (
                        avalon_sync.get_project_apps(new_value)
                    )
                    if "config" not in self.updates[mongo_id]:
                        self.updates[mongo_id]["config"] = {}
                    self.updates[mongo_id]["config"]["apps"] = proj_apps

                    for msg, items in warnings.items():
                        if not msg or not items:
                            continue
                        self.report_items["warning"][msg] = items
                    continue

                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}
                self.updates[mongo_id]["data"][key] = new_value
                self.log.debug(
                    "Setting data value of \"{}\" to \"{}\" <{}>".format(
                        key, new_value, ent_path
                    )
                )

    def convert_value_by_cust_attr_conf(self, value, cust_attr_conf):
        type_id = cust_attr_conf["type_id"]
        cust_attr_type_name = self.cust_attr_types_by_id[type_id]["name"]
        ignored = (
            "expression", "notificationtype", "dynamic enumerator"
        )
        if cust_attr_type_name in ignored:
            return None

        if cust_attr_type_name == "text":
            return value

        if cust_attr_type_name == "boolean":
            if value == "1":
                return True
            if value == "0":
                return False
            return bool(value)

        if cust_attr_type_name == "date":
            return arrow.get(value)

        cust_attr_config = json.loads(cust_attr_conf["config"])

        if cust_attr_type_name == "number":
            if cust_attr_config["isdecimal"]:
                return float(value)
            return int(value)

        if cust_attr_type_name == "enumerator":
            if not cust_attr_config["multiSelect"]:
                return value
            return value.split(", ")
        return value

    def process_hier_cleanup(self):
        if (
            not self.moved_in_avalon and
            not self.renamed_in_avalon and
            not self.hier_cust_attrs_changes
        ):
            return

        parent_changes = []
        hier_cust_attrs_ids = []
        hier_cust_attrs_keys = []
        all_keys = False
        for mongo_id in self.moved_in_avalon:
            parent_changes.append(mongo_id)
            hier_cust_attrs_ids.append(mongo_id)
            all_keys = True

        for mongo_id in self.renamed_in_avalon:
            if mongo_id not in parent_changes:
                parent_changes.append(mongo_id)

        for key, ftrack_ids in self.hier_cust_attrs_changes.items():
            if key.startswith("avalon_"):
                continue
            for ftrack_id in ftrack_ids:
                avalon_ent = self.avalon_ents_by_ftrack_id[ftrack_id]
                mongo_id = avalon_ent["_id"]
                if mongo_id in hier_cust_attrs_ids:
                    continue
                hier_cust_attrs_ids.append(mongo_id)
                if not all_keys and key not in hier_cust_attrs_keys:
                    hier_cust_attrs_keys.append(key)

        # Parents preparation ***
        mongo_to_ftrack_parents = {}
        missing_ftrack_ents = {}
        for mongo_id in parent_changes:
            avalon_ent = self.avalon_ents_by_id[mongo_id]
            ftrack_id = avalon_ent["data"]["ftrackId"]
            if ftrack_id not in self.ftrack_ents_by_id:
                missing_ftrack_ents[ftrack_id] = mongo_id
                continue
            ftrack_ent = self.ftrack_ents_by_id[ftrack_id]
            mongo_to_ftrack_parents[mongo_id] = len(ftrack_ent["link"])

        if missing_ftrack_ents:
            joine_ids = ", ".join(
                ["\"{}\"".format(id) for id in missing_ftrack_ents.keys()]
            )
            entities = self.process_session.query(
                self.entities_query_by_id.format(
                    self.cur_project["id"], joine_ids
                )
            ).all()
            for entity in entities:
                ftrack_id = entity["id"]
                self.ftrack_ents_by_id[ftrack_id] = entity
                mongo_id = missing_ftrack_ents[ftrack_id]
                mongo_to_ftrack_parents[mongo_id] = len(entity["link"])

        stored_parents_by_mongo = {}
        # sort by hierarchy level
        mongo_to_ftrack_parents = [k for k, v in sorted(
            mongo_to_ftrack_parents.items(),
            key=(lambda item: item[1])
        )]
        self.log.debug(
            "Updating parents and hieararchy because of name/parenting changes"
        )
        for mongo_id in mongo_to_ftrack_parents:
            avalon_ent = self.avalon_ents_by_id[mongo_id]
            vis_par = avalon_ent["data"]["visualParent"]
            if vis_par in stored_parents_by_mongo:
                parents = [par for par in stored_parents_by_mongo[vis_par]]
                if vis_par is not None:
                    parent_ent = self.avalon_ents_by_id[vis_par]
                    parents.append(parent_ent["name"])
                stored_parents_by_mongo[mongo_id] = parents
                continue

            ftrack_id = avalon_ent["data"]["ftrackId"]
            ftrack_ent = self.ftrack_ents_by_id[ftrack_id]
            ent_path_items = [ent["name"] for ent in ftrack_ent["link"]]
            parents = ent_path_items[1:len(ent_path_items)-1:]
            stored_parents_by_mongo[mongo_id] = parents

        for mongo_id, parents in stored_parents_by_mongo.items():
            avalon_ent = self.avalon_ents_by_id[mongo_id]
            cur_par = avalon_ent["data"]["parents"]
            if cur_par == parents:
                continue

            if "data" not in self.updates[mongo_id]:
                self.updates[mongo_id]["data"] = {}
            self.updates[mongo_id]["data"]["parents"] = parents

        # Skip custom attributes if didn't change
        if not hier_cust_attrs_ids:
            # TODO logging
            self.log.debug(
                "Hierarchical attributes were not changed. Skipping"
            )
            self.update_entities()
            return

        _, hier_attrs = self.avalon_cust_attrs

        # Hierarchical custom attributes preparation ***
        hier_attr_key_by_id = {
            attr["id"]: attr["key"]
            for attr in hier_attrs
        }
        hier_attr_id_by_key = {
            key: attr_id
            for attr_id, key in hier_attr_key_by_id.items()
        }

        if all_keys:
            hier_cust_attrs_keys = [
                key
                for key in hier_attr_id_by_key.keys()
                if not key.startswith("avalon_")
            ]

        mongo_ftrack_mapping = {}
        cust_attrs_ftrack_ids = []
        # ftrack_parenting = collections.defaultdict(list)
        entities_dict = collections.defaultdict(dict)

        children_queue = collections.deque()
        parent_queue = collections.deque()

        for mongo_id in hier_cust_attrs_ids:
            avalon_ent = self.avalon_ents_by_id[mongo_id]
            parent_queue.append(avalon_ent)
            ftrack_id = avalon_ent["data"]["ftrackId"]
            if ftrack_id not in entities_dict:
                entities_dict[ftrack_id] = {
                    "children": [],
                    "parent_id": None,
                    "hier_attrs": {}
                }

            mongo_ftrack_mapping[mongo_id] = ftrack_id
            cust_attrs_ftrack_ids.append(ftrack_id)
            children_ents = self.avalon_ents_by_parent_id.get(mongo_id) or []
            for children_ent in children_ents:
                _ftrack_id = children_ent["data"]["ftrackId"]
                if _ftrack_id in entities_dict:
                    continue

                entities_dict[_ftrack_id] = {
                    "children": [],
                    "parent_id": None,
                    "hier_attrs": {}
                }
                # if _ftrack_id not in ftrack_parenting[ftrack_id]:
                #     ftrack_parenting[ftrack_id].append(_ftrack_id)
                entities_dict[_ftrack_id]["parent_id"] = ftrack_id
                if _ftrack_id not in entities_dict[ftrack_id]["children"]:
                    entities_dict[ftrack_id]["children"].append(_ftrack_id)
                children_queue.append(children_ent)

        while children_queue:
            avalon_ent = children_queue.popleft()
            mongo_id = avalon_ent["_id"]
            ftrack_id = avalon_ent["data"]["ftrackId"]
            if ftrack_id in cust_attrs_ftrack_ids:
                continue

            mongo_ftrack_mapping[mongo_id] = ftrack_id
            cust_attrs_ftrack_ids.append(ftrack_id)

            children_ents = self.avalon_ents_by_parent_id.get(mongo_id) or []
            for children_ent in children_ents:
                _ftrack_id = children_ent["data"]["ftrackId"]
                if _ftrack_id in entities_dict:
                    continue

                entities_dict[_ftrack_id] = {
                    "children": [],
                    "parent_id": None,
                    "hier_attrs": {}
                }
                entities_dict[_ftrack_id]["parent_id"] = ftrack_id
                if _ftrack_id not in entities_dict[ftrack_id]["children"]:
                    entities_dict[ftrack_id]["children"].append(_ftrack_id)
                children_queue.append(children_ent)

        while parent_queue:
            avalon_ent = parent_queue.popleft()
            if avalon_ent["type"].lower() == "project":
                continue

            ftrack_id = avalon_ent["data"]["ftrackId"]

            vis_par = avalon_ent["data"]["visualParent"]
            if vis_par is None:
                vis_par = avalon_ent["parent"]

            parent_ent = self.avalon_ents_by_id[vis_par]
            parent_ftrack_id = parent_ent["data"].get("ftrackId")
            if parent_ftrack_id is None:
                self.handle_missing_ftrack_id(parent_ent)
                parent_ftrack_id = parent_ent["data"].get("ftrackId")
                if parent_ftrack_id is None:
                    continue

            if parent_ftrack_id not in entities_dict:
                entities_dict[parent_ftrack_id] = {
                    "children": [],
                    "parent_id": None,
                    "hier_attrs": {}
                }

            if ftrack_id not in entities_dict[parent_ftrack_id]["children"]:
                entities_dict[parent_ftrack_id]["children"].append(ftrack_id)

            entities_dict[ftrack_id]["parent_id"] = parent_ftrack_id

            if parent_ftrack_id in cust_attrs_ftrack_ids:
                continue
            mongo_ftrack_mapping[vis_par] = parent_ftrack_id
            cust_attrs_ftrack_ids.append(parent_ftrack_id)
            # if ftrack_id not in ftrack_parenting[parent_ftrack_id]:
            #     ftrack_parenting[parent_ftrack_id].append(ftrack_id)

            parent_queue.append(parent_ent)

        # Prepare values to query
        configuration_ids = set()
        for key in hier_cust_attrs_keys:
            configuration_ids.add(hier_attr_id_by_key[key])

        values = query_custom_attributes(
            self.process_session,
            configuration_ids,
            cust_attrs_ftrack_ids,
            True
        )

        ftrack_project_id = self.cur_project["id"]

        attr_types_by_id = self.cust_attr_types_by_id
        convert_types_by_id = {}
        for attr in hier_attrs:
            key = attr["key"]
            if key not in hier_cust_attrs_keys:
                continue

            type_id = attr["type_id"]
            attr_id = attr["id"]
            cust_attr_type_name = attr_types_by_id[type_id]["name"]
            convert_type = avalon_sync.get_python_type_for_custom_attribute(
                attr, cust_attr_type_name
            )

            convert_types_by_id[attr_id] = convert_type
            default_value = attr["default"]
            if key in FPS_KEYS:
                try:
                    default_value = convert_to_fps(default_value)
                except InvalidFpsValue:
                    pass

            entities_dict[ftrack_project_id]["hier_attrs"][key] = (
                attr["default"]
            )

        # PREPARE DATA BEFORE THIS
        invalid_fps_items = []
        avalon_hier = []
        for item in values:
            value = item["value"]
            if value is None:
                continue
            entity_id = item["entity_id"]
            configuration_id = item["configuration_id"]

            convert_type = convert_types_by_id[configuration_id]
            key = hier_attr_key_by_id[configuration_id]

            if convert_type:
                value = convert_type(value)

            if key in FPS_KEYS:
                try:
                    value = convert_to_fps(value)
                except InvalidFpsValue:
                    invalid_fps_items.append((entity_id, value))
                    continue
            entities_dict[entity_id]["hier_attrs"][key] = value

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
        project_values = {}
        for key, value in (
            entities_dict[ftrack_project_id]["hier_attrs"].items()
        ):
            if value is not None:
                project_values[key] = value

        for key in avalon_hier:
            value = entities_dict[ftrack_project_id]["avalon_attrs"][key]
            if value is not None:
                project_values[key] = value

        hier_down_queue = collections.deque()
        hier_down_queue.append(
            (project_values, ftrack_project_id)
        )

        while hier_down_queue:
            hier_values, parent_id = hier_down_queue.popleft()
            for child_id in entities_dict[parent_id]["children"]:
                _hier_values = hier_values.copy()
                for name in hier_cust_attrs_keys:
                    value = entities_dict[child_id]["hier_attrs"].get(name)
                    if value is not None:
                        _hier_values[name] = value

                entities_dict[child_id]["hier_attrs"].update(_hier_values)
                hier_down_queue.append((_hier_values, child_id))

        ftrack_mongo_mapping = {}
        for mongo_id, ftrack_id in mongo_ftrack_mapping.items():
            ftrack_mongo_mapping[ftrack_id] = mongo_id

        for ftrack_id, data in entities_dict.items():
            mongo_id = ftrack_mongo_mapping[ftrack_id]
            avalon_ent = self.avalon_ents_by_id[mongo_id]
            ent_path = self.get_ent_path(ftrack_id)
            # TODO logging
            self.log.debug(
                "Updating hierarchical attributes <{}>".format(ent_path)
            )
            for key, value in data["hier_attrs"].items():
                if (
                    key in avalon_ent["data"] and
                    avalon_ent["data"][key] == value
                ):
                    continue

                self.log.debug("- {}: {}".format(key, value))
                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}

                self.updates[mongo_id]["data"][key] = value

        self.update_entities()

    def process_task_updates(self):
        """
            Pull task information for selected ftrack ids to replace stored
            existing in Avalon.
            Solves problem of changing type (even Status in the future) of
            task without storing ftrack id for task in the DB. (Which doesn't
            bring much advantage currently and it could be troublesome for
            all hosts or plugins (for example Nuke) to collect and store.
        Returns:
            None
        """
        self.log.debug(
            "Processing task changes for parents: {}".format(
                self.modified_tasks_ftrackids
            )
        )
        if not self.modified_tasks_ftrackids:
            return

        joined_ids = ", ".join([
            "\"{}\"".format(ftrack_id)
            for ftrack_id in self.modified_tasks_ftrackids
        ])
        task_entities = self.process_session.query(
            self.task_entities_query_by_parent_id.format(
                self.cur_project["id"], joined_ids
            )
        ).all()

        ftrack_mongo_mapping_found = {}
        not_found_ids = []
        # Make sure all parents have updated tasks, as they may not have any
        tasks_per_ftrack_id = {
            ftrack_id: {}
            for ftrack_id in self.modified_tasks_ftrackids
        }

        # Query all task types at once
        task_types = self.process_session.query(self.task_types_query).all()
        task_types_by_id = {
            task_type["id"]: task_type
            for task_type in task_types
        }

        # prepare all tasks per parentId, eg. Avalon asset record
        for task_entity in task_entities:
            task_type = task_types_by_id[task_entity["type_id"]]
            ftrack_id = task_entity["parent_id"]
            if ftrack_id not in tasks_per_ftrack_id:
                tasks_per_ftrack_id[ftrack_id] = {}

            passed_regex = avalon_sync.check_regex(
                task_entity["name"], "task",
                schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                self.regex_failed.append(task_entity["id"])
                continue

            tasks_per_ftrack_id[ftrack_id][task_entity["name"]] = {
                "type": task_type["name"]
            }

        # find avalon entity by parentId
        # should be there as create was run first
        for ftrack_id in tasks_per_ftrack_id.keys():
            avalon_entity = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_entity:
                not_found_ids.append(ftrack_id)
                continue
            ftrack_mongo_mapping_found[ftrack_id] = avalon_entity["_id"]

        self._update_avalon_tasks(
            ftrack_mongo_mapping_found,
            tasks_per_ftrack_id
        )

    def update_entities(self):
        """
            Update Avalon entities by mongo bulk changes.
            Expects self.updates which are transfered to $set part of update
            command.
            Resets self.updates afterwards.
        """
        mongo_changes_bulk = []
        for mongo_id, changes in self.updates.items():
            avalon_ent = self.avalon_ents_by_id[mongo_id]
            is_project = avalon_ent["type"] == "project"
            change_data = avalon_sync.from_dict_to_set(changes, is_project)
            mongo_changes_bulk.append(
                UpdateOne({"_id": mongo_id}, change_data)
            )

        if not mongo_changes_bulk:
            return

        self.dbcon.bulk_write(mongo_changes_bulk)
        self.updates = collections.defaultdict(dict)

    @property
    def duplicated_report(self):
        if not self.duplicated:
            return []

        ft_project = self.cur_project
        duplicated_names = []
        for ftrack_id in self.duplicated:
            ftrack_ent = self.ftrack_ents_by_id.get(ftrack_id)
            if not ftrack_ent:
                ftrack_ent = self.process_session.query(
                    self.entities_query_by_id.format(
                        ft_project["id"], ftrack_id
                    )
                ).one()
                self.ftrack_ents_by_id[ftrack_id] = ftrack_ent
            name = ftrack_ent["name"]
            if name not in duplicated_names:
                duplicated_names.append(name)

        joined_names = ", ".join(
            ["\"{}\"".format(name) for name in duplicated_names]
        )
        ft_ents = self.process_session.query(
            self.entities_name_query_by_name.format(
                ft_project["id"], joined_names
            )
        ).all()

        ft_ents_by_name = collections.defaultdict(list)
        for ft_ent in ft_ents:
            name = ft_ent["name"]
            ft_ents_by_name[name].append(ft_ent)

        if not ft_ents_by_name:
            return []

        subtitle = "Duplicated entity names:"
        items = []
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

        for name, ents in ft_ents_by_name.items():
            items.append({
                "type": "label",
                "value": "## {}".format(name)
            })
            paths = []
            for ent in ents:
                ftrack_id = ent["id"]
                ent_path = "/".join([_ent["name"] for _ent in ent["link"]])
                avalon_ent = self.avalon_ents_by_id.get(ftrack_id)

                if avalon_ent:
                    additional = " (synchronized)"
                    if avalon_ent["name"] != name:
                        additional = " (synchronized as {})".format(
                            avalon_ent["name"]
                        )
                    ent_path += additional
                paths.append(ent_path)

            items.append({
                "type": "label",
                "value": '<p>{}</p>'.format("<br>".join(paths))
            })

        return items

    @property
    def regex_report(self):
        if not self.regex_failed:
            return []

        subtitle = "Entity names contain prohibited symbols:"
        items = []
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

        ft_project = self.cur_project
        for ftrack_id in self.regex_failed:
            ftrack_ent = self.ftrack_ents_by_id.get(ftrack_id)
            if not ftrack_ent:
                ftrack_ent = self.process_session.query(
                    self.entities_query_by_id.format(
                        ft_project["id"], ftrack_id
                    )
                ).one()
                self.ftrack_ents_by_id[ftrack_id] = ftrack_ent

            name = ftrack_ent["name"]
            ent_path_items = [_ent["name"] for _ent in ftrack_ent["link"][:-1]]
            ent_path_items.append("<strong>{}</strong>".format(name))
            ent_path = "/".join(ent_path_items)
            items.append({
                "type": "label",
                "value": "<p>{} - {}</p>".format(name, ent_path)
            })

        return items

    def report(self):
        msg_len = len(self.duplicated) + len(self.regex_failed)
        for msgs in self.report_items.values():
            msg_len += len(msgs)

        if msg_len == 0:
            return

        items = []
        project_name = self.cur_project["full_name"]
        title = "Synchronization report ({}):".format(project_name)

        keys = ["error", "warning", "info"]
        for key in keys:
            subitems = []
            if key == "warning":
                subitems.extend(self.duplicated_report)
                subitems.extend(self.regex_report)

            for _msg, _items in self.report_items[key].items():
                if not _items:
                    continue

                msg_items = _msg.split("||")
                msg = msg_items[0]
                subitems.append({
                    "type": "label",
                    "value": "# {}".format(msg)
                })

                if len(msg_items) > 1:
                    for note in msg_items[1:]:
                        subitems.append({
                            "type": "label",
                            "value": "<p><i>NOTE: {}</i></p>".format(note)
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

        self.show_interface(
            items=items,
            title=title,
            event=self._cur_event
        )
        return True

    def _update_avalon_tasks(
        self, ftrack_mongo_mapping_found, tasks_per_ftrack_id
    ):
        """
            Prepare new "tasks" content for existing records in Avalon.
        Args:
            ftrack_mongo_mapping_found (dictionary): ftrack parentId to
                Avalon _id mapping
            tasks_per_ftrack_id (dictionary): task dictionaries per ftrack
                parentId

        Returns:
            None
        """
        mongo_changes_bulk = []
        for ftrack_id, mongo_id in ftrack_mongo_mapping_found.items():
            filter = {"_id": mongo_id}
            change_data = {"$set": {}}
            change_data["$set"]["data.tasks"] = tasks_per_ftrack_id[ftrack_id]
            mongo_changes_bulk.append(UpdateOne(filter, change_data))

        if mongo_changes_bulk:
            self.dbcon.bulk_write(mongo_changes_bulk)

    def _mongo_id_configuration(
        self,
        ent_info,
        cust_attrs,
        hier_attrs,
        temp_dict
    ):
        # Use hierarchical mongo id attribute if possible.
        if "_hierarchical" not in temp_dict:
            hier_mongo_id_configuration_id = None
            for attr in hier_attrs:
                if attr["key"] == CUST_ATTR_ID_KEY:
                    hier_mongo_id_configuration_id = attr["id"]
                    break
            temp_dict["_hierarchical"] = hier_mongo_id_configuration_id

        hier_mongo_id_configuration_id = temp_dict.get("_hierarchical")
        if hier_mongo_id_configuration_id is not None:
            return hier_mongo_id_configuration_id

        # Legacy part for cases that MongoID attribute is per entity type.
        entity_type = ent_info["entity_type"]
        mongo_id_configuration_id = temp_dict.get(entity_type)
        if mongo_id_configuration_id is not None:
            return mongo_id_configuration_id

        for attr in cust_attrs:
            key = attr["key"]
            if key != CUST_ATTR_ID_KEY:
                continue

            if attr["entity_type"] != ent_info["entityType"]:
                continue

            if (
                ent_info["entityType"] == "task" and
                attr["object_type_id"] != ent_info["objectTypeId"]
            ):
                continue

            mongo_id_configuration_id = attr["id"]
            break

        temp_dict[entity_type] = mongo_id_configuration_id

        return mongo_id_configuration_id


def register(session):
    '''Register plugin. Called when used as an plugin.'''
    SyncToAvalonEvent(session).register()
