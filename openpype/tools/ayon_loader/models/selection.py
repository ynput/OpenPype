class SelectionModel(object):
    """Model handling selection changes.

    Triggering events:
    - "selection.project.changed"
    - "selection.folders.changed"
    - "selection.versions.changed"
    """

    event_source = "selection.model"

    def __init__(self, controller):
        self._controller = controller

        self._project_name = None
        self._folder_ids = set()
        self._version_ids = set()
        self._representation_ids = set()

    def get_selected_project_name(self):
        return self._project_name

    def set_selected_project(self, project_name):
        if self._project_name == project_name:
            return

        self._project_name = project_name
        self._controller.emit_event(
            "selection.project.changed",
            {"project_name": self._project_name},
            self.event_source
        )

    def get_selected_folder_ids(self):
        return self._folder_ids

    def set_selected_folders(self, folder_ids):
        if folder_ids == self._folder_ids:
            return

        self._folder_ids = folder_ids
        self._controller.emit_event(
            "selection.folders.changed",
            {
                "project_name": self._project_name,
                "folder_ids": folder_ids,
            },
            self.event_source
        )

    def get_selected_version_ids(self):
        return self._version_ids

    def set_selected_versions(self, version_ids):
        if version_ids == self._version_ids:
            return

        self._version_ids = version_ids
        self._controller.emit_event(
            "selection.versions.changed",
            {
                "project_name": self._project_name,
                "folder_ids": self._folder_ids,
                "version_ids": self._version_ids,
            },
            self.event_source
        )

    def get_selected_representation_ids(self):
        return self._representation_ids

    def set_selected_representations(self, repre_ids):
        if repre_ids == self._representation_ids:
            return

        self._representation_ids = repre_ids
        self._controller.emit_event(
            "selection.representations.changed",
            {
                "project_name": self._project_name,
                "folder_ids": self._folder_ids,
                "version_ids": self._version_ids,
                "representation_ids": self._representation_ids,
            }
        )
