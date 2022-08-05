"""Assigner tool models.

Models are not specific for any UI.
"""

import collections

from openpype.client import (
    get_versions,
    get_subsets,
    get_assets,
)
from .common import convert_documents
from .versions import VersionsModel
from .containers import ContainersModel
from .thumbnails import ThumbnailsModel


class AssignerToolModel(object):
    version_fields = [
        "_id",
        "name",
        "parent",
        "type",
        "version_id",
        "data.author",
        "data.time",
        "data.step",
        "data.frameStart",
        "data.frameEnd",
        "data.handleStart",
        "data.handleEnd",
        "data.thumbnail_id",
    ]

    def __init__(self, controller):
        self._controller = controller

        self.event_system.add_callback(
            "container.selection.changed",
            self._on_container_selection_change
        )
        self.event_system.add_callback(
            "version.selection.changed",
            self._on_version_selection_change
        )

        self._containers_model = ContainersModel(self)
        self._versions_model = VersionsModel(self)
        self._thumbnails_model = ThumbnailsModel(self)

        self._current_container_ids = set()
        self._current_version_ids = set()

        self._asset_docs_by_id = {}
        self._subset_docs_by_id = {}
        self._version_docs_by_id = {}

    @property
    def project_name(self):
        return self._controller.project_name

    @property
    def event_system(self):
        return self._controller.event_system

    def _on_container_selection_change(self, event):
        self.set_current_containers(event["container_ids"])

    def _on_version_selection_change(self, event):
        self.set_current_versions(event["version_ids"])

    def get_host_containers(self):
        return self._controller.host.get_containers()

    def get_asset_docs_by_ids(self, asset_ids):
        asset_docs = []
        if not asset_ids:
            return asset_docs

        for asset_id in set(asset_ids):
            asset_doc = self._asset_docs_by_id.get(asset_id)
            if asset_doc is not None:
                asset_docs.append(asset_doc)
        return asset_docs

    def _filter_docs_by_parent_id(self, parent_ids, docs):
        output = collections.defaultdict(list)
        if not parent_ids:
            return output
        parent_ids = set(parent_ids)
        for doc in docs:
            parent_id = doc["parent"]
            if parent_id in parent_ids:
                output[parent_id].append(doc)
        return output

    def get_subset_docs_by_asset_ids(self, asset_ids):
        return self._filter_docs_by_parent_id(
            asset_ids, self._subset_docs_by_id.values()
        )

    def get_version_docs_by_subset_ids(self, subset_ids):
        return self._filter_docs_by_parent_id(
            subset_ids, self._version_docs_by_id.values()
        )

    def refresh(self):
        self._containers_model.refresh_containers()
        available_container_ids = (
            self._containers_model.get_available_container_ids()
        )
        # Probably shoult restart current containers variable
        self.set_current_containers({
            container_id
            for container_id in self._current_container_ids
            if container_id in available_container_ids
        })

    def get_container_groups(self):
        return self._containers_model.get_container_groups()

    def get_current_containers_subset_items(self):
        return self._versions_model.get_subset_items()

    def set_current_containers(self, container_ids):
        if self._current_container_ids == container_ids:
            return

        self._current_container_ids == container_ids
        containers = self._containers_model.get_containers_by_id(container_ids)
        asset_ids = {
            container.asset_id
            for container in containers
        }
        asset_docs = get_assets(self.project_name, asset_ids=asset_ids)
        self._asset_docs_by_id = {
            asset_doc["_id"]: asset_doc
            for asset_doc in convert_documents(asset_docs)
        }

        subset_docs = get_subsets(self.project_name, asset_ids=asset_ids)
        self._subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in convert_documents(subset_docs)
        }

        version_docs = get_versions(
            self.project_name,
            subset_ids=self._subset_docs_by_id.keys(),
            hero=True,
            fields=self.version_fields
        )
        self._version_docs_by_id = {
            version_doc["_id"]: version_doc
            for version_doc in convert_documents(version_docs)
        }

        self._current_version_ids = {
            version_id
            for version_id in self._current_version_ids
            if version_id in self._version_docs_by_id
        }
        self._versions_model.set_asset_ids(
            set(self._asset_docs_by_id.keys())
        )
        self._context_changed("containers")

    def set_current_versions(self, version_ids):
        version_ids = set(version_ids)
        if self._current_version_ids == version_ids:
            return

        self._current_version_ids = version_ids
        self._context_changed("versions")

    def _context_changed(self, source_context_type):
        self.event_system.emit(
            "model.context.changed",
            {
                "container_ids": list(self._current_container_ids),
                "version_ids": list(self._current_version_ids),
                "changed_type": source_context_type
            }
        )

    def _get_thumbnail_ids_for_asset_ids(self, asset_ids):
        thumbnail_ids = []
        for asset_id in asset_ids:
            asset_doc = self._asset_docs_by_id[asset_id]
            thumbnail_ids.append(asset_doc["data"].get("thumbnail_id"))
        return thumbnail_ids

    def get_thumbnail_ids(self):
        if self._current_version_ids:
            return self._versions_model.get_thumbnail_ids_for_version_ids(
                self._current_version_ids
            )

        if self._current_container_ids:
            return self._get_thumbnail_ids_for_asset_ids(
                self._current_container_ids
            )
        return []

    def get_thumbnail_source(self, thumbnail_id):
        return self._thumbnails_model.get_thumbnail_source(thumbnail_id)

    def get_thumbnail_for_version(self, version_id):
        thumbnail_ids = self._versions_model.get_thumbnail_ids_for_version_ids(
            [version_id]
        )
        thumbnail_id = None
        if thumbnail_ids:
            thumbnail_id = thumbnail_ids[0]
        return self.get_thumbnail_source(thumbnail_id)

    def get_context_thumbnail_sources(self):
        thumbnail_ids = self.get_thumbnail_ids()
        return self._thumbnails_model.get_thumbnail_sources(thumbnail_ids)
