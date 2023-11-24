import os
from abc import ABCMeta, abstractmethod

import six
from openpype.style import get_default_entity_icon_color


class WorkfileInfo:
    """Information about workarea file with possible additional from database.

    Args:
        folder_id (str): Folder id.
        task_id (str): Task id.
        filepath (str): Filepath.
        filesize (int): File size.
        creation_time (int): Creation time (timestamp).
        modification_time (int): Modification time (timestamp).
        note (str): Note.
    """

    def __init__(
        self,
        folder_id,
        task_id,
        filepath,
        filesize,
        creation_time,
        modification_time,
        note,
    ):
        self.folder_id = folder_id
        self.task_id = task_id
        self.filepath = filepath
        self.filesize = filesize
        self.creation_time = creation_time
        self.modification_time = modification_time
        self.note = note

    def to_data(self):
        """Converts WorkfileInfo item to data.

        Returns:
            dict[str, Any]: Folder item data.
        """

        return {
            "folder_id": self.folder_id,
            "task_id": self.task_id,
            "filepath": self.filepath,
            "filesize": self.filesize,
            "creation_time": self.creation_time,
            "modification_time": self.modification_time,
            "note": self.note,
        }

    @classmethod
    def from_data(cls, data):
        """Re-creates WorkfileInfo item from data.

        Args:
            data (dict[str, Any]): Workfile info item data.

        Returns:
            WorkfileInfo: Workfile info item.
        """

        return cls(**data)


class FolderItem:
    """Item representing folder entity on a server.

    Folder can be a child of another folder or a project.

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
        """Converts folder item to data.

        Returns:
            dict[str, Any]: Folder item data.
        """

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
        """Re-creates folder item from data.

        Args:
            data (dict[str, Any]): Folder item data.

        Returns:
            FolderItem: Folder item.
        """

        return cls(**data)


class TaskItem:
    """Task item representing task entity on a server.

    Task is child of a folder.

    Task item has label that is used for display in UI. The label is by
        default using task name and type.

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
        """Alias for task_id.

        Returns:
            str: Task id.
        """

        return self.task_id

    @property
    def label(self):
        """Label of task item for UI.

        Returns:
            str: Label of task item.
        """

        if self._label is None:
            self._label = "{} ({})".format(self.name, self.task_type)
        return self._label

    def to_data(self):
        """Converts task item to data.

        Returns:
            dict[str, Any]: Task item data.
        """

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
        """Re-create task item from data.

        Args:
            data (dict[str, Any]): Task item data.

        Returns:
            TaskItem: Task item.
        """

        return cls(**data)


class FileItem:
    """File item that represents a file.

    Can be used for both Workarea and Published workfile. Workarea file
    will always exist on disk which is not the case for Published workfile.

    Args:
        dirpath (str): Directory path of file.
        filename (str): Filename.
        modified (float): Modified timestamp.
        representation_id (Optional[str]): Representation id of published
            workfile.
        filepath (Optional[str]): Prepared filepath.
        exists (Optional[bool]): If file exists on disk.
    """

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
        """Filepath of file.

        Returns:
            str: Full path to a file.
        """

        if self._filepath is None:
            self._filepath = os.path.join(self.dirpath, self.filename)
        return self._filepath

    @property
    def exists(self):
        """File is available.

        Returns:
            bool: If file exists on disk.
        """

        if self._exists is None:
            self._exists = os.path.exists(self.filepath)
        return self._exists

    def to_data(self):
        """Converts file item to data.

        Returns:
            dict[str, Any]: File item data.
        """

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
        """Re-creates file item from data.

        Args:
            data (dict[str, Any]): File item data.

        Returns:
            FileItem: File item.
        """

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
    """Result of workarea file formatting.

    Args:
        root (str): Root path of workarea.
        filename (str): Filename.
        exists (bool): True if file exists.
        filepath (str): Filepath. If not provided it will be constructed
            from root and filename.
    """

    def __init__(self, root, filename, exists, filepath=None):
        if not filepath and root and filename:
            filepath = os.path.join(root, filename)
        self.root = root
        self.filename = filename
        self.exists = exists
        self.filepath = filepath


@six.add_metaclass(ABCMeta)
class AbstractWorkfilesCommon(object):
    @abstractmethod
    def is_host_valid(self):
        """Host is valid for workfiles tool work.

        Returns:
            bool: True if host is valid.
        """

        pass

    @abstractmethod
    def get_workfile_extensions(self):
        """Get possible workfile extensions.

        Defined by host implementation.

        Returns:
            Iterable[str]: List of extensions.
        """

        pass

    @abstractmethod
    def is_save_enabled(self):
        """Is workfile save enabled.

        Returns:
            bool: True if save is enabled.
        """

        pass

    @abstractmethod
    def set_save_enabled(self, enabled):
        """Enable or disabled workfile save.

        Args:
            enabled (bool): Enable save workfile when True.
        """

        pass


class AbstractWorkfilesBackend(AbstractWorkfilesCommon):
    # Current context
    @abstractmethod
    def get_host_name(self):
        """Name of host.

        Returns:
            str: Name of host.
        """
        pass

    @abstractmethod
    def get_current_project_name(self):
        """Project name from current context of host.

        Returns:
            str: Name of project.
        """

        pass

    @abstractmethod
    def get_current_folder_id(self):
        """Folder id from current context of host.

        Returns:
            Union[str, None]: Folder id or None if host does not have
                any context.
        """

        pass

    @abstractmethod
    def get_current_task_name(self):
        """Task name from current context of host.

        Returns:
            Union[str, None]: Task name or None if host does not have
                any context.
        """

        pass

    @abstractmethod
    def get_current_workfile(self):
        """Current workfile from current context of host.

        Returns:
            Union[str, None]: Path to workfile or None if host does
                not have opened specific file.
        """

        pass

    @property
    @abstractmethod
    def project_anatomy(self):
        """Project anatomy for current project.

        Returns:
            Anatomy: Project anatomy.
        """

        pass

    @property
    @abstractmethod
    def project_settings(self):
        """Project settings for current project.

        Returns:
            dict[str, Any]: Project settings.
        """

        pass

    @abstractmethod
    def get_project_entity(self, project_name):
        """Get project entity by name.

        Args:
            project_name (str): Project name.

        Returns:
            dict[str, Any]: Project entity data.
        """

        pass

    @abstractmethod
    def get_folder_entity(self, project_name, folder_id):
        """Get folder entity by id.

        Args:
            project_name (str): Project name.
            folder_id (str): Folder id.

        Returns:
            dict[str, Any]: Folder entity data.
        """

        pass

    @abstractmethod
    def get_task_entity(self, project_name, task_id):
        """Get task entity by id.

        Args:
            project_name (str): Project name.
            task_id (str): Task id.

        Returns:
            dict[str, Any]: Task entity data.
        """

        pass

    def emit_event(self, topic, data=None, source=None):
        """Emit event.

        Args:
            topic (str): Event topic used for callbacks filtering.
            data (Optional[dict[str, Any]]): Event data.
            source (Optional[str]): Event source.
        """

        pass


class AbstractWorkfilesFrontend(AbstractWorkfilesCommon):
    """UI controller abstraction that is used for workfiles tool frontend.

    Abstraction to provide data for UI and to handle UI events.

    Provide access to abstract backend data, like folders and tasks. Cares
    about handling of selection, keep information about current UI selection
    and have ability to tell what selection should UI show.

    Selection is separated into 2 parts, first is what UI elements tell
    about selection, and second is what UI should show as selected.
    """

    @abstractmethod
    def register_event_callback(self, topic, callback):
        """Register event callback.

        Listen for events with given topic.

        Args:
            topic (str): Name of topic.
            callback (Callable): Callback that will be called when event
                is triggered.
        """

        pass

    # Host information
    @abstractmethod
    def get_workfile_extensions(self):
        """Each host can define extensions that can be used for workfile.

        Returns:
            List[str]: File extensions that can be used as workfile for
                current host.
        """

        pass

    # Selection information
    @abstractmethod
    def get_selected_folder_id(self):
        """Currently selected folder id.

        Returns:
            Union[str, None]: Folder id or None if no folder is selected.
        """

        pass

    @abstractmethod
    def set_selected_folder(self, folder_id):
        """Change selected folder.

        This deselects currently selected task.

        Args:
            folder_id (Union[str, None]): Folder id or None if no folder
                is selected.
        """

        pass

    @abstractmethod
    def get_selected_task_id(self):
        """Currently selected task id.

        Returns:
            Union[str, None]: Task id or None if no folder is selected.
        """

        pass

    @abstractmethod
    def get_selected_task_name(self):
        """Currently selected task name.

        Returns:
            Union[str, None]: Task name or None if no folder is selected.
        """

        pass

    @abstractmethod
    def set_selected_task(self, task_id, task_name):
        """Change selected task.

        Args:
            task_id (Union[str, None]): Task id or None if no task
                is selected.
            task_name (Union[str, None]): Task name or None if no task
                is selected.
        """

        pass

    @abstractmethod
    def get_selected_workfile_path(self):
        """Currently selected workarea workile.

        Returns:
            Union[str, None]: Selected workfile path.
        """

        pass

    @abstractmethod
    def set_selected_workfile_path(self, path):
        """Change selected workfile path.

        Args:
            path (Union[str, None]): Selected workfile path.
        """

        pass

    @abstractmethod
    def get_selected_representation_id(self):
        """Currently selected workfile representation id.

        Returns:
            Union[str, None]: Representation id or None if no representation
                is selected.
        """

        pass

    @abstractmethod
    def set_selected_representation_id(self, representation_id):
        """Change selected representation.

        Args:
            representation_id (Union[str, None]): Selected workfile
                representation id.
        """

        pass

    def get_selected_context(self):
        """Obtain selected context.

        Returns:
            dict[str, Union[str, None]]: Selected context.
        """

        return {
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
    def set_expected_selection(
        self,
        folder_id,
        task_name,
        workfile_name=None,
        representation_id=None
    ):
        """Define what should be selected in UI.

        Expected selection provide a way to define/change selection of
        sequential UI elements. For example, if folder and task should be
        selected a task element should wait until folder element has selected
        folder.

        Triggers 'expected_selection.changed' event.

        Args:
            folder_id (str): Folder id.
            task_name (str): Task name.
            workfile_name (Optional[str]): Workfile name. Used for workarea
                files UI element.
            representation_id (Optional[str]): Representation id. Used for
                published filed UI element.
        """

        pass

    @abstractmethod
    def get_expected_selection_data(self):
        """Data of expected selection.

        TODOs:
            Return defined object instead of dict.

        Returns:
            dict[str, Any]: Expected selection data.
        """

        pass

    @abstractmethod
    def expected_folder_selected(self, folder_id):
        """Expected folder was selected in UI.

        Args:
            folder_id (str): Folder id which was selected.
        """

        pass

    @abstractmethod
    def expected_task_selected(self, folder_id, task_name):
        """Expected task was selected in UI.

        Args:
            folder_id (str): Folder id under which task is.
            task_name (str): Task name which was selected.
        """

        pass

    @abstractmethod
    def expected_representation_selected(
        self, folder_id, task_name, representation_id
    ):
        """Expected representation was selected in UI.

        Args:
            folder_id (str): Folder id under which representation is.
            task_name (str): Task name under which representation is.
            representation_id (str): Representation id which was selected.
        """

        pass

    @abstractmethod
    def expected_workfile_selected(self, folder_id, task_name, workfile_name):
        """Expected workfile was selected in UI.

        Args:
            folder_id (str): Folder id under which workfile is.
            task_name (str): Task name under which workfile is.
            workfile_name (str): Workfile filename which was selected.
        """

        pass

    @abstractmethod
    def go_to_current_context(self):
        """Set expected selection to current context."""

        pass

    # Model functions
    @abstractmethod
    def get_folder_items(self, project_name, sender):
        """Folder items to visualize project hierarchy.

        This function may trigger events 'folders.refresh.started' and
        'folders.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of folder items in UI elements.

        Args:
            project_name (str): Project name for which are folders requested.
            sender (str): Who requested folder items.

        Returns:
            list[FolderItem]: Minimum possible information needed
                for visualisation of folder hierarchy.
        """

        pass

    @abstractmethod
    def get_task_items(self, project_name, folder_id, sender):
        """Task items.

        This function may trigger events 'tasks.refresh.started' and
        'tasks.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of task items in UI elements.

        Args:
            project_name (str): Project name for which are tasks requested.
            folder_id (str): Folder ID for which are tasks requested.
            sender (str): Who requested folder items.

        Returns:
            list[TaskItem]: Minimum possible information needed
                for visualisation of tasks.
        """

        pass

    @abstractmethod
    def has_unsaved_changes(self):
        """Has host unsaved change in currently running session.

        Returns:
            bool: Has unsaved changes.
        """

        pass

    @abstractmethod
    def get_workarea_dir_by_context(self, folder_id, task_id):
        """Get workarea directory by context.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.

        Returns:
            str: Workarea directory.
        """

        pass

    @abstractmethod
    def get_workarea_file_items(self, folder_id, task_id):
        """Get workarea file items.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.

        Returns:
            list[FileItem]: List of workarea file items.
        """

        pass

    @abstractmethod
    def get_workarea_save_as_data(self, folder_id, task_id):
        """Prepare data for Save As operation.

        Todos:
            Return defined object instead of dict.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.

        Returns:
            dict[str, Any]: Data for Save As operation.
        """

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
        """Calculate workfile path for passed context.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.
            extension (str): File extension.
            use_last_version (bool): Use last version.
            version (int): Version used if 'use_last_version' if 'False'.
            comment (str): User's comment (subversion).

        Returns:
            WorkareaFilepathResult: Result of the operation.
        """

        pass

    @abstractmethod
    def get_published_file_items(self, folder_id, task_id):
        """Get published file items.

        Args:
            folder_id (str): Folder id.
            task_id (Union[str, None]): Task id.

        Returns:
            list[FileItem]: List of published file items.
        """

        pass

    @abstractmethod
    def get_workfile_info(self, folder_id, task_id, filepath):
        """Workfile info from database.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.
            filepath (str): Workfile path.

        Returns:
            Union[WorkfileInfo, None]: Workfile info or None if was passed
                invalid context.
        """

        pass

    @abstractmethod
    def save_workfile_info(self, folder_id, task_id, filepath, note):
        """Save workfile info to database.

        At this moment the only information which can be saved about
            workfile is 'note'.

        When 'note' is 'None' it is only validated if workfile info exists,
            and if not then creates one with empty note.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.
            filepath (str): Workfile path.
            note (Union[str, None]): Note.
        """

        pass

    # General commands
    @abstractmethod
    def reset(self):
        """Reset everything, models, ui etc.

        Triggers 'controller.reset.started' event at the beginning and
        'controller.reset.finished' at the end.
        """

        pass

    # Controller actions
    @abstractmethod
    def open_workfile(self, folder_id, task_id, filepath):
        """Open a workfile for context.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.
            filepath (str): Workfile path.
        """

        pass

    @abstractmethod
    def save_current_workfile(self):
        """Save state of current workfile."""

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
        """Save current state of workfile to workarea.

        Args:
            folder_id (str): Folder id.
            task_id (str): Task id.
            workdir (str): Workarea directory.
            filename (str): Workarea filename.
            template_key (str): Template key used to get the workdir
                and filename.
        """

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
        """Action to copy published workfile representation to workarea.

        Triggers 'copy_representation.started' event on start and
        'copy_representation.finished' event with '{"failed": bool}'.

        Args:
            representation_id (str): Representation id.
            representation_filepath (str): Path to representation file.
            folder_id (str): Folder id.
            task_id (str): Task id.
            workdir (str): Workarea directory.
            filename (str): Workarea filename.
            template_key (str): Template key.
        """

        pass

    @abstractmethod
    def duplicate_workfile(self, src_filepath, workdir, filename):
        """Duplicate workfile.

        Workfiles is not opened when done.

        Args:
            src_filepath (str): Source workfile path.
            workdir (str): Destination workdir.
            filename (str): Destination filename.
        """

        pass
