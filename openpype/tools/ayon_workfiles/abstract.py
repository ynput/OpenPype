from abc import ABCMeta, abstractmethod

import six


@six.add_metaclass(ABCMeta)
class AbstractWorkfileController(object):
    @property
    @abstractmethod
    def log(self):
        """Controller's logger object.

        Returns:
            logging.Logger: Logger object that can be used for logging.
        """

        pass

    @property
    @abstractmethod
    def event_system(self):
        """Inner event system for publisher controller."""

        pass

    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self.event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self.event_system.add_callback(topic, callback)

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

    @property
    @abstractmethod
    def project_anatomy(self):
        """Anatomy object for current project.

        Todos:
            Rename to 'project_anatomy'.

        Returns:
            Anatomy: Project anatomy.
        """
        pass

    @abstractmethod
    def get_current_folder_id(self):
        pass

    @abstractmethod
    def get_current_task_name(self):
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
    def set_expected_folder_id(self, folder_id):
        pass

    @abstractmethod
    def set_expected_task_name(self, task_name):
        pass

    @abstractmethod
    def get_expected_folder_id(self):
        pass

    @abstractmethod
    def get_expected_task_name(self):
        pass

    @abstractmethod
    def go_to_current_context(self):
        pass

    # Model functions
    @abstractmethod
    def get_folder_items(self):
        pass

    @abstractmethod
    def get_task_items(self, folder_id):
        pass

    @abstractmethod
    def get_workarea_dir_by_context(self, folder_id, task_id):
        pass

    @abstractmethod
    def get_workarea_file_items(self, folder_id, task_id):
        pass

    @abstractmethod
    def get_published_file_items(self, folder_id):
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
