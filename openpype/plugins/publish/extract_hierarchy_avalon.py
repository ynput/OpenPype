import collections
from copy import deepcopy
import pyblish.api
from openpype.client import (
    get_assets,
    get_archived_assets
)
from openpype.pipeline import legacy_io


class ExtractHierarchyToAvalon(pyblish.api.ContextPlugin):
    """Create entities in Avalon based on collected data."""

    order = pyblish.api.ExtractorOrder - 0.01
    label = "Extract Hierarchy To Avalon"
    families = ["clip", "shot"]

    def process(self, context):
        if "hierarchyContext" not in context.data:
            self.log.info("skipping IntegrateHierarchyToAvalon")
            return

        if not legacy_io.Session:
            legacy_io.install()

        hierarchy_context = self._get_active_assets(context)
        self.log.debug("__ hierarchy_context: {}".format(hierarchy_context))

        project_name = context.data["projectName"]
        asset_names = self.extract_asset_names(hierarchy_context)

        asset_docs_by_name = {}
        for asset_doc in get_assets(project_name, asset_names=asset_names):
            name = asset_doc["name"]
            asset_docs_by_name[name] = asset_doc

        archived_asset_docs_by_name = collections.defaultdict(list)
        for asset_doc in get_archived_assets(
            project_name, asset_names=asset_names
        ):
            name = asset_doc["name"]
            archived_asset_docs_by_name[name].append(asset_doc)

        project_doc = None
        hierarchy_queue = collections.deque()
        for name, data in hierarchy_context.items():
            hierarchy_queue.append((name, data, None))

        while hierarchy_queue:
            item = hierarchy_queue.popleft()
            name, entity_data, parent = item

            entity_type = entity_data["entity_type"]
            if entity_type.lower() == "project":
                new_parent = project_doc = self.sync_project(
                    context,
                    entity_data
                )

            else:
                new_parent = self.sync_asset(
                    name,
                    entity_data,
                    parent,
                    project_doc,
                    asset_docs_by_name,
                    archived_asset_docs_by_name
                )
                # make sure all relative instances have correct avalon data
                self._set_avalon_data_to_relative_instances(
                    context,
                    project_name,
                    new_parent
                )

            children = entity_data.get("childs")
            if not children:
                continue

            for child_name, child_data in children.items():
                hierarchy_queue.append((child_name, child_data, new_parent))

    def extract_asset_names(self, hierarchy_context):
        """Extract all possible asset names from hierarchy context.

        Args:
            hierarchy_context (Dict[str, Any]): Nested hierarchy structure.

        Returns:
            Set[str]: All asset names from the hierarchy structure.
        """

        hierarchy_queue = collections.deque()
        for name, data in hierarchy_context.items():
            hierarchy_queue.append((name, data))

        asset_names = set()
        while hierarchy_queue:
            item = hierarchy_queue.popleft()
            name, data = item
            if data["entity_type"].lower() != "project":
                asset_names.add(name)

            children = data.get("childs")
            if children:
                for child_name, child_data in children.items():
                    hierarchy_queue.append((child_name, child_data))
        return asset_names

    def sync_project(self, context, entity_data):
        project_doc = context.data["projectEntity"]

        if "data" not in project_doc:
            project_doc["data"] = {}
        current_data = project_doc["data"]

        changes = {}
        entity_type = entity_data["entity_type"]
        if current_data.get("entityType") != entity_type:
            changes["entityType"] = entity_type

        # Custom attributes.
        attributes = entity_data.get("custom_attributes") or {}
        for key, value in attributes.items():
            if key not in current_data or current_data[key] != value:
                update_key = "data.{}".format(key)
                changes[update_key] = value
                current_data[key] = value

        if changes:
            # Update entity data with input data
            legacy_io.update_one(
                {"_id": project_doc["_id"]},
                {"$set": changes}
            )
        return project_doc

    def _prepare_new_tasks(self, asset_doc, entity_data):
        new_tasks = entity_data.get("tasks") or {}
        if not asset_doc:
            return new_tasks

        old_tasks = asset_doc.get("data", {}).get("tasks")
        # Just use new tasks if old are not available
        if not old_tasks:
            return new_tasks

        output = deepcopy(old_tasks)
        # Create mapping of lowered task names from old tasks
        cur_task_low_mapping = {
            task_name.lower(): task_name
            for task_name in old_tasks
        }
        # Add/update tasks from new entity data
        for task_name, task_info in new_tasks.items():
            task_info = deepcopy(task_info)
            task_name_low = task_name.lower()
            # Add new task
            if task_name_low not in cur_task_low_mapping:
                output[task_name] = task_info
                continue

            # Update existing task with new info
            mapped_task_name = cur_task_low_mapping.pop(task_name_low)
            src_task_info = output.pop(mapped_task_name)
            src_task_info.update(task_info)
            output[task_name] = src_task_info
        return output

    def sync_asset(
        self,
        asset_name,
        entity_data,
        parent,
        project,
        asset_docs_by_name,
        archived_asset_docs_by_name
    ):
        # Prepare data for new asset or for update comparison
        data = {
            "entityType": entity_data["entity_type"]
        }

        # Custom attributes.
        attributes = entity_data.get("custom_attributes") or {}
        for key, value in attributes.items():
            data[key] = value

        data["inputs"] = entity_data.get("inputs") or []

        # Parents and visual parent are empty if parent is project
        parents = []
        parent_id = None
        if project["_id"] != parent["_id"]:
            parent_id = parent["_id"]
            # Use parent's parents as source value
            parents.extend(parent["data"]["parents"])
            # Add parent's name to parents
            parents.append(parent["name"])

        data["visualParent"] = parent_id
        data["parents"] = parents

        asset_doc = asset_docs_by_name.get(asset_name)

        # Tasks
        data["tasks"] = self._prepare_new_tasks(asset_doc, entity_data)

        # --- Create/Unarchive asset and end ---
        if not asset_doc:
            archived_asset_doc = None
            for archived_entity in archived_asset_docs_by_name[asset_name]:
                archived_parents = (
                    archived_entity
                    .get("data", {})
                    .get("parents")
                )
                if data["parents"] == archived_parents:
                    archived_asset_doc = archived_entity
                    break

            # Create entity if doesn't exist
            if archived_asset_doc is None:
                return self.create_avalon_asset(
                    asset_name, data, project
                )

            return self.unarchive_entity(
                archived_asset_doc, data, project
            )

        # --- Update existing asset ---
        # Make sure current entity has "data" key
        if "data" not in asset_doc:
            asset_doc["data"] = {}
        cur_entity_data = asset_doc["data"]

        changes = {}
        for key, value in data.items():
            if key not in cur_entity_data or value != cur_entity_data[key]:
                update_key = "data.{}".format(key)
                changes[update_key] = value
                cur_entity_data[key] = value

        # Update asset in database if necessary
        if changes:
            # Update entity data with input data
            legacy_io.update_one(
                {"_id": asset_doc["_id"]},
                {"$set": changes}
            )
        return asset_doc

    def unarchive_entity(self, archived_doc, data, project):
        # Unarchived asset should not use same data
        asset_doc = {
            "_id": archived_doc["_id"],
            "schema": "openpype:asset-3.0",
            "name": archived_doc["name"],
            "parent": project["_id"],
            "type": "asset",
            "data": data
        }
        legacy_io.replace_one(
            {"_id": archived_doc["_id"]},
            asset_doc
        )

        return asset_doc

    def create_avalon_asset(self, name, data, project):
        asset_doc = {
            "schema": "openpype:asset-3.0",
            "name": name,
            "parent": project["_id"],
            "type": "asset",
            "data": data
        }
        self.log.debug("Creating asset: {}".format(asset_doc))
        asset_doc["_id"] = legacy_io.insert_one(asset_doc).inserted_id

        return asset_doc

    def _set_avalon_data_to_relative_instances(
        self,
        context,
        project_name,
        asset_doc
    ):
        asset_name = asset_doc["name"]
        new_parents = asset_doc["data"]["parents"]
        hierarchy = "/".join(new_parents)
        parent_name = project_name
        if new_parents:
            parent_name = new_parents[-1]

        for instance in context:
            # Skip if instance asset does not match
            instance_asset_name = instance.data.get("asset")
            if asset_name != instance_asset_name:
                continue

            instance_asset_doc = instance.data.get("assetEntity")
            # Update asset entity with new possible changes of asset document
            instance.data["assetEntity"] = asset_doc

            # Update anatomy data if asset was not set on instance
            if not instance_asset_doc:
                instance.data["anatomyData"].update({
                    "hierarchy": hierarchy,
                    "task": {},
                    "parent": parent_name
                })

    def _get_active_assets(self, context):
        """ Returns only asset dictionary.
            Usually the last part of deep dictionary which
            is not having any children
        """
        def get_pure_hierarchy_data(input_dict):
            input_dict_copy = deepcopy(input_dict)
            for key in input_dict.keys():
                self.log.debug("__ key: {}".format(key))
                # check if child key is available
                if input_dict[key].get("childs"):
                    # loop deeper
                    input_dict_copy[
                        key]["childs"] = get_pure_hierarchy_data(
                            input_dict[key]["childs"])
                elif key not in active_assets:
                    input_dict_copy.pop(key, None)
            return input_dict_copy

        hierarchy_context = context.data["hierarchyContext"]

        active_assets = []
        # filter only the active publishing instances
        for instance in context:
            if instance.data.get("publish") is False:
                continue

            if not instance.data.get("asset"):
                continue

            active_assets.append(instance.data["asset"])

        # remove duplicity in list
        active_assets = list(set(active_assets))
        self.log.debug("__ active_assets: {}".format(active_assets))

        return get_pure_hierarchy_data(hierarchy_context)
