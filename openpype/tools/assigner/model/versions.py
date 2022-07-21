import collections
from uuid import uuid4

from .common import AssignerToolSubModel


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


class VersionsModel(AssignerToolSubModel):
    def __init__(self, *args, **kwargs):
        super(VersionsModel, self).__init__(*args, **kwargs)
        self._asset_ids = set()
        self._group_items = []

    def refresh(self):
        self.event_system.emit("versions.refresh.started")

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
        subset_items_by_asset_id = collections.defaultdict(list)
        for asset_doc in asset_docs:
            asset_id = asset_doc["_id"]
            asset_name = asset_doc["name"]
            if asset_id not in subset_docs_by_asset_id:
                continue

            for subset_doc in subset_docs_by_asset_id[asset_id]:
                subset_id = subset_doc["_id"]
                versions_docs = version_docs_by_subset_id.get(subset_id)
                if not versions_docs:
                    continue

                subset_name = subset_doc["name"]
                subset_data = subset_doc["data"]
                family = subset_data.get("family")
                if not family:
                    families = subset_data.get("families")
                    if families:
                        family = families[0]

                versions_docs_by_id = {
                    version_doc["_id"]: version_doc
                    for version_doc in versions_docs
                }

                version_items = []
                for version_doc in versions_docs:
                    is_hero = version_doc["type"] == "hero_version"
                    version = None
                    if not is_hero:
                        version = version_doc["name"]
                    else:
                        version_id = version_doc["version_id"]
                        versioned_doc = versions_docs_by_id.get(version_id)
                        if versioned_doc:
                            version = versioned_doc["name"]

                    if version is not None:
                        version_item = VersionItem(
                            subset_id, version_doc["_id"], version, is_hero
                        )
                        version_items.append(version_item)

                if not version_items:
                    continue

                subset_item = SubsetItem(
                    self,
                    asset_name,
                    subset_id,
                    subset_name,
                    family
                )
                subset_items_by_asset_id[asset_id].append(subset_item)

                for version_item in version_items:
                    subset_item.add_version(version_item)

            for subset_items in subset_items_by_asset_id.values():
                group_item = SubsetGroupItem(asset_name, asset_id)
                group_items.append(group_item)

                for subset_item in subset_items:
                    group_item.add_children(subset_item)

        self._group_items = group_items

        self.event_system.emit("versions.refresh.finished")

    def get_subset_items(self):
        output = []
        for group_item in self._group_items:
            output.extend(group_item)
        return output

    def get_group_items(self):
        return list(self._group_items)

    def set_asset_ids(self, asset_ids):
        if asset_ids:
            asset_ids = set(asset_ids)
        else:
            asset_ids = set()

        if self._asset_ids != asset_ids:
            self._asset_ids = asset_ids
            self.refresh()
