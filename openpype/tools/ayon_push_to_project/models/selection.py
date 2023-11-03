class PushToProjectSelectionModel(object):
    """Model handling selection changes.

    Triggering events:
    - "selection.project.changed"
    - "selection.folder.changed"
    - "selection.task.changed"
    """

    event_source = "push-to-project.selection.model"

    def __init__(self, controller):
        self._controller = controller

        self._project_name = None
        self._folder_id = None
        self._task_name = None
        self._task_id = None

    def get_selected_project_name(self):
        return self._project_name

    def set_selected_project(self, project_name):
        if project_name == self._project_name:
            return

        self._project_name = project_name
        self._controller.emit_event(
            "selection.project.changed",
            {"project_name": project_name},
            self.event_source
        )

    def get_selected_folder_id(self):
        return self._folder_id

    def set_selected_folder(self, folder_id):
        if folder_id == self._folder_id:
            return

        self._folder_id = folder_id
        self._controller.emit_event(
            "selection.folder.changed",
            {
                "project_name": self._project_name,
                "folder_id": folder_id,
            },
            self.event_source
        )

    def get_selected_task_name(self):
        return self._task_name

    def get_selected_task_id(self):
        return self._task_id

    def set_selected_task(self, task_id, task_name):
        if task_id == self._task_id:
            return

        self._task_name = task_name
        self._task_id = task_id
        self._controller.emit_event(
            "selection.task.changed",
            {
                "project_name": self._project_name,
                "folder_id": self._folder_id,
                "task_name": task_name,
                "task_id": task_id,
            },
            self.event_source
        )
