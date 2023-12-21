class _ExampleController:
    def emit_event(self, topic, data, **kwargs):
        pass


class HierarchyExpectedSelection:
    """Base skeleton of expected selection model.

    Expected selection model holds information about which entities should be
    selected. The order of selection is very important as change of project
    will affect what folders are available in folders UI and so on. Because
    of that should expected selection model know what is current entity
    to select.

    If any of 'handle_project', 'handle_folder' or 'handle_task' is set to
    'False' expected selection data won't contain information about the
    entity type at all. Also if project is not handled then it is not
    necessary to call 'expected_project_selected'. Same goes for folder and
    task.

    Model is triggering event with 'expected_selection_changed' topic and
    data > data structure is matching 'get_expected_selection_data' method.

    Questions:
        Require '_ExampleController' as abstraction?

    Args:
        controller (Any): Controller object. ('_ExampleController')
        handle_project (bool): Project can be considered as can have expected
            selection.
        handle_folder (bool): Folder can be considered as can have expected
            selection.
        handle_task (bool): Task can be considered as can have expected
            selection.
    """

    def __init__(
        self,
        controller,
        handle_project=True,
        handle_folder=True,
        handle_task=True
    ):
        self._project_name = None
        self._folder_id = None
        self._task_name = None

        self._project_selected = True
        self._folder_selected = True
        self._task_selected = True

        self._controller = controller

        self._handle_project = handle_project
        self._handle_folder = handle_folder
        self._handle_task = handle_task

    def set_expected_selection(
        self,
        project_name=None,
        folder_id=None,
        task_name=None
    ):
        """Sets expected selection.

        Args:
            project_name (Optional[str]): Project name.
            folder_id (Optional[str]): Folder id.
            task_name (Optional[str]): Task name.
        """

        self._project_name = project_name
        self._folder_id = folder_id
        self._task_name = task_name

        self._project_selected = not self._handle_project
        self._folder_selected = not self._handle_folder
        self._task_selected = not self._handle_task
        self._emit_change()

    def get_expected_selection_data(self):
        project_current = False
        folder_current = False
        task_current = False
        if not self._project_selected:
            project_current = True
        elif not self._folder_selected:
            folder_current = True
        elif not self._task_selected:
            task_current = True
        data = {}
        if self._handle_project:
            data["project"] = {
                "name": self._project_name,
                "current": project_current,
                "selected": self._project_selected,
            }
        if self._handle_folder:
            data["folder"] = {
                "id": self._folder_id,
                "current": folder_current,
                "selected": self._folder_selected,
            }
        if self._handle_task:
            data["task"] = {
                "name": self._task_name,
                "current": task_current,
                "selected": self._task_selected,
            }

        return data

    def is_expected_project_selected(self, project_name):
        if not self._handle_project:
            return True
        return project_name == self._project_name and self._project_selected

    def is_expected_folder_selected(self, folder_id):
        if not self._handle_folder:
            return True
        return folder_id == self._folder_id and self._folder_selected

    def expected_project_selected(self, project_name):
        """UI selected requested project.

        Other entity types can be requested for selection.

        Args:
            project_name (str): Name of project.
        """

        if project_name != self._project_name:
            return False
        self._project_selected = True
        self._emit_change()
        return True

    def expected_folder_selected(self, folder_id):
        """UI selected requested folder.

        Other entity types can be requested for selection.

        Args:
            folder_id (str): Folder id.
        """

        if folder_id != self._folder_id:
            return False
        self._folder_selected = True
        self._emit_change()
        return True

    def expected_task_selected(self, folder_id, task_name):
        """UI selected requested task.

        Other entity types can be requested for selection.

        Because task name is not unique across project a folder id is also
        required to confirm the right task has been selected.

        Args:
            folder_id (str): Folder id.
            task_name (str): Task name.
        """

        if self._folder_id != folder_id:
            return False

        if task_name != self._task_name:
            return False
        self._task_selected = True
        self._emit_change()
        return True

    def _emit_change(self):
        self._controller.emit_event(
            "expected_selection_changed",
            self.get_expected_selection_data(),
        )
