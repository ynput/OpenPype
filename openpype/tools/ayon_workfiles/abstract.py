import os
from abc import ABCMeta, abstractmethod

import six


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
