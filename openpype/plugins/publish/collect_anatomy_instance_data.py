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

from openpype.pipeline import legacy_io


class CollectAnatomyInstanceData(pyblish.api.ContextPlugin):
    """Collect Instance specific Anatomy data.

    Plugin is running for all instances on context even not active instances.
    """

    order = pyblish.api.CollectorOrder + 0.49
    label = "Collect Anatomy Instance data"

    follow_workfile_version = False

    def process(self, context):
        self.log.info("Collecting anatomy data for all instances.")

        self.fill_missing_asset_docs(context)
        self.fill_latest_versions(context)
        self.fill_anatomy_data(context)

        self.log.info("Anatomy Data collection finished.")

    def fill_missing_asset_docs(self, context):
        self.log.debug("Qeurying asset documents for instances.")

        context_asset_doc = context.data.get("assetEntity")

        instances_with_missing_asset_doc = collections.defaultdict(list)
        for instance in context:
            instance_asset_doc = instance.data.get("assetEntity")
            _asset_name = instance.data["asset"]

            # There is possibility that assetEntity on instance is already set
            # which can happen in standalone publisher
            if (
                instance_asset_doc
                and instance_asset_doc["name"] == _asset_name
            ):
                continue

            # Check if asset name is the same as what is in context
            # - they may be different, e.g. in NukeStudio
            if context_asset_doc and context_asset_doc["name"] == _asset_name:
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
        asset_docs = legacy_io.find({
            "type": "asset",
            "name": {"$in": asset_names}
        })
        asset_docs_by_name = {
            asset_doc["name"]: asset_doc
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

    def fill_latest_versions(self, context):
        """Try to find latest version for each instance's subset.

        Key "latestVersion" is always set to latest version or `None`.

        Args:
            context (pyblish.Context)

        Returns:
            None

        """
        self.log.debug("Qeurying latest versions for instances.")

        hierarchy = {}
        subset_filters = []
        for instance in context:
            # Make sure `"latestVersion"` key is set
            latest_version = instance.data.get("latestVersion")
            instance.data["latestVersion"] = latest_version

            # Skip instances withou "assetEntity"
            asset_doc = instance.data.get("assetEntity")
            if not asset_doc:
                continue

            # Store asset ids and subset names for queries
            asset_id = asset_doc["_id"]
            subset_name = instance.data["subset"]

            # Prepare instance hiearchy for faster filling latest versions
            if asset_id not in hierarchy:
                hierarchy[asset_id] = {}
            if subset_name not in hierarchy[asset_id]:
                hierarchy[asset_id][subset_name] = []
            hierarchy[asset_id][subset_name].append(instance)
            subset_filters.append({
                "parent": asset_id,
                "name": subset_name
            })

        subset_docs = []
        if subset_filters:
            subset_docs = list(legacy_io.find({
                "type": "subset",
                "$or": subset_filters
            }))

        subset_ids = [
            subset_doc["_id"]
            for subset_doc in subset_docs
        ]

        last_version_by_subset_id = self._query_last_versions(subset_ids)
        for subset_doc in subset_docs:
            subset_id = subset_doc["_id"]
            last_version = last_version_by_subset_id.get(subset_id)
            if last_version is None:
                continue

            asset_id = subset_doc["parent"]
            subset_name = subset_doc["name"]
            _instances = hierarchy[asset_id][subset_name]
            for _instance in _instances:
                _instance.data["latestVersion"] = last_version

    def _query_last_versions(self, subset_ids):
        """Retrieve all latest versions for entered subset_ids.

        Args:
            subset_ids (list): List of subset ids with type `ObjectId`.

        Returns:
            dict: Key is subset id and value is last version name.
        """
        _pipeline = [
            # Find all versions of those subsets
            {"$match": {
                "type": "version",
                "parent": {"$in": subset_ids}
            }},
            # Sorting versions all together
            {"$sort": {"name": 1}},
            # Group them by "parent", but only take the last
            {"$group": {
                "_id": "$parent",
                "_version_id": {"$last": "$_id"},
                "name": {"$last": "$name"}
            }}
        ]

        last_version_by_subset_id = {}
        for doc in legacy_io.aggregate(_pipeline):
            subset_id = doc["_id"]
            last_version_by_subset_id[subset_id] = doc["name"]

        return last_version_by_subset_id

    def fill_anatomy_data(self, context):
        self.log.debug("Storing anatomy data to instance data.")

        project_doc = context.data["projectEntity"]
        context_asset_doc = context.data.get("assetEntity")

        project_task_types = project_doc["config"]["tasks"]

        for instance in context:
            if self.follow_workfile_version:
                version_number = context.data('version')
            else:
                version_number = instance.data.get("version")
            # If version is not specified for instance or context
            if version_number is None:
                # TODO we should be able to change default version by studio
                # preferences (like start with version number `0`)
                version_number = 1
                # use latest version (+1) if already any exist
                latest_version = instance.data["latestVersion"]
                if latest_version is not None:
                    version_number += int(latest_version)

            anatomy_updates = {
                "asset": instance.data["asset"],
                "family": instance.data["family"],
                "subset": instance.data["subset"],
                "version": version_number
            }

            # Hiearchy
            asset_doc = instance.data.get("assetEntity")
            if (
                asset_doc
                and (
                    not context_asset_doc
                    or asset_doc["_id"] != context_asset_doc["_id"]
                )
            ):
                parents = asset_doc["data"].get("parents") or list()
                parent_name = project_doc["name"]
                if parents:
                    parent_name = parents[-1]
                anatomy_updates["hierarchy"] = "/".join(parents)
                anatomy_updates["parent"] = parent_name

            # Task
            task_name = instance.data.get("task")
            if task_name:
                asset_tasks = asset_doc["data"]["tasks"]
                task_type = asset_tasks.get(task_name, {}).get("type")
                task_code = (
                    project_task_types
                    .get(task_type, {})
                    .get("short_name")
                )
                anatomy_updates["task"] = {
                    "name": task_name,
                    "type": task_type,
                    "short": task_code
                }

            # Additional data
            resolution_width = instance.data.get("resolutionWidth")
            if resolution_width:
                anatomy_updates["resolution_width"] = resolution_width

            resolution_height = instance.data.get("resolutionHeight")
            if resolution_height:
                anatomy_updates["resolution_height"] = resolution_height

            pixel_aspect = instance.data.get("pixelAspect")
            if pixel_aspect:
                anatomy_updates["pixel_aspect"] = float(
                    "{:0.2f}".format(float(pixel_aspect))
                )

            fps = instance.data.get("fps")
            if fps:
                anatomy_updates["fps"] = float("{:0.2f}".format(float(fps)))

            anatomy_data = copy.deepcopy(context.data["anatomyData"])
            anatomy_data.update(anatomy_updates)

            # Store anatomy data
            instance.data["projectEntity"] = project_doc
            instance.data["anatomyData"] = anatomy_data
            instance.data["version"] = version_number

            # Log collected data
            instance_name = instance.data["name"]
            instance_label = instance.data.get("label")
            if instance_label:
                instance_name += "({})".format(instance_label)
            self.log.debug("Anatomy data for instance {}: {}".format(
                instance_name,
                json.dumps(anatomy_data, indent=4)
            ))
