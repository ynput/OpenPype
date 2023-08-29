import os
from abc import ABCMeta, abstractmethod

import six
from openpype.style import get_default_entity_icon_color


class FolderItem:
    """

    Args:
        entity_id (str): Folder id.
        parent_id (Union[str, None]): Parent folder id. If 'None' then project
            is parent.
        name (str): Name of folder.
        label (str): Folder label.
        icon_name (str): Name of icon from font awesome.
        icon_color (str): Hex color string that will be used for icon.
    """

    def __init__(
        self, entity_id, parent_id, name, label, icon_name, icon_color
    ):
        self.entity_id = entity_id
        self.parent_id = parent_id
        self.name = name
        self.icon_name = icon_name or "fa.folder"
        self.icon_color = icon_color or get_default_entity_icon_color()
        self.label = label or name

    def to_data(self):
        return {
            "entity_id": self.entity_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "label": self.label,
            "icon_name": self.icon_name,
            "icon_color": self.icon_color,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class TaskItem:
    """

    Args:
        task_id (str): Task id.
        name (str): Name of task.
        task_type (str): Type of task.
        parent_id (str): Parent folder id.
        icon_name (str): Name of icon from font awesome.
        icon_color (str): Hex color string that will be used for icon.
    """

    def __init__(
        self, task_id, name, task_type, parent_id, icon_name, icon_color
    ):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.parent_id = parent_id
        self.icon_name = icon_name or "fa.male"
        self.icon_color = icon_color or get_default_entity_icon_color()
        self._label = None

    @property
    def id(self):
        return self.task_id

    @property
    def label(self):
        if self._label is None:
            self._label = "{} ({})".format(self.name, self.task_type)
        return self._label

    def to_data(self):
        return {
            "task_id": self.task_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "task_type": self.task_type,
            "icon_name": self.icon_name,
            "icon_color": self.icon_color,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class FileItem:
    def __init__(
        self,
        dirpath,
        filename,
        modified,
        representation_id=None,
        filepath=None,
        exists=None
    ):
        self.filename = filename
        self.dirpath = dirpath
        self.modified = modified
        self.representation_id = representation_id
        self._filepath = filepath
        self._exists = exists

    @property
    def filepath(self):
        if self._filepath is None:
            self._filepath = os.path.join(self.dirpath, self.filename)
        return self._filepath

    @property
    def exists(self):
        if self._exists is None:
            self._exists = os.path.exists(self.filepath)
        return self._exists

    def to_data(self):
        return {
            "filename": self.filename,
            "dirpath": self.dirpath,
            "modified": self.modified,
            "representation_id": self.representation_id,
            "filepath": self.filepath,
            "exists": self.exists,
        }

    @classmethod
    def from_data(cls, data):
        required_keys = {
            "filename",
            "dirpath",
            "modified",
            "representation_id"
        }
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise KeyError("Missing keys: {}".format(missing_keys))

        return cls(**{
            key: data[key]
            for key in required_keys
        })


class WorkareaFilepathResult:
    def __init__(self, root, filename, exists, filepath=None):
        if not filepath and root and filename:
            filepath = os.path.join(root, filename)
        self.root = root
        self.filename = filename
        self.exists = exists
        self.filepath = filepath


@six.add_metaclass(ABCMeta)
class AbstractWorkfileController(object):
    # Host information
    @abstractmethod
    def get_workfile_extensions(self):
        """
        Returns:
            List[str]: File extensions that can be used as workfile for
                current host.
        """
        pass

    # Current context
    @abstractmethod
    def get_host_name(self):
        pass

    @abstractmethod
    def get_current_project_name(self):
        pass

    @abstractmethod
    def get_current_folder_id(self):
        pass

    @abstractmethod
    def get_current_task_name(self):
        pass

    @abstractmethod
    def get_current_workfile(self):
        pass

    # Selection information
    @abstractmethod
    def get_selected_folder_id(self):
        pass

    @abstractmethod
    def set_selected_folder(self, folder_id):
        pass

    @abstractmethod
    def get_selected_task_id(self):
        pass

    @abstractmethod
    def get_selected_task_name(self):
        pass

    @abstractmethod
    def set_selected_task(self, folder_id, task_id, task_name):
        pass

    @abstractmethod
    def get_selected_workfile_path(self):
        pass

    @abstractmethod
    def set_selected_workfile_path(self, path):
        pass

    @abstractmethod
    def get_selected_representation_id(self):
        pass

    @abstractmethod
    def set_selected_representation_id(self, representation_id):
        pass

    def get_selected_context(self):
        return {
            "project_name": self.get_current_project_name(),
            "folder_id": self.get_selected_folder_id(),
            "task_id": self.get_selected_task_id(),
            "task_name": self.get_selected_task_name(),
            "workfile_path": self.get_selected_workfile_path(),
            "representation_id": self.get_selected_representation_id(),
        }

    # Expected selection
    # - expected selection is used to restore selection after refresh
    #   or when current context should be used
    @abstractmethod
    def set_expected_selection(self, folder_id, task_name):
        pass

    @abstractmethod
    def get_expected_selection_data(self):
        pass

    @abstractmethod
    def go_to_current_context(self):
        pass

    # Model functions
    @abstractmethod
    def get_folder_items(self, sender):
        """Folder items to visualize project hierarchy.

        This function may trigger events 'folders.refresh.started' and
        'folders.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of folder items in UI elements.

        Args:
            sender (str): Who requested folder items.

        Returns:
            list[FolderItem]: Minimum possible information needed
                for visualisation of folder hierarchy.
        """

        pass

    @abstractmethod
    def get_task_items(self, folder_id, sender):
        """Task items.

        This function may trigger events 'tasks.refresh.started' and
        'tasks.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of task items in UI elements.

        Args:
            folder_id (str): Folder ID for which are tasks requested.
            sender (str): Who requested folder items.

        Returns:
            list[TaskItem]: Minimum possible information needed
                for visualisation of tasks.
        """

        pass

    @abstractmethod
    def has_unsaved_changes(self):
        pass

    @abstractmethod
    def get_workarea_dir_by_context(self, folder_id, task_id):
        pass

    @abstractmethod
    def get_workarea_file_items(self, folder_id, task_id):
        pass

    @abstractmethod
    def get_workarea_save_as_data(self, folder_id, task_id):
        pass

    @abstractmethod
    def fill_workarea_filepath(
        self,
        folder_id,
        task_id,
        extension,
        use_last_version,
        version,
        comment,
    ):
        """

        Returns:
            WorkareaFilepathResult: Result of the operation.
        """
        pass

    @abstractmethod
    def get_published_file_items(self, folder_id, task_id):
        pass

    @abstractmethod
    def get_workfile_info(self, folder_id, task_id, filepath):
        pass

    @abstractmethod
    def save_workfile_info(self, folder_id, task_id, filepath, note):
        pass

    # General commands
    @abstractmethod
    def refresh(self):
        pass

    # Controller actions
    @abstractmethod
    def open_workfile(self, filepath):
        pass

    @abstractmethod
    def save_current_workfile(self):
        pass

    @abstractmethod
    def save_as_workfile(
        self,
        folder_id,
        task_id,
        workdir,
        filename,
        template_key,
    ):
        pass

    @abstractmethod
    def copy_workfile_representation(
        self,
        representation_id,
        representation_filepath,
        folder_id,
        task_id,
        workdir,
        filename,
        template_key,
    ):
        pass
