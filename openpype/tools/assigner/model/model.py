"""Assigner tool models.

Models are not specific for any UI.
"""

import collections

from openpype.client import (
    get_versions,
    get_subsets,
    get_assets,
)
from .versions import VersionsModel
from .containers import ContainersModel


class AssignerToolModel(object):
    def __init__(self, controller):
        self._controller = controller

        self._containers_model = ContainersModel(self)
        self._versions_model = VersionsModel(self)

        self._current_container_ids = set()
        # self._current_asset_ids = set()
        # self._current_version_ids = set()
        self._asset_docs_by_id = {}
        self._subset_docs_by_id = {}
        self._version_docs_by_id = {}

    @property
    def project_name(self):
        return self._controller.project_name

    @property
    def event_system(self):
        return self._controller.event_system

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
        # self._asset_docs_by_id = {}
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
            for asset_doc in asset_docs
        }
        subset_docs = get_subsets(self.project_name, asset_ids=asset_ids)
        self._subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in subset_docs
        }
        version_docs = get_versions(
            self.project_name,
            subset_ids=self._subset_docs_by_id.keys(),
            hero=True
        )
        self._version_docs_by_id = {
            version_doc["_id"]: version_doc
            for version_doc in version_docs
        }

        self._versions_model.set_asset_ids(
            set(self._asset_docs_by_id.keys())
        )
