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

    # Actions
    @abstractmethod
    def get_action_items(self, project_name, folder_id, task_id):
        pass

    @abstractmethod
    def trigger_action(self, project_name, folder_id, task_id, identifier):
        pass
