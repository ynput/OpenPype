import os
import collections
import re
import queue
import time
import toml
import atexit
import traceback

from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo import UpdateOne

from avalon import schema

from pype.ftrack.lib import avalon_sync
from pype.ftrack.lib.avalon_sync import (
    cust_attr_id_key, cust_attr_auto_sync, entity_schemas
)
from pype.vendor import ftrack_api
from pype.ftrack import BaseEvent

from pype.ftrack.lib.io_nonsingleton import DbConnector


class SyncToAvalonEvent(BaseEvent):

    dbcon = DbConnector()

    ignore_entTypes = [
        "socialfeed", "socialnotification", "note",
        "assetversion", "job", "user", "reviewsessionobject", "timer",
        "timelog", "auth_userrole"
    ]
    ignore_ent_types = ["Milestone"]
    ignore_keys = ["statusid"]

    project_query = (
        "select full_name, name, custom_attributes"
        ", project_schema._task_type_schema.types.name"
        " from Project where id is \"{}\""
    )

    entities_query_by_id = (
        "select id, name, parent_id, link, custom_attributes from TypedContext"
        " where project_id is \"{}\" and entity_id in ({})"
    )
    entities_name_query_by_name = (
        "select id, name from TypedContext"
        " where project_id is \"{}\" and name in ({})"
    )
    created_entities = []

    def __init__(self, session, plugins_presets={}):
        '''Expects a ftrack_api.Session instance'''
        self.set_process_session(session)
        super().__init__(session, plugins_presets)

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
            self._avalon_cust_attrs = avalon_sync.get_avalon_attr(
                self.process_session
            )
        return self._avalon_cust_attrs

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
            # TODO Do we need this split?
            # - project should not be in avalon_ent_by_name
            proj, ents = self.avalon_entities
            for ent in ents:
                self._avalon_ents_by_name[ent["name"]] = ent
        return self._avalon_ents_by_name

    @property
    def avalon_ents_by_id(self):
        if self._avalon_ents_by_id is None:
            self._avalon_ents_by_id = {}
            proj, ents = self.avalon_entities
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
            ftrack_id = proj["data"]["ftrackId"]
            self._avalon_ents_by_ftrack_id[ftrack_id] = proj
            for ent in ents:
                ftrack_id = ent["data"]["ftrackId"]
                self._avalon_ents_by_ftrack_id[ftrack_id] = ent
        return self._avalon_ents_by_ftrack_id

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
    def changeability_by_mongo_id(self):
        """Return info about changeability of entity and it's parents."""
        if self._changeability_by_mongo_id is None:
            self._changeability_by_mongo_id = collections.defaultdict(
                lambda: True
            )
            self._changeability_by_mongo_id[self.avalon_project_id] = False
            self._bubble_changeability(
                list(self.avalon_subsets_by_parents.keys())
            )

        return self._changeability_by_mongo_id

    @property
    def avalon_custom_attributes(self):
        """Return info about changeability of entity and it's parents."""
        if self._avalon_custom_attributes is None:
            self._avalon_custom_attributes = avalon_sync.get_avalon_attr(
                self.process_session
            )
        return self._avalon_custom_attributes

    def remove_cached_by_key(self, key, values):
        if self._avalon_ents is None:
            return

        if not isinstance(values):
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
            # TODO add more keys (if possible)
            # - this way not allow parent_id
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

            self._avalon_ents.remove(entity)
            if self._avalon_ents_by_ftrack_id is not None:
                self._avalon_ents_by_ftrack_id.pop(ftrack_id, None)

            if self._avalon_ents_by_parent_id is not None:
                self._avalon_ents_by_parent_id[parent_id].remove(entity)

            if self._avalon_ents_by_id is not None:
                self._avalon_ents_by_id.pop(mongo_id, None)

            if self._avalon_ents_by_name is not None:
                self._avalon_ents_by_name.pop(name, None)

            if mongo_id in self.task_changes_by_avalon_id:
                self.task_changes_by_avalon_id.pop(mongo_id)

    def _bubble_changeability(self, unchangeable_ids):
        unchangeable_queue = queue.Queue()
        for entity_id in unchangeable_ids:
            unchangeable_queue.put((entity_id, False))

        processed_parents_ids = []
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
                    _subset_ids = [
                        str(sub["_id"]) for sub in
                        self.avalon_subsets_by_parents[entity_id]
                    ]
                    joined_subset_ids = "| ".join(_subset_ids)
                    self.log.warning((
                        "Parent <{}> for subsets <{}> does not exist"
                    ).format(str(entity_id), joined_subset_ids))
                else:
                    # TODO logging - What is happening here?
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
            unchangeable_queue.put((parent_id, child_is_archived))

    def reset_variables(self):
        """Reset variables so each event callback has clear env."""
        self._cur_project = None

        self._avalon_cust_attrs = None

        self._avalon_ents = None
        self._avalon_ents_by_id = None
        self._avalon_ents_by_parent_id = None
        self._avalon_ents_by_ftrack_id = None
        self._avalon_ents_by_name = None
        self._avalon_subsets_by_parents = None
        self._changeability_by_mongo_id = None

        self.task_changes_by_avalon_id = {}

        self._avalon_custom_attributes = None
        self._ent_types_by_name = None

        self.ftrack_ents_by_id = {}
        self.obj_id_ent_type_map = {}

        self.ftrack_added = {}
        self.ftrack_moved = {}
        self.ftrack_renamed = {}
        self.ftrack_updated = {}
        self.ftrack_removed = {}
        self.hierarchy_update = []

        self.renamed_in_avalon = []

        self.duplicated = []
        self.regex_fail = []

        self.regex_schemas = {}
        self.updates = collections.defaultdict(dict)

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
                    ent_info["changes"] = changes.pop("name")
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
        entity = self.ftrack_ents_by_id.get(ftrack_id)
        if not entity:
            entity = self.process_session.query(
                self.entities_query_by_id.format(
                    self.cur_project["id"], ftrack_id
                )
            ).one()
            self.ftrack_ents_by_id[ftrack_id] = entity
        return "/".join([ent["name"] for ent in entity["link"]])

    def launch(self, session, event):
        return True
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
            if entityType in self.ignore_entTypes:
                continue

            entity_type = ent_info.get("entity_type")
            if not entity_type or entity_type in self.ignore_ent_types:
                continue

            action = ent_info["action"]
            ftrack_id = ent_info["entityId"]
            if action == "move":
                ent_keys = ent_info["keys"]
                # Seprate update info from move action
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

            found_actions.add(action)
            entities_by_action[action][ftrack_id] = ent_info

        found_actions = list(found_actions)
        if not found_actions:
            return True

        # Check if auto sync was turned on/off
        updated = entities_by_action["update"]
        for ftrack_id, ent_info in updated.items():
            # filter project
            if ent_info["entityType"] != "show":
                continue

            changes = ent_info["changes"]
            if cust_attr_auto_sync not in changes:
                continue

            auto_sync = changes[cust_attr_auto_sync]["new"]
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
            len(found_actions) == 1 and
            found_actions[0] == "update" and
            not updated
        ):
            return True

        ft_project = self.cur_project
        # Check if auto-sync custom attribute exists
        if cust_attr_auto_sync not in ft_project["custom_attributes"]:
            # TODO should we sent message to someone?
            # TODO report
            self.log.error((
                "Custom attribute \"{}\" is not created or user \"{}\" used"
                " for Event server don't have permissions to access it!"
            ).format(cust_attr_auto_sync, self.session.api_user))
            return True

        # Skip if auto-sync is not set
        auto_sync = ft_project["custom_attributes"][cust_attr_auto_sync]
        if auto_sync != "1":
            return True

        # Get ftrack entities - find all ftrack ids first
        ftrack_ids = []
        for ent_info in updated:
            ftrack_ids.append(ent_info["entityId"])

        for action, ent_infos in entities_by_action.items():
            # skip updated (already prepared) and removed (not exist in ftrack)
            if action in ["update", "remove"]:
                continue

            for ent_info in ent_infos:
                ftrack_id = ent_info["entityId"]
                if ftrack_id not in ftrack_ids:
                    ftrack_ids.append(ftrack_id)

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

            _ent_info = ent_info.copy()
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

        # 1.) Process removed - may affect all other actions
        self.process_removed()
        # 2.) Process renamed - may affect added
        self.process_renamed()
        # 3.) Process added - moved entity may be moved to new entity
        self.process_added()
        # 4.) Process moved
        self.process_moved()
        # 5.) Process updated
        self.process_updated()

        return True

    def process_removed(self):
        if not self.ftrack_removed:
            return
        ent_infos = self.ftrack_removed
        removable_ids = []
        recreate_ents = []
        removed_mapping = {}
        removed_names = []
        for ftrack_id, removed in ent_infos:
            entity_type = removed["entity_type"]
            parent_id = removed["parentId"]
            removed_name = removed["changes"]["name"]["old"]
            if entity_type == "Task":
                avalon_ent = self.avalon_ents_by_ftrack_id.get(parent_id)
                if not avalon_ent:
                    self.log.debug((
                        "Parent entity of task was not found in avalon <{}>"
                    ).format(self.get_ent_path(ftrack_id)))
                    continue

                mongo_id = avalon_ent["_id"]
                if mongo_id not in self.task_changes_by_avalon_id:
                    self.task_changes_by_avalon_id[mongo_id] = (
                        avalon_ent["data"]["tasks"]
                    )

                if removed_name in self.task_changes_by_avalon_id[mongo_id]:
                    self.task_changes_by_avalon_id[mongo_id].remove(
                        removed_name
                    )

                continue

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
            self.dbcon.update_many(
                {"_id": {"$in": removable_ids}, "type": "asset"},
                {"$set": {"type": "archived_asset"}}
            )
            self.remove_cached_by_key("id", removable_ids)

        if recreate_ents:
            # sort removed entities by parents len
            # - length of parents determine hierarchy level
            recreate_ents = sorted(
                recreate_ents.items(),
                key=(lambda line: len(
                    (line[1].get("data", {}).get("parents") or [])
                ))
            )
            # TODO recreate entities
            # remove mapping is for mapping removed and new entities
            removed_mapping["removed_ftrack_id"] = "new_ftrack_id"

        # Check if entities with same name can be synchronized
        if not removed_names:
            return

        joined_passed_names = ", ".join(
            ["\"{}\"".format(name) for name in removed_names]
        )
        same_name_entities = self.process_session.query(
            self.entities_name_query_by_name.format(joined_passed_names)
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
                    name, "| ".join([self.get_ent_path(ent) for ent in ents])
                ))
                continue

            entity = ents[0]
            self.log.debug("Checking if can synchronize entity <{}>".format(
                self.get_ent_path(entity)
            ))
            # skip if already synchronized
            ftrack_id = entity["id"]
            if ftrack_id in self.avalon_ents_by_ftrack_id:
                self.log.debug("Entity is already synchronized")
                continue

            parent_id = entity["parent_id"]
            if parent_id not in self.avalon_ents_by_ftrack_id:
                self.log.debug(
                    "Entity's parent entity doesn't seems to be synchronized."
                )
                continue

            synchronizable_ents.append(entity)

        if not synchronizable_ents:
            return

        synchronizable_ents = sorted(
            synchronizable_ents,
            key=(lambda entity: len(entity["link"]))
        )

        for entity in synchronizable_ents:
            parent_avalon_ent = self.avalon_ents_by_ftrack_id[
                entity["parent_id"]
            ]
            self.create_entity_in_avalon(entity, parent_avalon_ent)
            for child in entity["children"]:
                if child.entity_type.lower() == "task":
                    continue
                # TODO create children and children of children and children of children of children

    def create_entity_in_avalon(self, ftrack_ent, parent_avalon):
        proj, ents = self.avalon_entities

        # Parents, Hierarchy
        ent_path_items = [ent["name"] for ent in ftrack_ent["link"]]
        parents = ent_path_items[1:len(ent_path_items)-1:]
        hierarchy = ""
        if len(parents) > 0:
            hierarchy = os.path.sep.join(parents)

        # Tasks
        tasks = []
        for child in ftrack_ent["children"]:
            if child.entity_type.lower() != "task":
                continue
            tasks.append(child["name"])

        # Visual Parent
        vis_par = None
        if parent_avalon["type"].lower() != "project":
            vis_par = parent_avalon["_id"]

        mongo_id = ObjectId()
        final_entity = {
            "_id": mongo_id,
            "name": ftrack_ent["name"],
            "type": "asset",
            "schema": entity_schemas["asset"],
            "parent": proj["_id"],
            "data": {
                "ftrackId": ftrack_ent["id"],
                "entityType": ftrack_ent.entity_type,
                "parents": parents,
                "hierarchy": hierarchy,
                "tasks": tasks,
                "visualParent": vis_par
            }
        }
        cust_attrs = self.get_cust_attr_values(ftrack_ent)
        for key, val in cust_attrs:
            final_entity["data"][key] = val

        schema.validate(final_entity)
        self.dbcon.insert_one(final_entity)

        # Skip if self._avalon_ents is not set(maybe never happen)
        if self._avalon_ents is None:
            return final_entity

        if self._avalon_ents is not None:
            self._avalon_ents.append(final_entity)

        if self._avalon_ents_by_id is not None:
            self._avalon_ents_by_id[mongo_id] = final_entity

        if self._avalon_ents_by_parent_id is not None:
            self._avalon_ents_by_parent_id[vis_par].append(final_entity)

        if self._avalon_ents_by_ftrack_id is not None:
            self._avalon_ents_by_ftrack_id[ftrack_ent["id"]] = final_entity

        if self._avalon_ents_by_name is not None:
            self._avalon_ents_by_name[ftrack_ent["name"]] = final_entity

        return final_entity

    def get_cust_attr_values(self, entity, keys=None):
        output = {}
        custom_attrs, hier_attrs = self.avalon_custom_attributes
        not_processed_keys = True
        if keys:
            not_processed_keys = [k for k in keys]
        # Notmal custom attributes
        processed_keys = []
        for attr in custom_attrs:
            if not not_processed_keys:
                break
            key = attr["key"]
            if key in processed_keys:
                continue
            if key.startswith("avalon_"):
                continue

            if key not in entity["custom_attributes"]:
                continue

            if keys:
                if key not in keys:
                    continue
                else:
                    not_processed_keys.remove(key)

            output[key] = entity["custom_attributes"][key]
            processed_keys.append(key)

        if not not_processed_keys:
            return output

        # Hierarchical cust attrs
        hier_keys = []
        defaults = {}
        for attr in hier_attrs:
            key = attr["key"]
            if key.startswith("avalon_"):
                continue

            if keys and key not in keys:
                continue
            hier_keys.append(key)
            defaults[key] = attr["default"]

        hier_values = avalon_sync.get_hierarchical_attributes(
            self.processing_session, entity, hier_keys, defaults
        )
        for key, val in hier_values.items():
            output[key] = val

        return output

    def process_renamed(self):
        if not self.ftrack_renamed:
            return

        ent_infos = self.ftrack_renamed
        renamed_tasks = {}
        not_found = {}
        changeable_queue = queue.Queue()
        for ftrack_id, ent_info in ent_infos.items():
            entity_type = ent_info["entity_type"]
            new_name = ent_info["changes"]["name"]["new"]
            old_name = ent_info["changes"]["name"]["old"]
            if entity_type == "Task":
                parent_id = ent_info["parentId"]
                renamed_tasks[parent_id] = {
                    "new": new_name,
                    "old": old_name,
                    "ent_info": ent_info
                }
                continue

            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                not_found[ftrack_id] = ent_info
                continue

            if new_name == avalon_ent["name"]:
                continue

            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                changeable_queue.put((ftrack_id, avalon_ent, new_name))
            else:
                ftrack_ent = self.ftrack_ents_by_id[ftrack_id]
                ftrack_ent["name"] = avalon_ent["name"]
                try:
                    self.process_session.commit()
                except Exception:
                    self.process_session.rollback()
                    # TODO report
                    # TODO logging

        # Process renaming in Avalon DB
        while not changeable_queue.empty():
            ftrack_id, avalon_ent, new_name = changeable_queue.get()
            mongo_id = avalon_ent["_id"]
            old_name = avalon_ent["name"]

            _entity_type = "asset"
            if entity_type == "Project":
                _entity_type = "project"

            passed_regex = avalon_sync.check_regex(
                new_name, _entity_type, schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                # TODO report
                # TODO logging
                # new name does not match regex (letters numbers and _)
                ent_path = self.get_ent_path(ftrack_id)
                # TODO move this to special report method
                self.log.warning(
                    "Entity name contain invalid symbols <{}>".format(ent_path)
                )
                continue

            # if avalon does not have same name then can be changed
            same_name_avalon_ent = self.avalon_ents_by_name.get(new_name)
            if not same_name_avalon_ent:
                old_val = self._avalon_ents_by_name.pop(old_name)
                old_val["name"] = new_name
                self._avalon_ents_by_name[new_name] = old_val
                self.updates[mongo_id] = {"name": new_name}
                self.renamed_in_avalon.append(ftrack_id)
                # TODO report
                # TODO logging
                # TODO go through children to change parents
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
            for item in list(changeable_queue.queue):
                if same_name_ftrack_id == item[0]:
                    same_is_unprocessed = True
                    break

            if same_is_unprocessed:
                changeable_queue.put((ftrack_id, avalon_ent, new_name))
                continue

            # TODO report
            # TODO logging
            # Duplicated entity name
            # TODO move this to special report method
            self.log.warning(
                "Entity name is duplicated in the project <{}>".format(
                    ent_path
                )
            )

        for parent_id, task_change in renamed_tasks.items():
            avalon_ent = self.avalon_ents_by_ftrack_id.get(parent_id)
            ent_info = task_change["ent_info"]
            if not avalon_ent:
                not_found[ent_info["entityId"]] = ent_info
                continue

            mongo_id = avalon_ent["_id"]
            if mongo_id not in self.task_changes_by_avalon_id:
                self.task_changes_by_avalon_id[mongo_id] = (
                    avalon_ent["data"]["tasks"]
                )

            new_name = task_change["new"]
            old_name = task_change["old"]
            passed_regex = avalon_sync.check_regex(
                new_name, "task", schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                ftrack_id = ent_info["enityId"]
                entity = self.ftrack_ents_by_id[ftrack_id]
                entity["name"] = old_name
                try:
                    self.process_session.commit()
                    # TODO report
                    # TODO logging
                except Exception:
                    self.process_session.rollback()
                    # TODO report
                    # TODO logging

                continue

            if old_name in self.task_changes_by_avalon_id[mongo_id]:
                self.task_changes_by_avalon_id[mongo_id].remove(old_name)

            if new_name not in self.task_changes_by_avalon_id[mongo_id]:
                self.task_changes_by_avalon_id[mongo_id].append(new_name)

        # TODO process not_found

    def process_added(self):
        ent_infos = self.ftrack_added
        if not ent_infos:
            return

        # Skip if already exit in avalon db or tasks entities
        # - happen when was created by any sync event/action
        pop_out_ents = []
        new_tasks_by_parent = collections.defaultdict(list)
        _new_ent_infos = {}
        for ftrack_id, ent_info in ent_infos.items():
            if self.avalon_ents_by_ftrack_id.get(ftrack_id):
                pop_out_ents.append(ftrack_id)
                continue

            if ent_info["entity_type"] == "Task":
                parent_id = ent_info["parentId"]
                new_tasks_by_parent[parent_id].append(ent_info)
                pop_out_ents.append(ftrack_id)

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
        not_found_parents = []
        duplicated = []
        regex_failed = []
        for ftrack_id, entity in to_sync_by_id.items():
            if entity.entity_type.lower() == "project":
                raise Exception((
                    "Project can't be created with event handler!"
                    "This is a bug"
                ))
            parent_id = entity["parent_id"]
            parent_avalon = self.avalon_ents_by_ftrack_id.get(parent_id)
            if not parent_avalon:
                parent_avalon = self.process_parent_nonexistence(parent_id)
                if not parent_avalon:
                    not_found_parents.append(ftrack_id)
                    continue

            name = entity["name"]
            passed_regex = avalon_sync.check_regex(
                name, "asset", schema_patterns=self.regex_schemas
            )
            if not passed_regex:
                regex_failed.append(ftrack_id)

            if name in self.avalon_ents_by_name:
                duplicated.append(ftrack_id)

        ids_to_pop = list(set(regex_failed).union(set(duplicated)))

        # TODO go through not found parents
        parent_already_exist = []
        for ftrack_id in not_found_parents:
            if ftrack_id in ids_to_pop:
                continue
            entity = self.ftrack_ents_by_id[ftrack_id]
            parent_id = entity["parent_id"]
            result = self.process_parent_nonexistence(parent_id)
            if not result:
                ids_to_pop.append(ftrack_id)
                continue

            parent_already_exist.append(ftrack_id)

        ignored_entities = {}
        for ftrack_id in ids_to_pop:
            ignored_entities[ftrack_id] = to_sync_by_id.pop(ftrack_id)



        # joined_passed_names = ", ".join(
        #     ["\"{}\"".format(name) for name in all_passed_names]
        # )
        # name_ftrack_ents = self.process_session.query(
        #     self.entities_name_query_by_name.format(
        #         self.cur_project["id"], joined_passed_names
        #     )
        # ).all()
        #
        # ents_by_name = collections.defaultdict(list)
        # for entity in name_ftrack_ents:
        #     ftrack_id = entity["id"]
        #     if ftrack_id not in self.ftrack_ents_by_id:
        #         self.ftrack_ents_by_id[ftrack_id] = entity
        #     ents_by_name[entity["name"]].append(entity)


    def process_moved(self):
        if not self.ftrack_moved:
            return

        found = {}
        not_found = {}
        for ftrack_id, ent_info in self.ftrack_moved.items():
            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                not_found[ftrack_id] = ent_info
                continue

            found[ftrack_id] = {
                "avalon_ent": avalon_ent,
                "ent_info": ent_info,
                "renamed": ftrack_id in self.ftrack_renamed
            }

        # TODO process not_found (not synchronized)

        for ftrack_id, ent_dict in found.items():
            updates = {}
            avalon_ent = ent_dict["avalon_ent"]
            ent_info = ent_dict["ent_info"]
            renamed = ent_dict["renamed"]

            new_parent_id = ent_info["changes"]["parent_id"]["new"]
            old_parent_id = ent_info["changes"]["parent_id"]["old"]

            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                # TODO implement
                par_av_ent = self.avalon_ents_by_ftrack_id.get(new_parent_id)
                # THIS MUST HAPPEND AFTER CREATING NEW ENTITIES !!!!
                updates["data.visualParent"] = par_av_ent["_id"]
                if renamed:
                    pass

    def process_updated(self, ent_infos):
        # Only custom attributes changes should get here
        if not ent_infos:
            return

        # TODO check if entity exist in mongo!!!!
        # Try to create if not (In that case `update` does not make sence)
        ftrack_mongo_mapping = {}
        not_found = {}
        not_found_ids = []
        for ftrack_id, ent_info in ent_infos.items():
            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if avalon_ent:
                ftrack_mongo_mapping[ftrack_id] = avalon_ent["_id"]
                continue
            not_found_ids.append(ftrack_id)

        for ftrack_id in not_found_ids:
            not_found[ftrack_id] = ent_infos.pop(ftrack_id)

        self.process_not_found(not_found)
        if not ent_infos:
            return

        cust_attrs, hier_attrs = self.avalon_cust_attrs
        cust_attrs_by_obj_id = collections.defaultdict(dict)
        for cust_attr in cust_attrs:
            key = cust_attr["key"]
            if key.startswith("avalon_"):
                continue

            ca_ent_type = cust_attr["entity_type"]

            if ca_ent_type == "show":
                cust_attrs_by_obj_id[ca_ent_type][key] = cust_attr
            else:
                obj_id = cust_attr["object_type_id"]
                cust_attrs_by_obj_id[obj_id][key] = cust_attr

        for ftrack_id, ent_info in ent_infos:
            mongo_id = ftrack_mongo_mapping[ftrack_id]
            entType = ent_infos["entityType"]
            if entType == "show":
                ent_cust_attrs = cust_attrs_by_obj_id.get("show")
            else:
                obj_type_id = ent_infos["objectTypeId"]
                ent_cust_attrs = cust_attrs_by_obj_id.get(obj_type_id)

            if not ent_cust_attrs:
                continue

            for key, values in ent_info["changes"].items():
                if key not in ent_cust_attrs:
                    continue

                if "data" not in self.updates[mongo_id]:
                    self.updates[mongo_id]["data"] = {}
                value = values["new"]
                self.updates[mongo_id]["data"][key] = value

    def process_not_found(self, ent_infos):
        raise NotImplemented("process_not_found is not Implemented yet")


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''
    SyncToAvalonEvent(session, plugins_presets).register()


removed_example = {
    'action': 'remove',
    'changes': {
        'bid': {'new': None, 'old': 0.0},
        'context_type': {'new': None, 'old': 'task'},
        'description': {'new': None, 'old': ''},
        'enddate': {'new': None, 'old': None},
        'id': {'new': None, 'old': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6'},
        'isopen': {'new': None, 'old': False},
        'isrequirecomment': {'new': None, 'old': False},
        'name': {'new': None, 'old': 'compositing'},
        'object_typeid': {'new': None, 'old': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c'},
        'parent_id': {'new': None, 'old': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
        'priorityid': {'new': None, 'old': '9661b320-3a0c-11e2-81c1-0800200c9a66'},
        'showid': {'new': None, 'old': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
        'sort': {'new': None, 'old': 0.0},
        'startdate': {'new': None, 'old': None},
        'statusid': {'new': None, 'old': '44dd9fb2-4164-11df-9218-0019bb4983d8'},
        'taskid': {'new': None, 'old': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6'},
        'thumbid': {'new': None, 'old': None},
        'typeid': {'new': None, 'old': '44dd23b6-4164-11df-9218-0019bb4983d8'}
    },
    'entityId': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6',
    'entityType': 'task',
    'entity_type': 'Task',
    'keys': ['id', 'taskid', 'thumbid', 'context_type', 'name', 'parent_id', 'bid', 'description', 'startdate', 'enddate', 'statusid', 'typeid', 'priorityid', 'isopen', 'isrequirecomment', 'object_typeid', 'showid', 'sort'],
    'objectTypeId': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c',
    'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6',
    'parents': [
        {'entityId': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
        {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None},
        {'entityId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'},
        {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
        {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'}
    ]
}

add_example = {
    'action': 'add',
    'changes': {
        'bid': {'new': 0.0, 'old': None},
        'context_type': {'new': 'task', 'old': None},
        'description': {'new': '', 'old': None},
        'enddate': {'new': None, 'old': None},
        'id': {'new': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6', 'old': None},
        'isopen': {'new': False, 'old': None},
        'isrequirecomment': {'new': False, 'old': None},
        'name': {'new': 's001_ep_02_shot_0080', 'old': None},
        'object_typeid': {'new': 'bad911de-3bd6-47b9-8b46-3476e237cb36', 'old': None},
        'parent_id': {'new': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'old': None},
        'priorityid': {'new': '9661b320-3a0c-11e2-81c1-0800200c9a66', 'old': None},
        'showid': {'new': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'old': None},
        'startdate': {'new': None, 'old': None},
        'statusid': {'new': 'a0bbf0b4-15e2-11e1-b21a-0019bb4983d8', 'old': None},
        'taskid': {'new': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6', 'old': None},
        'typeid': {'new': None, 'old': None}
    },
    'entityId': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6',
    'entityType': 'task',
    'entity_type': 'Shot',
    'keys': ['startdate', 'showid', 'typeid', 'enddate', 'name', 'isopen', 'parent_id', 'context_type', 'bid', 'priorityid', 'statusid', 'isrequirecomment', 'object_typeid', 'taskid', 'id', 'description' ],
    'objectTypeId': 'bad911de-3bd6-47b9-8b46-3476e237cb36',
    'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
    'parents': [
        {'entityId': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6' },
        {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
        {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
        {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None}
    ]
}

event_data = {
    '_data': {
        'data': {
            'clientToken': 'dfd96508-06e6-11ea-94d1-3e41ec9bc0d6',
            'entities': [{
                'action': 'update',
                'changes': {'name': {'new': 's001_ep_02_shot_00101', 'old': 's001_ep_02_shot_0010'}},
                'entityId': 'f9388f70-fafb-11e9-9faa-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Shot',
                'keys': ['name'],
                'objectTypeId': 'bad911de-3bd6-47b9-8b46-3476e237cb36',
                'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                'parents': [{
                    'entityId': 'f9388f70-fafb-11e9-9faa-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'
                }, {
                    'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'
                }, {
                    'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'
                }, {
                    'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6',
                    'entityType': 'show',
                    'parentId': None
                }]
            }, {
                'action': 'move',
                'changes': {
                    'parent_id': {
                        'new': 'f911b742-fafb-11e9-9faa-3e41ec9bc0d6',
                        'old': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'
                    }
                },
                'entityId': '69dd9f1c-0638-11ea-97bc-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Shot',
                'keys': ['parent_id'],
                'objectTypeId': 'bad911de-3bd6-47b9-8b46-3476e237cb36',
                'parentId': 'f911b742-fafb-11e9-9faa-3e41ec9bc0d6',
                'parents': [{
                    'entityId': '69dd9f1c-0638-11ea-97bc-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': 'f911b742-fafb-11e9-9faa-3e41ec9bc0d6'
                }, {
                    'entityId': 'f911b742-fafb-11e9-9faa-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': 'f8fd8b82-fafb-11e9-9faa-3e41ec9bc0d6'
                }, {
                    'entityId': 'f8fd8b82-fafb-11e9-9faa-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'
                }, {
                    'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6',
                    'entityType': 'show',
                    'parentId': None
                }]
            }, {
                'action': 'add',
                'changes': {
                    'bid': {'new': 0.0, 'old': None},
                    'context_type': {'new': 'task', 'old': None},
                    'description': {'new': '', 'old': None},
                    'enddate': {'new': None, 'old': None},
                    'id': {'new': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6', 'old': None},
                    'isopen': {'new': False, 'old': None},
                    'isrequirecomment': {'new': False, 'old': None},
                    'name': {'new': 's001_ep_02_shot_0080', 'old': None},
                    'object_typeid': {'new': 'bad911de-3bd6-47b9-8b46-3476e237cb36', 'old': None},
                    'parent_id': {'new': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'old': None},
                    'priorityid': {'new': '9661b320-3a0c-11e2-81c1-0800200c9a66', 'old': None},
                    'showid': {'new': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'old': None},
                    'startdate': {'new': None, 'old': None},
                    'statusid': {'new': 'a0bbf0b4-15e2-11e1-b21a-0019bb4983d8', 'old': None},
                    'taskid': {'new': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6', 'old': None},
                    'typeid': {'new': None, 'old': None}
                },
                'entityId': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Shot',
                'keys': ['startdate', 'showid', 'typeid', 'enddate', 'name', 'isopen', 'parent_id', 'context_type', 'bid', 'priorityid', 'statusid', 'isrequirecomment', 'object_typeid', 'taskid', 'id', 'description' ],
                'objectTypeId': 'bad911de-3bd6-47b9-8b46-3476e237cb36',
                'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                'parents': [
                    {'entityId': '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6' },
                    {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
                    {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
                    {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None}
                ]
            }, {
                'action': 'remove',
                'changes': {
                    'bid': {'new': None, 'old': 0.0},
                    'context_type': {'new': None, 'old': 'task'},
                    'description': {'new': None, 'old': ''},
                    'enddate': {'new': None, 'old': None},
                    'id': {'new': None, 'old': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6'},
                    'isopen': {'new': None, 'old': False},
                    'isrequirecomment': {'new': None, 'old': False},
                    'name': {'new': None, 'old': 'compositing'},
                    'object_typeid': {'new': None, 'old': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c'},
                    'parent_id': {'new': None, 'old': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    'priorityid': {'new': None, 'old': '9661b320-3a0c-11e2-81c1-0800200c9a66'},
                    'showid': {'new': None, 'old': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
                    'sort': {'new': None, 'old': 0.0},
                    'startdate': {'new': None, 'old': None},
                    'statusid': {'new': None, 'old': '44dd9fb2-4164-11df-9218-0019bb4983d8'},
                    'taskid': {'new': None, 'old': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6'},
                    'thumbid': {'new': None, 'old': None},
                    'typeid': {'new': None, 'old': '44dd23b6-4164-11df-9218-0019bb4983d8'}
                },
                'entityId': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Task',
                'keys': ['id', 'taskid', 'thumbid', 'context_type', 'name', 'parent_id', 'bid', 'description', 'startdate', 'enddate', 'statusid', 'typeid', 'priorityid', 'isopen', 'isrequirecomment', 'object_typeid', 'showid', 'sort'],
                'objectTypeId': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c',
                'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6',
                'parents': [
                    {'entityId': 'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None},
                    {'entityId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'},
                    {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
                    {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'}
                ]
            }, {
                'action': 'remove',
                'changes': {
                    'bid': {'new': None, 'old': 0.0},
                    'context_type': {'new': None, 'old': 'task'},
                    'description': {'new': None, 'old': ''},
                    'enddate': {'new': None, 'old': None},
                    'id': {'new': None, 'old': 'dd62a91a-06e6-11ea-a504-3e41ec9bc0d6'},
                    'isopen': {'new': None, 'old': False},
                    'isrequirecomment': {'new': None, 'old': False},
                    'name': {'new': None, 'old': 'modeling'},
                    'object_typeid': {'new': None, 'old': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c'},
                    'parent_id': {'new': None, 'old': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    'priorityid': {'new': None, 'old': '9661b320-3a0c-11e2-81c1-0800200c9a66'},
                    'showid': {'new': None, 'old': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
                    'sort': {'new': None, 'old': 0.0},
                    'startdate': {'new': None, 'old': None},
                    'statusid': {'new': None, 'old': '44dd9fb2-4164-11df-9218-0019bb4983d8'},
                    'taskid': {'new': None, 'old': 'dd62a91a-06e6-11ea-a504-3e41ec9bc0d6'},
                    'thumbid': {'new': None, 'old': None},
                    'typeid': {'new': None, 'old': '44dc53c8-4164-11df-9218-0019bb4983d8'}
                },
                'entityId': 'dd62a91a-06e6-11ea-a504-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Task',
                'keys': ['id', 'taskid', 'thumbid', 'context_type', 'name', 'parent_id', 'bid', 'description', 'startdate', 'enddate', 'statusid', 'typeid', 'priorityid', 'isopen', 'isrequirecomment', 'object_typeid', 'showid', 'sort'],
                'objectTypeId': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c',
                'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6',
                'parents': [
                    {'entityId': 'dd62a91a-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None},
                    {'entityId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'},
                    {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
                    {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'}
                ]
            }, {
                'action': 'remove',
                'changes': {
                    'bid': {'new': None, 'old': 0.0},
                    'context_type': {'new': None, 'old': 'task'},
                    'description': {'new': None, 'old': ''},
                    'enddate': {'new': None, 'old': None},
                    'id': {'new': None, 'old': 'dd6dc9e4-06e6-11ea-a504-3e41ec9bc0d6'},
                    'isopen': {'new': None, 'old': False},
                    'isrequirecomment': {'new': None, 'old': False},
                    'name': {'new': None, 'old': 'texture'},
                    'object_typeid': {'new': None, 'old': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c'},
                    'parent_id': {'new': None, 'old': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    'priorityid': {'new': None, 'old': '9661b320-3a0c-11e2-81c1-0800200c9a66'},
                    'showid': {'new': None, 'old': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
                    'sort': {'new': None, 'old': 0.0},
                    'startdate': {'new': None, 'old': None},
                    'statusid': {'new': None, 'old': '44dd9fb2-4164-11df-9218-0019bb4983d8'},
                    'taskid': {'new': None, 'old': 'dd6dc9e4-06e6-11ea-a504-3e41ec9bc0d6'},
                    'thumbid': {'new': None, 'old': None},
                    'typeid': {'new': None, 'old': 'c09dfaa8-ac6d-11e7-bd00-0a580aa00e67'}
                },
                'entityId': 'dd6dc9e4-06e6-11ea-a504-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Task',
                'keys': ['id', 'taskid', 'thumbid', 'context_type', 'name', 'parent_id', 'bid', 'description', 'startdate', 'enddate', 'statusid', 'typeid', 'priorityid', 'isopen', 'isrequirecomment', 'object_typeid', 'showid', 'sort'],
                'objectTypeId': '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c',
                'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6',
                'parents': [
                    {'entityId': 'dd6dc9e4-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None},
                    {'entityId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'},
                    {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
                    {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'}
                ]
            }, {
                'action': 'remove',
                'changes': {
                    'bid': {'new': None, 'old': 0.0},
                    'context_type': {'new': None, 'old': 'task'},
                    'description': {'new': None, 'old': ''},
                    'enddate': {'new': None, 'old': None},
                    'id': {'new': None, 'old': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    'isopen': {'new': None, 'old': False},
                    'isrequirecomment': {'new': None, 'old': False},
                    'name': {'new': None, 'old': 's001_ep_02_shot_0070'},
                    'object_typeid': {'new': None, 'old': 'bad911de-3bd6-47b9-8b46-3476e237cb36'},
                    'parent_id': {'new': None, 'old': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'},
                    'priorityid': {'new': None, 'old': '9661b320-3a0c-11e2-81c1-0800200c9a66'},
                    'showid': {'new': None, 'old': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
                    'sort': {'new': None, 'old': 0.0},
                    'startdate': {'new': None, 'old': None},
                    'statusid': {'new': None, 'old': 'a0bbf0b4-15e2-11e1-b21a-0019bb4983d8'},
                    'taskid': {'new': None, 'old': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6'},
                    'thumbid': {'new': None, 'old': None},
                    'typeid': {'new': None, 'old': None}
                },
                'entityId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Shot',
                'keys': ['id', 'taskid', 'thumbid', 'context_type', 'name', 'parent_id', 'bid', 'description', 'startdate', 'enddate', 'statusid', 'typeid', 'priorityid', 'isopen', 'isrequirecomment', 'object_typeid', 'showid', 'sort'],
                'objectTypeId': 'bad911de-3bd6-47b9-8b46-3476e237cb36',
                'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                'parents': [
                    {'entityId': 'dd562c80-06e6-11ea-a504-3e41ec9bc0d6', 'entityType': 'task', 'parentId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6'},
                    {'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'},
                    {'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6', 'entityType': 'task', 'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'},
                    {'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6', 'entityType': 'show', 'parentId': None }
                ]
            }],
            'parents': [
                'dd62a91a-06e6-11ea-a504-3e41ec9bc0d6',
                'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                '69dd9f1c-0638-11ea-97bc-3e41ec9bc0d6',
                'f911b742-fafb-11e9-9faa-3e41ec9bc0d6',
                'f8fd8b82-fafb-11e9-9faa-3e41ec9bc0d6',
                '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6',
                'dd6dc9e4-06e6-11ea-a504-3e41ec9bc0d6',
                'dd562c80-06e6-11ea-a504-3e41ec9bc0d6',
                '872e0a9c-06e8-11ea-b67a-3e41ec9bc0d6',
                '83f56510-0638-11ea-9d25-3e41ec9bc0d6',
                'dd784a4a-06e6-11ea-a504-3e41ec9bc0d6',
                'f9388f70-fafb-11e9-9faa-3e41ec9bc0d6'
            ],
            'pushToken': 'e0bf693606e611ea8f823e41ec9bc0d6',
            'user': {
                'name': 'Kuba Trllo',
                'userid': '2a8ae090-cbd3-11e8-a87a-0a580aa00121'
            }
        },
        'id': '978b06c4351a4dca80f3fefb75f0ac62',
        'in_reply_to_event': None,
        'sent': None,
        'source': {
            'applicationId': 'ftrack.client.web',
            'id': 'dfd96508-06e6-11ea-94d1-3e41ec9bc0d6',
            'user': {
                'id': '2a8ae090-cbd3-11e8-a87a-0a580aa00121',
                'username': 'jakub.trllo'
            }
        },
        'target': '',
        'topic': 'ftrack.update'
    },
    '_stopped': False
}


custom_attr_event = {
    '_data': {
        'data': {
            'clientToken': 'dfd96508-06e6-11ea-94d1-3e41ec9bc0d6',
            'entities': [{
                'action': 'update',
                'changes': {
                    'frameEnd': {'new': '1010', 'old': ''}
                },
                'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                'entityType': 'task',
                'entity_type': 'Episode',
                'keys': ['frameEnd'],
                'objectTypeId': '22139355-61da-4c8f-9db4-3abc870166bc',
                'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6',
                'parents': [{
                    'entityId': 'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6'
                }, {
                    'entityId': '83f56510-0638-11ea-9d25-3e41ec9bc0d6',
                    'entityType': 'task',
                    'parentId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'
                }, {
                    'entityId': '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6',
                    'entityType': 'show',
                    'parentId': None
                }]
            }],
            'parents': [
                'f935a8b4-fafb-11e9-9faa-3e41ec9bc0d6',
                '83f56510-0638-11ea-9d25-3e41ec9bc0d6',
                '24b76ed8-fafb-11e9-9a47-3e41ec9bc0d6'
            ],
            'pushToken': 'e0bfec8a-06e6-11ea-8f82-3e41ec9bc0d6',
            'user': {
                'name': 'Kuba Trllo',
                'userid': '2a8ae090-cbd3-11e8-a87a-0a580aa00121'
            }
        },
        'id': 'c21ef98e3f634c20ae18509052662345',
        'in_reply_to_event': None,
        'sent': None,
        'source': {
            'applicationId': 'ftrack.client.web',
            'id': 'dfd96508-06e6-11ea-94d1-3e41ec9bc0d6',
            'user': {
                'id': '2a8ae090-cbd3-11e8-a87a-0a580aa00121',
                'username': 'jakub.trllo'
            }
        },
        'target': '',
        'topic': 'ftrack.update'
    },
    '_stopped': False
}
