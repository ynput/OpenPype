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

from pype.ftrack.lib import avalon_sync
from pype.ftrack.lib.avalon_sync import cust_attr_id_key, cust_attr_auto_sync
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
        "select id, name, parent_id, link, custom_attributes"
        " from TypedContext where project_id is \"{}\" and "
        "entity_id in ({})"
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
            proj, ents = self.avalon_entities
            self._avalon_ents_by_name[proj["name"]] = proj
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
            self.dbcon.Session["AVALON_PROJECT"] = self.cur_project["full_name"]
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
        self._cur_event = None

        self._avalon_cust_attrs = None

        self._avalon_ents = None
        self._avalon_ents_by_id = None
        self._avalon_ents_by_parent_id = None
        self._avalon_ents_by_ftrack_id = None
        self._avalon_ents_by_name = None
        self._avalon_subsets_by_parents = None
        self._changeability_by_mongo_id = None

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

    def filter_updates(self, updates):
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
            if cust_attr_auto_sync in changes:
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
        updated = self.filter_updates(updated)

        # skip most of events where nothing has changed for avalon
        if (
            len(found_actions) == 1 and
            found_actions[0] == "update" and
            not updates
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

        # Filter updates where name is changing
        name_updates = {}
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
            name_updates[ftrack_id] = _ent_info

        # 1.) Process removed (removed from ftrack database)
        self.process_removed(entities_by_action["remove"])
        self.process_hiearchy_changes(
            entities_by_action["move"], name_updates
        )
        # 2.) Process added
        self.process_added(entities_by_action["add"])
        # 3.) Process moved (changed parent_id)
        self.process_moved(entities_by_action["move"])
        # 4.) Process updated
        self.process_updated(updated)

        return True

    def process_removed(self, ent_infos):
        remove_data = {
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
        if not ent_infos:
            return
        removable_ids = []
        recreate_ents = []
        removed_mapping = {}
        for ftrack_id, removed in ent_infos:
            entity_type = removed["entity_type"]
            parent_id = removed["parentId"]
            removed_name = removed["changes"]["name"]
            if entity_type == "Task":
                avalon_ent = self.avalon_ents_by_ftrack_id.get(parent_id)
                if not avalon_ent:
                    # TODO Find avalon_ent
                    pass

                mongo_id = avalon_ent["_id"]
                tasks = avalon_ent["data"]["tasks"]
                if removed_name not in tasks:
                    continue

                continue

            avalon_ent = self.avalon_ents_by_ftrack_id.get(ftrack_id)
            if not avalon_ent:
                continue
            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                removable_ids.append(mongo_id)
            else:
                recreate_ents.append(avalon_ent)

        if removable_ids:
            self.dbcon.update_many(
                {"_id": {"$in": removable_ids}, "type": "asset"},
                {"$set": {"type": "archived_asset"}}
            )

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

    def process_hiearchy_changes(self, moved, name_changes):
        if not moved and not name_changes:
            return

        self.process_moved(moved)


    def process_moved(self, ent_infos):
        if not ent_infos:
            return

        found = {}
        not_found = {}
        for ent_info in ent_infos:
            ftrack_id = ent_info["entityId"]
            avalon_ent = self.avalon_ents_by_ftrack_id.get("ftrack_id")
            if avalon_ent:
                found[ftrack_id] = {
                    "avalon_ent": avalon_ent,
                    "ent_info": ent_info
                }
                continue

            not_found[ftrack_id] = ent_info

        if not_found:
            joined_ids = ", ".join([
                "\"{}\"".format(id) for id in not_found.keys()
            ])
            ftrack_entities = self.process_session.query(
                self.entities_query_by_id.format(
                    self.cur_project["id"], joined_ids
                )
            ).all()
            for entity in ftrack_entities:
                # TODO find avalon entity
                pass

        updates = {}
        for ftrack_id, ent_dict in found.items():
            avalon_ent = ent_dict["avalon_ent"]
            ent_info = ent_dict["ent_info"]
            new_parent_id = ent_info["changes"]["parent_id"]["new"]
            old_parent_id = ent_info["changes"]["parent_id"]["old"]

            mongo_id = avalon_ent["_id"]
            if self.changeability_by_mongo_id[mongo_id]:
                # TODO implement
                updates[mongo_id] = {"data.visualParent": "asdasd"}

    def process_added(self, ent_infos):
        if not ent_infos:
            return

        # Skip if already exit in avalon db
        # - happen when was created by any sync event/action
        already_exist = []
        for ftrack_id, ent_info in ent_infos.items():
            if self.avalon_ents_by_ftrack_id.get(ftrack_id):
                already_exist.append(ftrack_id)

        for ftrack_id in already_exist:
            ent_infos.pop(ftrack_id)

        add_data = {
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
        # sort by parents length (same as by hierarchy level)
        _ent_infos = sorted(
            ent_infos.values(),
            key=(lambda ent_info: len(ent_info.get("parents", [])))
        )
        ent_infos = {}
        for ent_info in _ent_infos:
            ftrack_id = ent_info["entityId"]
            ent_infos[ftrack_id] = ent_info

        duplicated = []
        _regex_success = {}
        _schema_patterns = {}
        failed_ids = []
        all_new_by_name = collections.defaultdict(list)
        tasks_by_parent_id = collections.defaultdict(list)
        for ent_info in ent_infos:
            name = ent_info["changes"]["name"]["new"]
            if name in all_new_names:
                duplicated.append(name)
            all_new_by_name[name].append(ent_info)
            entity_type = ent_info["entity_type"]

            passed_regex = _regex_success.get(name)
            if passed_regex is None:
                _entity_type = "asset"
                if entity_type == "Project":
                    _entity_type = "project"
                elif entity_type == "Task":
                    _entity_type = "task"

                passed_regex = avalon_sync.check_regex(
                    name, _entity_type, schema_patterns=_schema_patterns
                )
                _regex_success[name] = passed_regex

            if entity_type == "Task":
                if passed_regex:
                    tasks_by_parent_id[ent_info["parentId"]].append(name)
                continue

            if not passed_regex:
                failed_ids.append(ent_info["entityId"])

        ignore_ids = []

        for ent_info in ent_infos:
            ftrack_id = ent_info["entityId"]
            entity_type = ent_info["entity_type"]
            parent_id = ent_info["parent_id"]

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
