import collections
import uuid
from datetime import datetime

from bson.objectid import ObjectId
from avalon.api import AvalonMongoDB
from openpype_modules.ftrack.lib import BaseAction, statics_icon
from openpype_modules.ftrack.lib.avalon_sync import create_chunks


class DeleteAssetSubset(BaseAction):
    '''Edit meta data action.'''

    # Action identifier.
    identifier = "delete.asset.subset"
    # Action label.
    label = "Delete Asset/Subsets"
    # Action description.
    description = "Removes from Avalon with all childs and asset from Ftrack"
    icon = statics_icon("ftrack", "action_icons", "DeleteAsset.svg")

    settings_key = "delete_asset_subset"
    # Db connection
    dbcon = None

    splitter = {"type": "label", "value": "---"}
    action_data_by_id = {}
    asset_prefix = "asset:"
    subset_prefix = "subset:"

    def __init__(self, *args, **kwargs):
        self.dbcon = AvalonMongoDB()

        super(DeleteAssetSubset, self).__init__(*args, **kwargs)

    def discover(self, session, entities, event):
        """ Validation """
        task_ids = []
        for ent_info in event["data"]["selection"]:
            if ent_info.get("entityType") == "task":
                task_ids.append(ent_info["entityId"])

        is_valid = False
        for entity in entities:
            if (
                entity["id"] in task_ids
                and entity.entity_type.lower() != "task"
            ):
                is_valid = True
                break

        if is_valid:
            is_valid = self.valid_roles(session, entities, event)
        return is_valid

    def _launch(self, event):
        try:
            entities = self._translate_event(event)
            if "values" not in event["data"]:
                self.dbcon.install()
                return self._interface(self.session, entities, event)

            confirmation = self.confirm_delete(entities, event)
            if confirmation:
                return confirmation

            self.dbcon.install()
            response = self.launch(
                self.session, entities, event
            )
        finally:
            self.dbcon.uninstall()

        return self._handle_result(response)

    def interface(self, session, entities, event):
        self.show_message(event, "Preparing data...", True)
        items = []
        title = "Choose items to delete"

        # Filter selection and get ftrack ids
        selection = event["data"].get("selection") or []
        ftrack_ids = []
        project_in_selection = False
        for entity in selection:
            entity_type = (entity.get("entityType") or "").lower()
            if entity_type != "task":
                if entity_type == "show":
                    project_in_selection = True
                continue

            ftrack_id = entity.get("entityId")
            if not ftrack_id:
                continue

            ftrack_ids.append(ftrack_id)

        if project_in_selection:
            msg = "It is not possible to use this action on project entity."
            self.show_message(event, msg, True)

        # Filter event even more (skip task entities)
        # - task entities are not relevant for avalon
        entity_mapping = {}
        for entity in entities:
            ftrack_id = entity["id"]
            if ftrack_id not in ftrack_ids:
                continue

            if entity.entity_type.lower() == "task":
                ftrack_ids.remove(ftrack_id)

            entity_mapping[ftrack_id] = entity

        if not ftrack_ids:
            # It is bug if this happens!
            return {
                "success": False,
                "message": "Invalid selection for this action (Bug)"
            }

        if entities[0].entity_type.lower() == "project":
            project = entities[0]
        else:
            project = entities[0]["project"]

        project_name = project["full_name"]
        self.dbcon.Session["AVALON_PROJECT"] = project_name

        selected_av_entities = list(self.dbcon.find({
            "type": "asset",
            "data.ftrackId": {"$in": ftrack_ids}
        }))
        found_without_ftrack_id = {}
        if len(selected_av_entities) != len(ftrack_ids):
            found_ftrack_ids = [
                ent["data"]["ftrackId"] for ent in selected_av_entities
            ]
            for ftrack_id, entity in entity_mapping.items():
                if ftrack_id in found_ftrack_ids:
                    continue

                av_ents_by_name = list(self.dbcon.find({
                    "type": "asset",
                    "name": entity["name"]
                }))
                if not av_ents_by_name:
                    continue

                ent_path_items = [ent["name"] for ent in entity["link"]]
                parents = ent_path_items[1:len(ent_path_items)-1:]
                # TODO we should say to user that
                # few of them are missing in avalon
                for av_ent in av_ents_by_name:
                    if av_ent["data"]["parents"] != parents:
                        continue

                    # TODO we should say to user that found entity
                    # with same name does not match same ftrack id?
                    if "ftrackId" not in av_ent["data"]:
                        selected_av_entities.append(av_ent)
                        found_without_ftrack_id[str(av_ent["_id"])] = ftrack_id
                        break

        if not selected_av_entities:
            return {
                "success": True,
                "message": (
                    "Didn't found entities in avalon."
                    " You can use Ftrack's Delete button for the selection."
                )
            }

        # Remove cached action older than 2 minutes
        old_action_ids = []
        for action_id, data in self.action_data_by_id.items():
            created_at = data.get("created_at")
            if not created_at:
                old_action_ids.append(action_id)
                continue
            cur_time = datetime.now()
            existing_in_sec = (created_at - cur_time).total_seconds()
            if existing_in_sec > 60 * 2:
                old_action_ids.append(action_id)

        for action_id in old_action_ids:
            self.action_data_by_id.pop(action_id, None)

        # Store data for action id
        action_id = str(uuid.uuid1())
        self.action_data_by_id[action_id] = {
            "attempt": 1,
            "created_at": datetime.now(),
            "project_name": project_name,
            "subset_ids_by_name": {},
            "subset_ids_by_parent": {},
            "without_ftrack_id": found_without_ftrack_id
        }

        id_item = {
            "type": "hidden",
            "name": "action_id",
            "value": action_id
        }

        items.append(id_item)
        asset_ids = [ent["_id"] for ent in selected_av_entities]
        subsets_for_selection = self.dbcon.find({
            "type": "subset",
            "parent": {"$in": asset_ids}
        })

        asset_ending = ""
        if len(selected_av_entities) > 1:
            asset_ending = "s"

        asset_title = {
            "type": "label",
            "value": "# Delete asset{}:".format(asset_ending)
        }
        asset_note = {
            "type": "label",
            "value": (
                "<p><i>NOTE: Action will delete checked entities"
                " in Ftrack and Avalon with all children entities and"
                " published content.</i></p>"
            )
        }

        items.append(asset_title)
        items.append(asset_note)

        asset_items = collections.defaultdict(list)
        for asset in selected_av_entities:
            ent_path_items = [project_name]
            ent_path_items.extend(asset.get("data", {}).get("parents") or [])
            ent_path_to_parent = "/".join(ent_path_items) + "/"
            asset_items[ent_path_to_parent].append(asset)

        for asset_parent_path, assets in sorted(asset_items.items()):
            items.append({
                "type": "label",
                "value": "## <b>- {}</b>".format(asset_parent_path)
            })
            for asset in assets:
                items.append({
                    "label": asset["name"],
                    "name": "{}{}".format(
                        self.asset_prefix, str(asset["_id"])
                    ),
                    "type": 'boolean',
                    "value": False
                })

        subset_ids_by_name = collections.defaultdict(list)
        subset_ids_by_parent = collections.defaultdict(list)
        for subset in subsets_for_selection:
            subset_id = subset["_id"]
            name = subset["name"]
            parent_id = subset["parent"]
            subset_ids_by_name[name].append(subset_id)
            subset_ids_by_parent[parent_id].append(subset_id)

        if not subset_ids_by_name:
            return {
                "items": items,
                "title": title
            }

        subset_ending = ""
        if len(subset_ids_by_name.keys()) > 1:
            subset_ending = "s"

        subset_title = {
            "type": "label",
            "value": "# Subset{} to delete:".format(subset_ending)
        }
        subset_note = {
            "type": "label",
            "value": (
                "<p><i>WARNING: Subset{} will be removed"
                " for all <b>selected</b> entities.</i></p>"
            ).format(subset_ending)
        }

        items.append(self.splitter)
        items.append(subset_title)
        items.append(subset_note)

        for name in subset_ids_by_name:
            items.append({
                "label": "<b>{}</b>".format(name),
                "name": "{}{}".format(self.subset_prefix, name),
                "type": "boolean",
                "value": False
            })

        self.action_data_by_id[action_id]["subset_ids_by_parent"] = (
            subset_ids_by_parent
        )
        self.action_data_by_id[action_id]["subset_ids_by_name"] = (
            subset_ids_by_name
        )

        return {
            "items": items,
            "title": title
        }

    def confirm_delete(self, entities, event):
        values = event["data"]["values"]
        action_id = values.get("action_id")
        spec_data = self.action_data_by_id.get(action_id)
        if not spec_data:
            # it is a bug if this happens!
            return {
                "success": False,
                "message": "Something bad has happened. Please try again."
            }

        # Process Delete confirmation
        delete_key = values.get("delete_key")
        if delete_key:
            delete_key = delete_key.lower().strip()
            # Go to launch part if user entered `delete`
            if delete_key == "delete":
                return
            # Skip whole process if user didn't enter any text
            elif delete_key == "":
                self.action_data_by_id.pop(action_id, None)
                return {
                    "success": True,
                    "message": "Deleting cancelled (delete entry was empty)"
                }
            # Get data to show again
            to_delete = spec_data["to_delete"]

        else:
            to_delete = collections.defaultdict(list)
            for key, value in values.items():
                if not value:
                    continue
                if key.startswith(self.asset_prefix):
                    _key = key.replace(self.asset_prefix, "")
                    to_delete["assets"].append(_key)

                elif key.startswith(self.subset_prefix):
                    _key = key.replace(self.subset_prefix, "")
                    to_delete["subsets"].append(_key)

            self.action_data_by_id[action_id]["to_delete"] = to_delete

        asset_to_delete = len(to_delete.get("assets") or []) > 0
        subset_to_delete = len(to_delete.get("subsets") or []) > 0

        if not asset_to_delete and not subset_to_delete:
            self.action_data_by_id.pop(action_id, None)
            return {
                "success": True,
                "message": "Nothing was selected to delete"
            }

        attempt = spec_data["attempt"]
        if attempt > 3:
            self.action_data_by_id.pop(action_id, None)
            return {
                "success": False,
                "message": "You didn't enter \"DELETE\" properly 3 times!"
            }

        self.action_data_by_id[action_id]["attempt"] += 1

        title = "Confirmation of deleting"

        if asset_to_delete:
            asset_len = len(to_delete["assets"])
            asset_ending = ""
            if asset_len > 1:
                asset_ending = "s"
            title += " {} Asset{}".format(asset_len, asset_ending)
            if subset_to_delete:
                title += " and"

        if subset_to_delete:
            sub_len = len(to_delete["subsets"])
            type_ending = ""
            sub_ending = ""
            if sub_len == 1:
                subset_ids_by_name = spec_data["subset_ids_by_name"]
                if len(subset_ids_by_name[to_delete["subsets"][0]]) > 1:
                    sub_ending = "s"

            elif sub_len > 1:
                type_ending = "s"
                sub_ending = "s"

            title += " {} type{} of subset{}".format(
                sub_len, type_ending, sub_ending
            )

        items = []

        id_item = {"type": "hidden", "name": "action_id", "value": action_id}
        delete_label = {
            'type': 'label',
            'value': '# Please enter "DELETE" to confirm #'
        }
        delete_item = {
            "name": "delete_key",
            "type": "text",
            "value": "",
            "empty_text": "Type Delete here..."
        }

        items.append(id_item)
        items.append(delete_label)
        items.append(delete_item)

        return {
            "items": items,
            "title": title
        }

    def launch(self, session, entities, event):
        self.show_message(event, "Processing...", True)
        values = event["data"]["values"]
        action_id = values.get("action_id")
        spec_data = self.action_data_by_id.get(action_id)
        if not spec_data:
            # it is a bug if this happens!
            return {
                "success": False,
                "message": "Something bad has happened. Please try again."
            }

        report_messages = collections.defaultdict(list)

        project_name = spec_data["project_name"]
        to_delete = spec_data["to_delete"]
        self.dbcon.Session["AVALON_PROJECT"] = project_name

        assets_to_delete = to_delete.get("assets") or []
        subsets_to_delete = to_delete.get("subsets") or []

        # Convert asset ids to ObjectId obj
        assets_to_delete = [
            ObjectId(asset_id)
            for asset_id in assets_to_delete
            if asset_id
        ]

        subset_ids_by_parent = spec_data["subset_ids_by_parent"]
        subset_ids_by_name = spec_data["subset_ids_by_name"]

        subset_ids_to_archive = []
        asset_ids_to_archive = []
        ftrack_ids_to_delete = []
        if len(assets_to_delete) > 0:
            map_av_ftrack_id = spec_data["without_ftrack_id"]
            # Prepare data when deleting whole avalon asset
            avalon_assets = self.dbcon.find(
                {"type": "asset"},
                {
                    "_id": 1,
                    "data.visualParent": 1,
                    "data.ftrackId": 1
                }
            )
            avalon_assets_by_parent = collections.defaultdict(list)
            for asset in avalon_assets:
                asset_id = asset["_id"]
                parent_id = asset["data"]["visualParent"]
                avalon_assets_by_parent[parent_id].append(asset)
                if asset_id in assets_to_delete:
                    ftrack_id = map_av_ftrack_id.get(str(asset_id))
                    if not ftrack_id:
                        ftrack_id = asset["data"].get("ftrackId")

                    if ftrack_id:
                        ftrack_ids_to_delete.append(ftrack_id)

            children_queue = collections.deque()
            for mongo_id in assets_to_delete:
                children_queue.append(mongo_id)

            while children_queue:
                mongo_id = children_queue.popleft()
                if mongo_id in asset_ids_to_archive:
                    continue

                asset_ids_to_archive.append(mongo_id)
                for subset_id in subset_ids_by_parent.get(mongo_id, []):
                    if subset_id not in subset_ids_to_archive:
                        subset_ids_to_archive.append(subset_id)

                children = avalon_assets_by_parent.get(mongo_id)
                if not children:
                    continue

                for child in children:
                    child_id = child["_id"]
                    if child_id not in asset_ids_to_archive:
                        children_queue.append(child_id)

        # Prepare names of assets in ftrack and ids of subsets in mongo
        asset_names_to_delete = []
        if len(subsets_to_delete) > 0:
            for name in subsets_to_delete:
                asset_names_to_delete.append(name)
                for subset_id in subset_ids_by_name[name]:
                    if subset_id in subset_ids_to_archive:
                        continue
                    subset_ids_to_archive.append(subset_id)

        # Get ftrack ids of entities where will be delete only asset
        not_deleted_entities_id = []
        ftrack_id_name_map = {}
        if asset_names_to_delete:
            for entity in entities:
                ftrack_id = entity["id"]
                ftrack_id_name_map[ftrack_id] = entity["name"]
                if ftrack_id not in ftrack_ids_to_delete:
                    not_deleted_entities_id.append(ftrack_id)

        mongo_proc_txt = "MongoProcessing: "
        ftrack_proc_txt = "Ftrack processing: "
        if asset_ids_to_archive:
            self.log.debug("{}Archivation of assets <{}>".format(
                mongo_proc_txt,
                ", ".join([str(id) for id in asset_ids_to_archive])
            ))
            self.dbcon.update_many(
                {
                    "_id": {"$in": asset_ids_to_archive},
                    "type": "asset"
                },
                {"$set": {"type": "archived_asset"}}
            )

        if subset_ids_to_archive:
            self.log.debug("{}Archivation of subsets <{}>".format(
                mongo_proc_txt,
                ", ".join([str(id) for id in subset_ids_to_archive])
            ))
            self.dbcon.update_many(
                {
                    "_id": {"$in": subset_ids_to_archive},
                    "type": "subset"
                },
                {"$set": {"type": "archived_subset"}}
            )

        if ftrack_ids_to_delete:
            self.log.debug("{}Deleting Ftrack Entities <{}>".format(
                ftrack_proc_txt, ", ".join(ftrack_ids_to_delete)
            ))

            entities_by_link_len = self._prepare_entities_before_delete(
                ftrack_ids_to_delete, session
            )
            for link_len in sorted(entities_by_link_len.keys(), reverse=True):
                for entity in entities_by_link_len[link_len]:
                    session.delete(entity)

                try:
                    session.commit()
                except Exception:
                    ent_path = "/".join(
                        [ent["name"] for ent in entity["link"]]
                    )
                    msg = "Failed to delete entity"
                    report_messages[msg].append(ent_path)
                    session.rollback()
                    self.log.warning(
                        "{} <{}>".format(msg, ent_path),
                        exc_info=True
                    )

        if not_deleted_entities_id and asset_names_to_delete:
            joined_not_deleted = ",".join([
                "\"{}\"".format(ftrack_id)
                for ftrack_id in not_deleted_entities_id
            ])
            joined_asset_names = ",".join([
                "\"{}\"".format(name)
                for name in asset_names_to_delete
            ])
            # Find assets of selected entities with names of checked subsets
            assets = session.query((
                "select id from Asset where"
                " context_id in ({}) and name in ({})"
            ).format(joined_not_deleted, joined_asset_names)).all()

            self.log.debug("{}Deleting Ftrack Assets <{}>".format(
                ftrack_proc_txt,
                ", ".join([asset["id"] for asset in assets])
            ))
            for asset in assets:
                session.delete(asset)
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                    msg = "Failed to delete asset"
                    report_messages[msg].append(asset["id"])
                    self.log.warning(
                        "Asset: {} <{}>".format(asset["name"], asset["id"]),
                        exc_info=True
                    )

        return self.report_handle(report_messages, project_name, event)

    def _prepare_entities_before_delete(self, ftrack_ids_to_delete, session):
        """Filter children entities to avoid CircularDependencyError."""
        joined_ids_to_delete = ", ".join(
            ["\"{}\"".format(id) for id in ftrack_ids_to_delete]
        )
        to_delete_entities = session.query(
            "select id, link from TypedContext where id in ({})".format(
                joined_ids_to_delete
            )
        ).all()
        # Find all children entities and add them to list
        # - Delete tasks first then their parents and continue
        parent_ids_to_delete = [
            entity["id"]
            for entity in to_delete_entities
        ]
        while parent_ids_to_delete:
            joined_parent_ids_to_delete = ",".join([
                "\"{}\"".format(ftrack_id)
                for ftrack_id in parent_ids_to_delete
            ])
            _to_delete = session.query((
                "select id, link from TypedContext where parent_id in ({})"
            ).format(joined_parent_ids_to_delete)).all()
            parent_ids_to_delete = []
            for entity in _to_delete:
                parent_ids_to_delete.append(entity["id"])
                to_delete_entities.append(entity)

        # Unset 'task_id' from AssetVersion entities
        # - when task is deleted the asset version is not marked for deletion
        task_ids = set(
            entity["id"]
            for entity in to_delete_entities
            if entity.entity_type.lower() == "task"
        )
        for chunk in create_chunks(task_ids):
            asset_versions = session.query((
                "select id, task_id from AssetVersion where task_id in ({})"
            ).format(self.join_query_keys(chunk))).all()
            for asset_version in asset_versions:
                asset_version["task_id"] = None
            session.commit()

        entities_by_link_len = collections.defaultdict(list)
        for entity in to_delete_entities:
            entities_by_link_len[len(entity["link"])].append(entity)

        return entities_by_link_len

    def report_handle(self, report_messages, project_name, event):
        if not report_messages:
            return {
                "success": True,
                "message": "Deletion was successful!"
            }

        title = "Delete report ({}):".format(project_name)
        items = []
        items.append({
            "type": "label",
            "value": "# Deleting was not completely successful"
        })
        items.append({
            "type": "label",
            "value": "<p><i>Check logs for more information</i></p>"
        })
        for msg, _items in report_messages.items():
            if not _items or not msg:
                continue

            items.append({
                "type": "label",
                "value": "# {}".format(msg)
            })

            if isinstance(_items, str):
                _items = [_items]
            items.append({
                "type": "label",
                "value": '<p>{}</p>'.format("<br>".join(_items))
            })
            items.append(self.splitter)

        self.show_interface(items, title, event)

        return {
            "success": False,
            "message": "Deleting finished. Read report messages."
        }


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    DeleteAssetSubset(session).register()
