"""
Requires:
    context     -> anatomyData
    context     -> projectEntity
    context     -> assetEntity
    instance    -> asset
    instance    -> subset
    instance    -> family

Optional:
    instance    -> version
    instance    -> resolutionWidth
    instance    -> resolutionHeight
    instance    -> fps

Provides:
    instance    -> projectEntity
    instance    -> assetEntity
    instance    -> anatomyData
    instance    -> version
    instance    -> latestVersion
"""

import copy
import json
import collections

import pyblish.api

from openpype.client import (
    get_assets,
    get_subsets,
    get_last_versions,
    get_asset_name_identifier,
)
from openpype.pipeline.version_start import get_versioning_start


class CollectAnatomyInstanceData(pyblish.api.ContextPlugin):
    """Collect Instance specific Anatomy data.

    Plugin is running for all instances on context even not active instances.
    """

    order = pyblish.api.CollectorOrder + 0.49
    label = "Collect Anatomy Instance data"

    follow_workfile_version = False

    def process(self, context):
        self.log.debug("Collecting anatomy data for all instances.")

        project_name = context.data["projectName"]
        self.fill_missing_asset_docs(context, project_name)
        self.fill_latest_versions(context, project_name)
        self.fill_anatomy_data(context)

        self.log.debug("Anatomy Data collection finished.")

    def fill_missing_asset_docs(self, context, project_name):
        self.log.debug("Querying asset documents for instances.")

        context_asset_doc = context.data.get("assetEntity")
        context_asset_name = None
        if context_asset_doc:
            context_asset_name = get_asset_name_identifier(context_asset_doc)

        instances_with_missing_asset_doc = collections.defaultdict(list)
        for instance in context:
            instance_asset_doc = instance.data.get("assetEntity")
            _asset_name = instance.data["asset"]

            # There is possibility that assetEntity on instance is already set
            # which can happen in standalone publisher
            if instance_asset_doc:
                instance_asset_name = get_asset_name_identifier(
                    instance_asset_doc)
                if instance_asset_name == _asset_name:
                    continue

            # Check if asset name is the same as what is in context
            # - they may be different, e.g. in NukeStudio
            if context_asset_name and context_asset_name == _asset_name:
                instance.data["assetEntity"] = context_asset_doc

            else:
                instances_with_missing_asset_doc[_asset_name].append(instance)

        if not instances_with_missing_asset_doc:
            self.log.debug("All instances already had right asset document.")
            return

        asset_names = list(instances_with_missing_asset_doc.keys())
        self.log.debug("Querying asset documents with names: {}".format(
            ", ".join(["\"{}\"".format(name) for name in asset_names])
        ))

        asset_docs = get_assets(project_name, asset_names=asset_names)
        asset_docs_by_name = {
            get_asset_name_identifier(asset_doc): asset_doc
            for asset_doc in asset_docs
        }

        not_found_asset_names = []
        for asset_name, instances in instances_with_missing_asset_doc.items():
            asset_doc = asset_docs_by_name.get(asset_name)
            if not asset_doc:
                not_found_asset_names.append(asset_name)
                continue

            for _instance in instances:
                _instance.data["assetEntity"] = asset_doc

        if not_found_asset_names:
            joined_asset_names = ", ".join(
                ["\"{}\"".format(name) for name in not_found_asset_names]
            )
            self.log.warning((
                "Not found asset documents with names \"{}\"."
            ).format(joined_asset_names))

    def fill_latest_versions(self, context, project_name):
        """Try to find latest version for each instance's subset.

        Key "latestVersion" is always set to latest version or `None`.

        Args:
            context (pyblish.Context)

        Returns:
            None

        """
        self.log.debug("Querying latest versions for instances.")

        hierarchy = {}
        names_by_asset_ids = collections.defaultdict(set)
        for instance in context:
            # Make sure `"latestVersion"` key is set
            latest_version = instance.data.get("latestVersion")
            instance.data["latestVersion"] = latest_version

            # Skip instances without "assetEntity"
            asset_doc = instance.data.get("assetEntity")
            if not asset_doc:
                continue

            # Store asset ids and subset names for queries
            asset_id = asset_doc["_id"]
            subset_name = instance.data["subset"]

            # Prepare instance hierarchy for faster filling latest versions
            if asset_id not in hierarchy:
                hierarchy[asset_id] = {}
            if subset_name not in hierarchy[asset_id]:
                hierarchy[asset_id][subset_name] = []
            hierarchy[asset_id][subset_name].append(instance)
            names_by_asset_ids[asset_id].add(subset_name)

        subset_docs = []
        if names_by_asset_ids:
            subset_docs = list(get_subsets(
                project_name, names_by_asset_ids=names_by_asset_ids
            ))

        subset_ids = [
            subset_doc["_id"]
            for subset_doc in subset_docs
        ]

        last_version_docs_by_subset_id = get_last_versions(
            project_name, subset_ids, fields=["name"]
        )
        for subset_doc in subset_docs:
            subset_id = subset_doc["_id"]
            last_version_doc = last_version_docs_by_subset_id.get(subset_id)
            if last_version_doc is None:
                continue

            asset_id = subset_doc["parent"]
            subset_name = subset_doc["name"]
            _instances = hierarchy[asset_id][subset_name]
            for _instance in _instances:
                _instance.data["latestVersion"] = last_version_doc["name"]

    def fill_anatomy_data(self, context):
        self.log.debug("Storing anatomy data to instance data.")

        project_doc = context.data["projectEntity"]
        project_task_types = project_doc["config"]["tasks"]

        for instance in context:
            anatomy_data = copy.deepcopy(context.data["anatomyData"])
            anatomy_data.update({
                "family": instance.data["family"],
                "subset": instance.data["subset"],
            })

            self._fill_asset_data(instance, project_doc, anatomy_data)
            self._fill_task_data(instance, project_task_types, anatomy_data)

            # Define version
            version_number = None
            if self.follow_workfile_version:
                version_number = context.data("version")

            # Even if 'follow_workfile_version' is enabled, it may not be set
            #   because workfile version was not collected to 'context.data'
            # - that can happen e.g. in 'traypublisher' or other hosts without
            #   a workfile
            if version_number is None:
                version_number = instance.data.get("version")

            # use latest version (+1) if already any exist
            if version_number is None:
                latest_version = instance.data["latestVersion"]
                if latest_version is not None:
                    version_number = int(latest_version) + 1

            # If version is not specified for instance or context
            if version_number is None:
                task_data = anatomy_data.get("task") or {}
                task_name = task_data.get("name")
                task_type = task_data.get("type")
                version_number = get_versioning_start(
                    context.data["projectName"],
                    instance.context.data["hostName"],
                    task_name=task_name,
                    task_type=task_type,
                    family=instance.data["family"],
                    subset=instance.data["subset"]
                )
            anatomy_data["version"] = version_number

            # Additional data
            resolution_width = instance.data.get("resolutionWidth")
            if resolution_width:
                anatomy_data["resolution_width"] = resolution_width

            resolution_height = instance.data.get("resolutionHeight")
            if resolution_height:
                anatomy_data["resolution_height"] = resolution_height

            pixel_aspect = instance.data.get("pixelAspect")
            if pixel_aspect:
                anatomy_data["pixel_aspect"] = float(
                    "{:0.2f}".format(float(pixel_aspect))
                )

            fps = instance.data.get("fps")
            if fps:
                anatomy_data["fps"] = float("{:0.2f}".format(float(fps)))

            # Store anatomy data
            instance.data["projectEntity"] = project_doc
            instance.data["anatomyData"] = anatomy_data
            instance.data["version"] = version_number

            # Log collected data
            instance_name = instance.data["name"]
            instance_label = instance.data.get("label")
            if instance_label:
                instance_name += " ({})".format(instance_label)
            self.log.debug("Anatomy data for instance {}: {}".format(
                instance_name,
                json.dumps(anatomy_data, indent=4)
            ))

    def _fill_asset_data(self, instance, project_doc, anatomy_data):
        # QUESTION should we make sure that all asset data are poped if asset
        #   data cannot be found?
        # - 'asset', 'hierarchy', 'parent', 'folder'
        asset_doc = instance.data.get("assetEntity")
        if asset_doc:
            parents = asset_doc["data"].get("parents") or list()
            parent_name = project_doc["name"]
            if parents:
                parent_name = parents[-1]

            hierarchy = "/".join(parents)
            anatomy_data.update({
                "asset": asset_doc["name"],
                "hierarchy": hierarchy,
                "parent": parent_name,
                "folder": {
                    "name": asset_doc["name"],
                },
            })
            return

        if instance.data.get("newAssetPublishing"):
            hierarchy = instance.data["hierarchy"]
            anatomy_data["hierarchy"] = hierarchy

            parent_name = project_doc["name"]
            if hierarchy:
                parent_name = hierarchy.split("/")[-1]

            asset_name = instance.data["asset"].split("/")[-1]
            anatomy_data.update({
                "asset": asset_name,
                "hierarchy": hierarchy,
                "parent": parent_name,
                "folder": {
                    "name": asset_name,
                },
            })

    def _fill_task_data(self, instance, project_task_types, anatomy_data):
        # QUESTION should we make sure that all task data are poped if task
        #   data cannot be resolved?
        # - 'task'

        # Skip if there is no task
        task_name = instance.data.get("task")
        if not task_name:
            return

        # Find task data based on asset entity
        asset_doc = instance.data.get("assetEntity")
        task_data = self._get_task_data_from_asset(
            asset_doc, task_name, project_task_types
        )
        if task_data:
            # Fill task data
            # - if we're in editorial, make sure the task type is filled
            if (
                not instance.data.get("newAssetPublishing")
                or task_data["type"]
            ):
                anatomy_data["task"] = task_data
                return

        # New hierarchy is not created, so we can only skip rest of the logic
        if not instance.data.get("newAssetPublishing"):
            return

        # Try to find task data based on hierarchy context and asset name
        hierarchy_context = instance.context.data.get("hierarchyContext")
        asset_name = instance.data.get("asset")
        if not hierarchy_context or not asset_name:
            return

        project_name = instance.context.data["projectName"]
        # OpenPype approach vs AYON approach
        if "/" not in asset_name:
            tasks_info = self._find_tasks_info_in_hierarchy(
                hierarchy_context, asset_name
            )
        else:
            current_data = hierarchy_context.get(project_name, {})
            for key in asset_name.split("/"):
                if key:
                    current_data = current_data.get("childs", {}).get(key, {})
            tasks_info = current_data.get("tasks", {})

        task_info = tasks_info.get(task_name, {})
        task_type = task_info.get("type")
        task_code = (
            project_task_types
            .get(task_type, {})
            .get("short_name")
        )
        anatomy_data["task"] = {
            "name": task_name,
            "type": task_type,
            "short": task_code
        }

    def _get_task_data_from_asset(
        self, asset_doc, task_name, project_task_types
    ):
        """

        Args:
            asset_doc (Union[dict[str, Any], None]): Asset document.
            task_name (Union[str, None]): Task name.
            project_task_types (dict[str, dict[str, Any]]): Project task
                types.

        Returns:
            Union[dict[str, str], None]: Task data or None if not found.
        """

        if not asset_doc or not task_name:
            return None

        asset_tasks = asset_doc["data"]["tasks"]
        task_type = asset_tasks.get(task_name, {}).get("type")
        task_code = (
            project_task_types
            .get(task_type, {})
            .get("short_name")
        )
        return {
            "name": task_name,
            "type": task_type,
            "short": task_code
        }

    def _find_tasks_info_in_hierarchy(self, hierarchy_context, asset_name):
        """Find tasks info for an asset in editorial hierarchy.

        Args:
            hierarchy_context (dict[str, Any]): Editorial hierarchy context.
            asset_name (str): Asset name.

        Returns:
            dict[str, dict[str, Any]]: Tasks info by name.
        """

        hierarchy_queue = collections.deque()
        hierarchy_queue.append(copy.deepcopy(hierarchy_context))
        while hierarchy_queue:
            item = hierarchy_queue.popleft()
            if asset_name in item:
                return item[asset_name].get("tasks") or {}

            for subitem in item.values():
                hierarchy_queue.extend(subitem.get("childs") or [])
        return {}
