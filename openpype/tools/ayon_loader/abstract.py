from abc import ABCMeta, abstractmethod
import six


class VersionItem:
    def __init__(
        self,
        version_id,
        version,
        is_hero,
        subset_id,
        thumbnail_id,
        published_time,
        author,
        frame_range,
        duration,
        handles,
        step,
        in_scene
    ):
        self.version_id = version_id
        self.subset_id = subset_id
        self.thumbnail_id = thumbnail_id
        self.version = version
        self.is_hero = is_hero
        self.published_time = published_time
        self.author = author
        self.frame_range = frame_range
        self.duration = duration
        self.handles = handles
        self.step = step
        self.in_scene = in_scene

    def __eq__(self, other):
        if not isinstance(other, VersionItem):
            return False
        return (
            self.is_hero == other.is_hero
            and self.version == other.version
            and self.version_id == other.version_id
            and self.subset_id == other.subset_id
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if not isinstance(other, VersionItem):
            return False
        if (
            other.version == self.version
            and self.is_hero
        ):
            return True
        return other.version < self.version

    def to_data(self):
        return {
            "version_id": self.version_id,
            "subset_id": self.subset_id,
            "thumbnail_id": self.thumbnail_id,
            "version": self.version,
            "is_hero": self.is_hero,
            "published_time": self.published_time,
            "author": self.author,
            "frame_range": self.frame_range,
            "duration": self.duration,
            "handles": self.handles,
            "step": self.step,
            "in_scene": self.in_scene,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class ProductItem:
    def __init__(
        self,
        product_id,
        product_type,
        product_name,
        product_icon,
        product_type_icon,
        group_name,
        folder_id,
        folder_label,
        version_items,
    ):
        self.product_id = product_id
        self.product_type = product_type
        self.product_name = product_name
        self.product_icon = product_icon
        self.product_type_icon = product_type_icon
        self.group_name = group_name
        self.folder_id = folder_id
        self.folder_label = folder_label
        self.version_items = version_items

    def to_data(self):
        return {
            "product_id": self.product_id,
            "product_type": self.product_type,
            "product_name": self.product_name,
            "product_icon": self.product_icon,
            "product_type_icon": self.product_type_icon,
            "group_name": self.group_name,
            "folder_id": self.folder_id,
            "folder_label": self.folder_label,
            "version_items": [
                version_item.to_data()
                for version_item in self.version_items
            ],
        }

    @classmethod
    def from_data(cls, data):
        version_items = [
            VersionItem.from_data(version)
            for version in data["version_items"]
        ]
        data["version_items"] = version_items
        return cls(**data)


class ProductTypeItem:
    def __init__(self, name, icon, checked):
        self.name = name
        self.icon = icon
        self.checked = checked

    def to_data(self):
        return {
            "name": self.name,
            "icon": self.icon,
            "checked": self.checked,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


@six.add_metaclass(ABCMeta)
class AbstractController:
    @abstractmethod
    def get_current_project(self):
        pass

    @abstractmethod
    def reset(self):
        pass

    # Model wrapper calls
    @abstractmethod
    def get_project_items(self):
        pass

    @abstractmethod
    def get_product_type_items(self, project_name):
        pass

    # Selection model wrapper calls
    @abstractmethod
    def get_selected_project_name(self):
        pass

    @abstractmethod
    def set_selected_project(self, project_name):
        pass

    @abstractmethod
    def get_selected_folder_ids(self):
        pass

    @abstractmethod
    def set_selected_folders(self, folder_ids):
        pass
