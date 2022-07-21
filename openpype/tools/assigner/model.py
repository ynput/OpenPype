"""Assigner tool models.

Models are not specific for any UI.
"""
import copy
import collections
from uuid import uuid4

from openpype.client import (
    get_representations,
    get_versions,
    get_subsets,
    get_assets,
)
from openpype.pipeline import schema


class ContainerGroupItem(object):
    """Containers group item.

    Containers are grouped by representation id (and it's full context).

    Args:
        asset_id (ObjectId): Asset database id.
        asset_name (str): Asset name.
        subset_id (ObjectId): Subset database id.
        subset_name (str): Name of subset.
        family (str): Subset family.
        version_id (ObjectId): Version database id.
        version (Union[int, HeroVersion]): Version number or HeroVersion.
        representation_id (str): Representation database id as string.
        representation_name (str): Name of representation
    """

    def __init__(
        self,
        asset_id,
        asset_name,
        subset_id,
        subset_name,
        family,
        version_id,
        version,
        representation_id,
        representation_name,
        thumbnail_id,
    ):
        is_valid = (
            asset_id
            and subset_id
            and version_id
            and family
            and representation_name
        )
        label = "Invalid {}".format(representation_id)
        if is_valid:
            label = "{}:{}:{}".format(
                asset_name,
                subset_name,
                representation_name
            )
        self._label = label
        self._asset_id = asset_id
        self._subset_id = subset_id
        self._version_id = version_id
        self._version = version
        self._representation_id = representation_id
        self._family = family
        self._is_valid = is_valid
        self._thumbnail_id = thumbnail_id

        self._containers_by_id = {}

    @property
    def id(self):
        return self._representation_id

    @property
    def is_valid(self):
        return self._is_valid

    @property
    def thumbnail_id(self):
        return self._thumbnail_id

    @property
    def label(self):
        return self._label

    @property
    def family(self):
        return self._family

    @property
    def representation_id(self):
        """Representation id from which was container loaded.

        Returns:
            str: Database id of representation.
        """

        return self._representation_id

    @property
    def version_id(self):
        """Version id from which was container loaded.

        Returns:
            ObjectId: Database id of version document.
            None: Representation was loaded from version which was removed.
        """

        return self._version_id

    @property
    def subset_id(self):
        return self._subset_id

    @property
    def asset_id(self):
        return self._asset_id

    @property
    def containers(self):
        return list(self._containers_by_id.values())

    def add_container_item(self, item):
        if item.id not in self._containers_by_id:
            self._containers_by_id[item.id] = item


class ContainerItem(object):
    """Container item that have all required data about container.

    Primarily used for UI purposes as prepares all required data.
    """

    def __init__(self, raw_data, group_item):
        self._raw_data = copy.deepcopy(raw_data)
        self._label = raw_data["namespace"]
        # TODO probably some unique name? In scene manager is used:
        #   '{raw_data["representation"]}{raw_data["objectName"]}'
        self._id = str(uuid4())
        self._representation_id = raw_data["representation"]
        self._group_item = group_item

    @property
    def id(self):
        return self._id

    @property
    def asset_id(self):
        return self._group_item.asset_id

    @property
    def label(self):
        return self._label

    @property
    def thumbnail_id(self):
        return self._group_item.thumbnail_id

    @property
    def is_valid(self):
        return self._group_item.is_valid

    @property
    def representation_id(self):
        return self._group_item.representation_id

    @property
    def version_id(self):
        return self._group_item.version_id

    @property
    def raw_data(self):
        """Container data returned from host."""

        return copy.deepcopy(self._raw_data)


class BaseSubsetItem(object):
    _id = None
    asset_name = None
    subset_name = None
    family = None
    author = None
    frames = None
    duration = None
    handles = None
    step = None

    @property
    def id(self):
        if self._id is None:
            self._id = str(uuid4())
        return self._id


class SubsetGroupItem(BaseSubsetItem):
    def __init__(self, asset_name, asset_id):
        self._children_by_id = {}
        self._id = str(asset_id)
        self._label = asset_name
        self._asset_name = asset_name

    @property
    def asset_name(self):
        return self._asset_name

    def __iter__(self):
        for child in self._children_by_id.values():
            yield child

    def get_subset_items(self):
        output = []
        for child in self._children_by_id.values():
            output.extend(child.get_subset_items())
        return output

    def add_children(self, child):
        self._children_by_id[child.id] = child


class SubsetItem(BaseSubsetItem):
    def __init__(
        self,
        versions_model,
        asset_name,
        subset_id,
        subset_name,
        family
    ):
        self._id = str(subset_id)
        self._versions_model = versions_model
        self._asset_name = asset_name
        self._subset_id = subset_id
        self._subset_name = subset_name
        self._family = family

        self._version_items_by_id = {}
        self._current_version_item = None
        self._sorted_versions = None
        self._author = None
        self._publish_time = None

    def get_subset_items(self):
        return [self]

    def add_version(self, version_item):
        self._version_items_by_id[version_item.id] = version_item
        if self._current_version_item is None:
            self._current_version_item = version_item
        # Reset sorted versions
        self._sorted_versions = None

    def _sort_versions(self):
        if self._sorted_versions is not None:
            return

        self._sorted_versions = [
            item.id
            for item in sorted(self._version_items_by_id.values())
        ]

    def get_version_labels_by_id(self):
        self._sort_versions()

        output = []
        for item_id in self._sorted_versions:
            version_item = self._version_items_by_id[item_id]
            output.append((item_id, version_item.label))
        return output

    def set_current_version(self, version_id):
        if version_id not in self._version_items_by_id:
            return
        self._current_version_item = self._version_items_by_id[version_id]

    @property
    def family(self):
        return self._family

    @property
    def subset_name(self):
        return self._subset_name

    @property
    def asset_name(self):
        return self._asset_name

    # Properties looking into current version
    @property
    def author(self):
        if self._current_version_item:
            return self._current_version_item.author

    @property
    def frames(self):
        if self._current_version_item:
            return self._current_version_item.frames

    @property
    def duration(self):
        if self._current_version_item:
            return self._current_version_item.duration

    @property
    def handles(self):
        if self._current_version_item:
            return self._current_version_item.handles

    @property
    def step(self):
        if self._current_version_item:
            return self._current_version_item.step


class VersionItem(object):
    def __init__(self, subset_id, version_id, version, is_hero):
        self._subset_id = subset_id
        self._version_id = version_id
        self._version = version
        self._is_hero = is_hero

        label = "v{:0>3}".format(version)
        if is_hero:
            label = "<{}>".format(label)
        self._label = label

    def __repr__(self):
        return "<{} {} ({})>".format(
            self.__class__.__name__, self.label, self.subset_id
        )

    def __lt__(self, other):
        if not isinstance(other, VersionItem) or self.is_hero:
            return False
        if other.is_hero:
            return True
        return self.version < other.version

    def __gt__(self, other):
        if not isinstance(other, VersionItem) or self.is_hero:
            return True
        if other.is_hero:
            return False
        return self.version > other.version

    def __le__(self, other):
        if self.__lt__(other):
            return True
        return self.__eq__(other)

    def __ge__(self, other):
        if self.__gt__(other):
            return True
        return self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, VersionItem) or self.is_hero != other.is_hero:
            return False
        return self.version == other.version

    @property
    def is_hero(self):
        return self._is_hero

    @property
    def id(self):
        return self._version_id

    @property
    def version(self):
        return self._version

    @property
    def subset_id(self):
        return self._subset_id

    @property
    def label(self):
        return self._label

    @property
    def step(self):
        return None

    @property
    def handles(self):
        return None

    @property
    def duration(self):
        return None

    @property
    def frames(self):
        return None

    @property
    def author(self):
        return None


class AssignerToolSubModel(object):
    def __init__(self, main_model):
        self._main_model = main_model

    @property
    def event_system(self):
        return self._main_model.event_system


class ContainersModel(AssignerToolSubModel):
    _representation_fields = ["_id", "name", "parent", "data.thumbnail_id"]
    _version_fields = [
        "_id",
        "parent",
        "name",
        "type",
        "version_id",
        "data.family",
        "data.families",
        "data.thumbnail_id"
    ]
    _subset_fields = [
        "_id",
        "name",
        "schema",
        "parent",
        "data.family",
        "data.families",
        "data.thumbnail_id"
    ]
    _asset_fields = ["_id", "name", "data.thumbnail_id"]

    def __init__(self, *args, **kwargs):
        super(ContainersModel, self).__init__(*args, **kwargs)

        # Containers data
        self._containers = None
        self._containers_by_id = {}
        self._container_groups = []

    def get_container_groups(self):
        if self._containers is None:
            self._cache_containers()
        return list(self._container_groups)

    def refresh_containers(self):
        # Unset containers and reload them
        self._containers = None
        self._cache_containers()

    def get_available_container_ids(self):
        return set(self._containers_by_id.keys())

    def get_containers_by_id(self, container_ids):
        return [
            self._containers_by_id[container_id]
            for container_id in container_ids
        ]

    def _cache_containers(self):
        """Get containers from host and prepare required information.

        Go through each returned container and find related version ids. Then
        convert them into 'ContainerItem'.
        """

        containers_by_id = {}
        container_groups = []
        self._containers_by_id = containers_by_id
        self._container_groups = container_groups

        # Get containers from host
        host_containers = list(self._main_model.get_host_containers())

        # Get all representation id from containers
        representation_ids = {
            container["representation"]
            for container in host_containers
        }
        project_name = self._main_model.project_name

        # Query representations
        repre_docs = get_representations(
            project_name,
            representation_ids=representation_ids,
            fields=self._representation_fields
        )
        repre_docs_by_id = {
            str(repre_doc["_id"]): repre_doc
            for repre_doc in repre_docs
        }

        # Query versions
        version_docs = get_versions(
            project_name,
            version_ids={
                repre_doc["parent"]
                for repre_doc in repre_docs_by_id.values()
            },
            hero=True,
            fields=self._version_fields
        )
        version_docs_by_id = {
            version_doc["_id"]: version_doc
            for version_doc in version_docs
        }
        version_ids_for_hero = {
            version_doc["version_id"]
            for version_doc in version_docs_by_id.values()
            if version_doc["type"] == "hero_version"
        }
        version_names_for_hero = {}
        if version_ids_for_hero:
            version_docs_hero = get_versions(
                project_name,
                version_ids=version_ids_for_hero,
                fields=["_id", "name"]
            )
            for version_doc_hero in version_docs_hero:
                version_id = version_doc_hero["_id"]
                version_names_for_hero[version_id] = version_doc_hero["name"]

        # Query subsets
        subset_docs = get_subsets(
            project_name,
            subset_ids={
                version_doc["parent"]
                for version_doc in version_docs_by_id.values()
            },
            fields=self._subset_fields
        )
        subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in subset_docs
        }

        # Query assets
        asset_docs = get_assets(
            project_name,
            asset_ids={
                subset_doc["parent"]
                for subset_doc in subset_docs_by_id.values()
            },
            fields=self._asset_fields
        )
        asset_docs_by_id = {
            asset_doc["_id"]: asset_doc
            for asset_doc in asset_docs
        }

        # Store version ids by representation id (converted to string)
        groups_by_repre_id = {}
        for container in host_containers:
            repre_id = container["representation"]
            if repre_id in groups_by_repre_id:
                continue
            repre_doc = repre_docs_by_id.get(repre_id) or {}
            version_id = repre_doc.get("parent")
            version_doc = version_docs_by_id.get(version_id) or {}
            subset_id = version_doc.get("parent")
            subset_doc = subset_docs_by_id.get(subset_id) or {}
            asset_id = subset_doc.get("parent")
            asset_doc = asset_docs_by_id.get(asset_id) or {}
            thumbnail_id = self._extract_thumbnail_id(
                repre_doc, version_doc, subset_doc, asset_doc
            )
            family = self._extract_family(subset_doc, version_doc)
            version = None
            if version_doc:
                if version_doc["type"] != "hero_version":
                    version = version_doc.get("name")
                else:
                    version_id_hero = version_doc.get("version_id")
                    version = version_names_for_hero.get(version_id_hero)

            container_group_item = ContainerGroupItem(
                asset_id,
                asset_doc.get("name"),
                subset_id,
                subset_doc.get("name"),
                family,
                version_id,
                version,
                repre_id,
                repre_doc.get("name"),
                thumbnail_id,
            )
            container_groups.append(container_group_item)
            groups_by_repre_id[repre_id] = container_group_item

        # Create container items
        containers = []
        for container in host_containers:
            repre_id = container["representation"]
            container_group = groups_by_repre_id[repre_id]
            container_item = ContainerItem(container, container_group)
            containers_by_id[container_item.id] = container_item
            containers.append(container_item)
            container_group.add_container_item(container_item)

        self._containers = containers

    def _extract_family(self, subset_doc, version_doc):
        if not subset_doc:
            return None

        maj_version, _ = schema.get_schema_version(subset_doc["schema"])
        if maj_version < 3:
            source_data = version_doc.get("data") or {}
        else:
            source_data = subset_doc.get("data") or {}

        family = source_data.get("family")
        if family:
            return family
        families = source_data.get("families")
        if families:
            return families[0]
        return None

    def _extract_thumbnail_id(
        self, repre_doc, version_doc, subset_doc, asset_doc
    ):
        for doc in (repre_doc, version_doc, subset_doc, asset_doc):
            thumbnail_id = doc.get("data", {}).get("thumbnail_id")
            if thumbnail_id:
                return thumbnail_id
        return None


class VersionsModel(AssignerToolSubModel):
    def __init__(self, *args, **kwargs):
        super(VersionsModel, self).__init__(*args, **kwargs)
        self._asset_ids = set()
        self._items_by_id = {}

    def refresh(self):
        asset_docs = self._main_model.get_asset_docs_by_ids(self._asset_ids)
        subset_docs_by_asset_id = (
            self._main_model.get_subset_docs_by_asset_ids(self._asset_ids)
        )
        subset_ids = set()
        for subset_docs in subset_docs_by_asset_id.values():
            for subset_doc in subset_docs:
                subset_ids.add(subset_doc["_id"])

        version_docs_by_subset_id = (
            self._main_model.get_version_docs_by_subset_ids(subset_ids)
        )

        group_items = []
        subset_items_by_asset_id = {}
        for asset_doc in asset_docs:
            asset_id = asset_doc["_id"]
            asset_name = asset_doc["name"]
            if asset_id not in subset_docs_by_asset_id:
                continue

            for subset_doc in subset_docs_by_asset_id[asset_id]:
                subset_id = subset_doc["_id"]
                subset_name = subset_doc["name"]
                subset_data = subset_doc["data"]
                family = subset_data.get("family")
                if not family:
                    families = subset_data.get("families")
                    if families:
                        family = families[0]


                subset_item = SubsetItem(
                    self,
                    subset_id,
                    subset_name,
                    family
                )
            group_item = SubsetGroupItem(asset_id)
            group_items.append(group_item)



    def set_asset_ids(self, asset_ids):
        if not asset_ids:
            asset_ids = set(asset_ids)
        else:
            asset_ids = set()

        if self._asset_ids == asset_ids:
            return

        self._asset_ids = asset_ids
        self.refresh()


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
        self.set_current_containers({
            container_id
            for container_id in self._current_container_ids
            if container_id in available_container_ids
        })

    def get_container_groups(self):
        return self._containers_model.get_container_groups()

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