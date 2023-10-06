from abc import ABCMeta, abstractmethod
import six


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


class ProductItem:
    def __init__(
        self,
        product_id,
        product_type,
        product_name,
        product_icon,
        product_type_icon,
        product_in_scene,
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
        self.product_in_scene = product_in_scene
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
            "product_in_scene": self.product_in_scene,
            "group_name": self.group_name,
            "folder_id": self.folder_id,
            "folder_label": self.folder_label,
            "version_items": {
                version_id: version_item.to_data()
                for version_id, version_item in self.version_items.items()
            },
        }

    @classmethod
    def from_data(cls, data):
        version_items = {
            version_id: VersionItem.from_data(version)
            for version_id, version in data["version_items"].items()
        }
        data["version_items"] = version_items
        return cls(**data)


class VersionItem:
    def __init__(
        self,
        version_id,
        version,
        is_hero,
        product_id,
        thumbnail_id,
        published_time,
        author,
        frame_range,
        duration,
        handles,
        step,
        comment,
        source
    ):
        self.version_id = version_id
        self.product_id = product_id
        self.thumbnail_id = thumbnail_id
        self.version = version
        self.is_hero = is_hero
        self.published_time = published_time
        self.author = author
        self.frame_range = frame_range
        self.duration = duration
        self.handles = handles
        self.step = step
        self.comment = comment
        self.source = source

    def __eq__(self, other):
        if not isinstance(other, VersionItem):
            return False
        return (
            self.is_hero == other.is_hero
            and self.version == other.version
            and self.version_id == other.version_id
            and self.product_id == other.product_id
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
            "product_id": self.product_id,
            "thumbnail_id": self.thumbnail_id,
            "version": self.version,
            "is_hero": self.is_hero,
            "published_time": self.published_time,
            "author": self.author,
            "frame_range": self.frame_range,
            "duration": self.duration,
            "handles": self.handles,
            "step": self.step,
            "comment": self.comment,
            "source": self.source,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class RepreItem:
    def __init__(
        self,
        representation_id,
        representation_name,
        representation_icon,
        product_name,
        folder_label,
    ):
        self.representation_id = representation_id
        self.representation_name = representation_name
        self.representation_icon = representation_icon
        self.product_name = product_name
        self.folder_label = folder_label

    def to_data(self):
        return {
            "representation_id": self.representation_id,
            "representation_name": self.representation_name,
            "representation_icon": self.representation_icon,
            "product_name": self.product_name,
            "folder_label": self.folder_label,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


@six.add_metaclass(ABCMeta)
class AbstractController:

    @abstractmethod
    def emit_event(self, topic, data=None, source=None):
        pass

    @abstractmethod
    def register_event_callback(self, topic, callback):
        pass

    @abstractmethod
    def reset(self):
        pass

    # Model wrapper calls
    @abstractmethod
    def get_project_items(self):
        pass

    @abstractmethod
    def get_folder_items(self, project_name, sender=None):
        pass

    @abstractmethod
    def get_product_items(self, project_name, folder_ids, sender=None):
        pass

    @abstractmethod
    def get_product_item(self, project_name, product_id):
        """

        Args:
            project_name (str): Project name.
            product_id (str): Product id.

        Returns:
             Union[ProductItem, None]: Product info or None if not found.
        """

        pass

    @abstractmethod
    def get_product_type_items(self, project_name):
        pass

    @abstractmethod
    def get_representation_items(
        self, project_name, version_ids, sender=None
    ):
        pass

    @abstractmethod
    def get_folder_entity(self, project_name, folder_id):
        pass

    @abstractmethod
    def get_version_thumbnail_ids(self, project_name, version_ids):
        pass

    @abstractmethod
    def get_folder_thumbnail_ids(self, project_name, folder_ids):
        pass

    @abstractmethod
    def get_thumbnail_path(self, project_name, thumbnail_id):
        pass

    # Load action items
    @abstractmethod
    def get_versions_action_items(self, project_name, version_ids):
        pass

    @abstractmethod
    def get_representations_action_items(
        self, project_name, representation_ids
    ):
        pass

    @abstractmethod
    def trigger_action_item(
        self,
        identifier,
        options,
        project_name,
        version_ids,
        representation_ids
    ):
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

    @abstractmethod
    def get_selected_version_ids(self):
        pass

    @abstractmethod
    def set_selected_versions(self, version_ids):
        pass

    @abstractmethod
    def get_selected_representation_ids(self):
        pass

    @abstractmethod
    def set_selected_representations(self, repre_ids):
        pass

    @abstractmethod
    def fill_root_in_source(self, source):
        pass

    @abstractmethod
    def get_current_context(self):
        """Current context is a context of the current scene.

        Example output:
            {
                "project_name": "MyProject",
                "folder_id": "0011223344-5566778-99",
                "task_name": "Compositing",
            }

        Returns:
            dict[str, Union[str, None]]: Context data.
        """

        pass

    @abstractmethod
    def is_loaded_products_supported(self):
        """Is capable to get information about loaded products.

        Returns:
            bool: True if it is supported.
        """

        pass

    @abstractmethod
    def get_loaded_product_ids(self):
        """Return set of loaded product ids.

        Returns:
            set[str]: Set of loaded product ids.
        """

        pass
