from abc import ABCMeta, abstractmethod

import six


@six.add_metaclass(ABCMeta)
class AbstractLauncherCommon(object):
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


class AbstractLauncherBackend(AbstractLauncherCommon):
    @abstractmethod
    def emit_event(self, topic, data=None, source=None):
        """Emit event.

        Args:
            topic (str): Event topic used for callbacks filtering.
            data (Optional[dict[str, Any]]): Event data.
            source (Optional[str]): Event source.
        """

        pass

    @abstractmethod
    def get_project_settings(self, project_name):
        """Project settings for current project.

        Args:
            project_name (Union[str, None]): Project name.

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


class AbstractLauncherFrontEnd(AbstractLauncherCommon):
    # Entity items for UI
    @abstractmethod
    def get_project_items(self, sender=None):
        """Project items for all projects.

        This function may trigger events 'projects.refresh.started' and
        'projects.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of project items in UI elements.

        Args:
            sender (str): Who requested folder items.

        Returns:
            list[ProjectItem]: Minimum possible information needed
                for visualisation of folder hierarchy.
        """

        pass

    @abstractmethod
    def get_folder_items(self, project_name, sender=None):
        """Folder items to visualize project hierarchy.

        This function may trigger events 'folders.refresh.started' and
        'folders.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of folder items in UI elements.

        Args:
            project_name (str): Project name.
            sender (str): Who requested folder items.

        Returns:
            list[FolderItem]: Minimum possible information needed
                for visualisation of folder hierarchy.
        """

        pass

    @abstractmethod
    def get_task_items(self, project_name, folder_id, sender=None):
        """Task items.

        This function may trigger events 'tasks.refresh.started' and
        'tasks.refresh.finished' which will contain 'sender' value in data.
        That may help to avoid re-refresh of task items in UI elements.

        Args:
            project_name (str): Project name.
            folder_id (str): Folder ID for which are tasks requested.
            sender (str): Who requested folder items.

        Returns:
            list[TaskItem]: Minimum possible information needed
                for visualisation of tasks.
        """

        pass

    @abstractmethod
    def get_selected_project_name(self):
        """Selected project name.

        Returns:
            Union[str, None]: Selected project name.
        """

        pass

    @abstractmethod
    def get_selected_folder_id(self):
        """Selected folder id.

        Returns:
            Union[str, None]: Selected folder id.
        """

        pass

    @abstractmethod
    def get_selected_task_id(self):
        """Selected task id.

        Returns:
            Union[str, None]: Selected task id.
        """

        pass

    @abstractmethod
    def get_selected_task_name(self):
        """Selected task name.

        Returns:
            Union[str, None]: Selected task name.
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

    @abstractmethod
    def set_selected_project(self, project_name):
        """Change selected folder.

        Args:
            project_name (Union[str, None]): Project nameor None if no project
                is selected.
        """

        pass

    @abstractmethod
    def set_selected_folder(self, folder_id):
        """Change selected folder.

        Args:
            folder_id (Union[str, None]): Folder id or None if no folder
                is selected.
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

    # Actions
    @abstractmethod
    def get_action_items(self, project_name, folder_id, task_id):
        """Get action items for given context.

        Args:
            project_name (Union[str, None]): Project name.
            folder_id (Union[str, None]): Folder id.
            task_id (Union[str, None]): Task id.

        Returns:
            list[ActionItem]: List of action items that should be shown
                for given context.
        """

        pass

    @abstractmethod
    def trigger_action(self, project_name, folder_id, task_id, action_id):
        """Trigger action on given context.

        Args:
            project_name (Union[str, None]): Project name.
            folder_id (Union[str, None]): Folder id.
            task_id (Union[str, None]): Task id.
            action_id (str): Action identifier.
        """

        pass

    @abstractmethod
    def set_application_force_not_open_workfile(
        self, project_name, folder_id, task_id, action_ids, enabled
    ):
        """This is application action related to force not open last workfile.

        Args:
            project_name (Union[str, None]): Project name.
            folder_id (Union[str, None]): Folder id.
            task_id (Union[str, None]): Task id.
            action_id (Iterable[str]): Action identifiers.
            enabled (bool): New value of force not open workfile.
        """

        pass

    @abstractmethod
    def refresh(self):
        """Refresh everything, models, ui etc.

        Triggers 'controller.refresh.started' event at the beginning and
        'controller.refresh.finished' at the end.
        """

        pass

    @abstractmethod
    def refresh_actions(self):
        """Refresh actions and all related data.

        Triggers 'controller.refresh.actions.started' event at the beginning
        and 'controller.refresh.actions.finished' at the end.
        """

        pass
