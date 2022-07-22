import collections

from .common import AssignerToolSubModel


class SubsetItem(object):
    def __init__(
        self,
        versions_model,
        asset_id,
        asset_name,
        subset_id,
        subset_name,
        family,
        subset_group,
    ):
        self._id = str(subset_id)
        self._versions_model = versions_model
        self._asset_id = asset_id
        self._asset_name = asset_name
        self._subset_id = subset_id
        self._subset_name = subset_name
        self._family = family
        self._subset_group = subset_group

        self._version_items_by_id = {}
        self._current_version_item = None
        self._sorted_versions = None

    @property
    def id(self):
        return self._id

    def get_subset_items(self):
        return [self]

    def add_version(self, version_item):
        self._version_items_by_id[version_item.id] = version_item
        if self._current_version_item is None:
            self._current_version_item = version_item
        # Reset sorted versions
        self._sorted_versions = None

    def _sort_versions(self):
        if self._sorted_versions is None:
            sorted_versions = reversed(sorted(
                self._version_items_by_id.values()
            ))
            self._sorted_versions = [
                item.id
                for item in sorted_versions
            ]

    def get_version_by_id(self, version_id):
        return self._version_items_by_id[version_id]

    def get_sorted_versions(self):
        self._sort_versions()

        return [
            self._version_items_by_id[item_id]
            for item_id in self._sorted_versions
        ]

    @property
    def family(self):
        return self._family

    @property
    def subset_name(self):
        return self._subset_name

    @property
    def asset_name(self):
        return self._asset_name

    @property
    def asset_id(self):
        return self._asset_id


class VersionItem(object):
    def __init__(
        self,
        subset_id,
        version_id,
        version,
        is_hero,
        version_data
    ):
        self._subset_id = subset_id
        self._version_id = version_id
        self._version = version
        self._is_hero = is_hero

        self._author = version_data.get("author")
        self._time = version_data.get("time")
        self._step = version_data.get("step")
        self._thumbnail_id = version_data.get("thumbnail_id")

        frame_start = version_data.get("frameStart")
        frame_end = version_data.get("frameEnd")

        handle_start = version_data.get("handleStart")
        handle_end = version_data.get("handleEnd")

        handles = None
        frames = None
        duration = None
        if handle_start is not None and handle_end is not None:
            handles = "{}-{}".format(str(handle_start), str(handle_end))

        if frame_start is not None and frame_end is not None:
            # Remove superfluous zeros from numbers (3.0 -> 3) to improve
            # readability for most frame ranges
            frame_start = int(frame_start)
            frame_end = int(frame_end)
            frames = "{0}-{1}".format(frame_start, frame_end)
            duration = frame_end - frame_start + 1

        self._handles = handles
        self._duration = duration
        self._frames = frames

        label = "v{:0>3}".format(version)
        if is_hero:
            label = "[{}]".format(label)
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
        return self._step

    @property
    def handles(self):
        return self._handles

    @property
    def duration(self):
        return self._duration

    @property
    def frames(self):
        return self._frames

    @property
    def author(self):
        return self._author

    @property
    def time(self):
        return self._time

    @property
    def thumbnail_id(self):
        return self._thumbnail_id


class VersionsModel(AssignerToolSubModel):
    def __init__(self, *args, **kwargs):
        super(VersionsModel, self).__init__(*args, **kwargs)
        self._asset_ids = set()
        self._subset_items = []
        self._thumbnail_id_by_version_id = {}

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

        subset_items = []
        thumbnail_id_by_version_id = {}
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
                    version_data = {}
                    if not is_hero:
                        version = version_doc["name"]
                        version_data = version_doc["data"]
                    else:
                        version_id = version_doc["version_id"]
                        versioned_doc = versions_docs_by_id.get(version_id)
                        if versioned_doc:
                            version = versioned_doc["name"]
                            version_data = versioned_doc["data"]

                    if version is not None:
                        version_item = VersionItem(
                            subset_id,
                            version_doc["_id"],
                            version,
                            is_hero,
                            version_data
                        )
                        thumbnail_id_by_version_id[version_item.id] = (
                            version_item.thumbnail_id
                        )
                        version_items.append(version_item)

                if not version_items:
                    continue

                subset_group = subset_data.get("subsetGroup")
                subset_item = SubsetItem(
                    self,
                    asset_id,
                    asset_name,
                    subset_id,
                    subset_name,
                    family,
                    subset_group
                )
                subset_items_by_asset_id[asset_id].append(subset_item)

                for version_item in version_items:
                    subset_item.add_version(version_item)

                subset_items.append(subset_item)

        self._subset_items = subset_items
        self._thumbnail_id_by_version_id = thumbnail_id_by_version_id

        self.event_system.emit("versions.refresh.finished")

    def get_thumbnail_ids_for_version_ids(self, version_ids):
        return [
            self._thumbnail_id_by_version_id.get(version_id)
            for version_id in version_ids
        ]

    def get_subset_items(self):
        return list(self._subset_items)

    def set_asset_ids(self, asset_ids):
        if asset_ids:
            asset_ids = set(asset_ids)
        else:
            asset_ids = set()

        if self._asset_ids != asset_ids:
            self._asset_ids = asset_ids
            self.refresh()
