from abc import ABCMeta, abstractmethod

import six


@six.add_metaclass(ABCMeta)
class AbstractLauncherCommon(object):
    @abstractmethod
    def register_event_callback(self, topic, callback):
        pass


class AbstractLauncherBackend(AbstractLauncherCommon):
    @abstractmethod
    def emit_event(self, topic, data=None, source=None):
        pass

    @abstractmethod
    def get_project_settings(self, project_name):
        pass

    @abstractmethod
    def get_project_entity(self, project_name):
        pass

    @abstractmethod
    def get_folder_entity(self, project_name, folder_id):
        pass

    @abstractmethod
    def get_task_entity(self, project_name, task_id):
        pass


class AbstractLauncherFrontEnd(AbstractLauncherCommon):
    # Entity items for UI
    @abstractmethod
    def get_project_items(self, sender=None):
        pass

    @abstractmethod
    def get_folder_items(self, project_name, sender=None):
        pass

    @abstractmethod
    def get_task_items(self, project_name, folder_id, sender=None):
        pass

    @abstractmethod
    def get_selected_project_name(self):
        """Selected project name.

        Returns:
            str: Selected project name.
        """

        pass

    @abstractmethod
    def get_selected_folder_id(self):
        """Selected folder id.

        Returns:
            str: Selected folder id.
        """

        pass

    @abstractmethod
    def get_selected_task_id(self):
        """Selected task id.

        Returns:
            str: Selected task id.
        """

        pass

    @abstractmethod
    def get_selected_task_name(self):
        """Selected task name.

        Returns:
            str: Selected task name.
        """

        pass

    @abstractmethod
    def get_selected_context(self):
        """Get whole selected context.

        Example:
            {
                "project_name": self.get_selected_project_name(),
                "folder_id": self.get_selected_folder_id(),
                "task_id": self.get_selected_task_id(),
                "task_name": self.get_selected_task_name(),
            }

        Returns:
            dict[str, Union[str, None]]: Selected context.
        """

        pass

    # Actions
    @abstractmethod
    def get_action_items(self, project_name, folder_id, task_id):
        pass

    @abstractmethod
    def set_application_force_not_open_workfile(
        self, project_name, folder_id, task_id, action_id, enabled
    ):
        pass

    @abstractmethod
    def trigger_action(self, project_name, folder_id, task_id, identifier):
        pass
