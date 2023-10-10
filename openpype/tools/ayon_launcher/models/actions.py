import os

from openpype import resources
from openpype.lib import Logger, OpenPypeSettingsRegistry
from openpype.pipeline.actions import (
    discover_launcher_actions,
    LauncherAction,
)


# class Action:
#     def __init__(self, label, icon=None, identifier=None):
#         self._label = label
#         self._icon = icon
#         self._callbacks = []
#         self._identifier = identifier or uuid.uuid4().hex
#         self._checked = True
#         self._checkable = False
#
#     def set_checked(self, checked):
#         self._checked = checked
#
#     def set_checkable(self, checkable):
#         self._checkable = checkable
#
#     def set_label(self, label):
#         self._label = label
#
#     def add_callback(self, callback):
#         self._callbacks = callback
#
#
# class Menu:
#     def __init__(self, label, icon=None):
#         self.label = label
#         self.icon = icon
#         self._actions = []
#
#     def add_action(self, action):
#         self._actions.append(action)


class ApplicationAction(LauncherAction):
    """Action to launch an application.

    Application action based on 'ApplicationManager' system.

    Handling of applications in launcher is not ideal and should be completely
    redone from scratch. This is just a temporary solution to keep backwards
    compatibility with OpenPype launcher.

    Todos:
        Move handling of errors to frontend.
    """

    # Application object
    application = None
    # Action attributes
    name = None
    label = None
    label_variant = None
    group = None
    icon = None
    color = None
    order = 0
    data = {}
    project_settings = {}
    project_entities = {}

    _log = None
    required_session_keys = (
        "AVALON_PROJECT",
        "AVALON_ASSET",
        "AVALON_TASK"
    )

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def is_compatible(self, session):
        for key in self.required_session_keys:
            if not session.get(key):
                return False

        project_name = session["AVALON_PROJECT"]
        project_entity = self.project_entities[project_name]
        apps = project_entity["attrib"].get("applications")
        if not apps or self.application.full_name not in apps:
            return False

        project_settings = self.project_settings[project_name]
        only_available = project_settings["applications"]["only_available"]
        if only_available and not self.application.find_executable():
            return False
        return True

    def _show_message_box(self, title, message, details=None):
        from qtpy import QtWidgets, QtGui
        from openpype import style

        dialog = QtWidgets.QMessageBox()
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        dialog.setWindowIcon(icon)
        dialog.setStyleSheet(style.load_stylesheet())
        dialog.setWindowTitle(title)
        dialog.setText(message)
        if details:
            dialog.setDetailedText(details)
        dialog.exec_()

    def process(self, session, **kwargs):
        """Process the full Application action"""

        from openpype.lib import (
            ApplictionExecutableNotFound,
            ApplicationLaunchFailed,
        )

        project_name = session["AVALON_PROJECT"]
        asset_name = session["AVALON_ASSET"]
        task_name = session["AVALON_TASK"]
        try:
            self.application.launch(
                project_name=project_name,
                asset_name=asset_name,
                task_name=task_name,
                **self.data
            )

        except ApplictionExecutableNotFound as exc:
            details = exc.details
            msg = exc.msg
            log_msg = str(msg)
            if details:
                log_msg += "\n" + details
            self.log.warning(log_msg)
            self._show_message_box(
                "Application executable not found", msg, details
            )

        except ApplicationLaunchFailed as exc:
            msg = str(exc)
            self.log.warning(msg, exc_info=True)
            self._show_message_box("Application launch failed", msg)


class ActionItem:
    """Item representing single action to trigger.

    Todos:
        Get rid of application specific logic.

    Args:
        identifier (str): Unique identifier of action item.
        label (str): Action label.
        variant_label (Union[str, None]): Variant label, full label is
            concatenated with space. Actions are grouped under single
            action if it has same 'label' and have set 'variant_label'.
        icon (dict[str, str]): Icon definition.
        order (int): Action ordering.
        is_application (bool): Is action application action.
        force_not_open_workfile (bool): Force not open workfile. Application
            related.
        full_label (Optional[str]): Full label, if not set it is generated
            from 'label' and 'variant_label'.
    """

    def __init__(
        self,
        identifier,
        label,
        variant_label,
        icon,
        order,
        is_application,
        force_not_open_workfile,
        full_label=None
    ):
        self.identifier = identifier
        self.label = label
        self.variant_label = variant_label
        self.icon = icon
        self.order = order
        self.is_application = is_application
        self.force_not_open_workfile = force_not_open_workfile
        self._full_label = full_label

    def copy(self):
        return self.from_data(self.to_data())

    @property
    def full_label(self):
        if self._full_label is None:
            if self.variant_label:
                self._full_label = " ".join([self.label, self.variant_label])
            else:
                self._full_label = self.label
        return self._full_label

    def to_data(self):
        return {
            "identifier": self.identifier,
            "label": self.label,
            "variant_label": self.variant_label,
            "icon": self.icon,
            "order": self.order,
            "is_application": self.is_application,
            "force_not_open_workfile": self.force_not_open_workfile,
            "full_label": self._full_label,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


def get_action_icon(action):
    """Get action icon info.

    Args:
        action (LacunherAction): Action instance.

    Returns:
        dict[str, str]: Icon info.
    """

    icon = action.icon
    if not icon:
        return {
            "type": "awesome-font",
            "name": "fa.cube",
            "color": "white"
        }

    if isinstance(icon, dict):
        return icon

    icon_path = resources.get_resource(icon)
    if not os.path.exists(icon_path):
        try:
            icon_path = icon.format(resources.RESOURCES_DIR)
        except Exception:
            pass

    if os.path.exists(icon_path):
        return {
            "type": "path",
            "path": icon_path,
        }

    return {
        "type": "awesome-font",
        "name": icon,
        "color": action.color or "white"
    }


class ActionsModel:
    """Actions model.

    Args:
        controller (AbstractLauncherBackend): Controller instance.
    """

    _not_open_workfile_reg_key = "force_not_open_workfile"

    def __init__(self, controller):
        self._controller = controller

        self._log = None

        self._discovered_actions = None
        self._actions = None
        self._action_items = {}

        self._launcher_tool_reg = OpenPypeSettingsRegistry("launcher_tool")

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def refresh(self):
        self._discovered_actions = None
        self._actions = None
        self._action_items = {}

        self._controller.emit_event("actions.refresh.started")
        self._get_action_objects()
        self._controller.emit_event("actions.refresh.finished")

    def get_action_items(self, project_name, folder_id, task_id):
        """Get actions for project.

        Args:
            project_name (Union[str, None]): Project name.
            folder_id (Union[str, None]): Folder id.
            task_id (Union[str, None]): Task id.

        Returns:
            list[ActionItem]: List of actions.
        """

        not_open_workfile_actions = self._get_no_last_workfile_for_context(
            project_name, folder_id, task_id)
        session = self._prepare_session(project_name, folder_id, task_id)
        output = []
        action_items = self._get_action_items(project_name)
        for identifier, action in self._get_action_objects().items():
            if not action.is_compatible(session):
                continue

            action_item = action_items[identifier]
            # Handling of 'force_not_open_workfile' for applications
            if action_item.is_application:
                action_item = action_item.copy()
                action_item.force_not_open_workfile = (
                    not_open_workfile_actions.get(identifier, False)
                )

            output.append(action_item)
        return output

    def set_application_force_not_open_workfile(
        self, project_name, folder_id, task_id, action_ids, enabled
    ):
        no_workfile_reg_data = self._get_no_last_workfile_reg_data()
        project_data = no_workfile_reg_data.setdefault(project_name, {})
        folder_data = project_data.setdefault(folder_id, {})
        task_data = folder_data.setdefault(task_id, {})
        for action_id in action_ids:
            task_data[action_id] = enabled
        self._launcher_tool_reg.set_item(
            self._not_open_workfile_reg_key, no_workfile_reg_data
        )

    def trigger_action(self, project_name, folder_id, task_id, identifier):
        session = self._prepare_session(project_name, folder_id, task_id)
        failed = False
        error_message = None
        action_label = identifier
        action_items = self._get_action_items(project_name)
        try:
            action = self._actions[identifier]
            action_item = action_items[identifier]
            action_label = action_item.full_label
            self._controller.emit_event(
                "action.trigger.started",
                {
                    "identifier": identifier,
                    "full_label": action_label,
                }
            )
            if isinstance(action, ApplicationAction):
                per_action = self._get_no_last_workfile_for_context(
                    project_name, folder_id, task_id
                )
                force_not_open_workfile = per_action.get(identifier, False)
                if force_not_open_workfile:
                    action.data["start_last_workfile"] = False
                else:
                    action.data.pop("start_last_workfile", None)
            action.process(session)
        except Exception as exc:
            self.log.warning("Action trigger failed.", exc_info=True)
            failed = True
            error_message = str(exc)

        self._controller.emit_event(
            "action.trigger.finished",
            {
                "identifier": identifier,
                "failed": failed,
                "error_message": error_message,
                "full_label": action_label,
            }
        )

    def _get_no_last_workfile_reg_data(self):
        try:
            no_workfile_reg_data = self._launcher_tool_reg.get_item(
                self._not_open_workfile_reg_key)
        except ValueError:
            no_workfile_reg_data = {}
            self._launcher_tool_reg.set_item(
                self._not_open_workfile_reg_key, no_workfile_reg_data)
        return no_workfile_reg_data

    def _get_no_last_workfile_for_context(
        self, project_name, folder_id, task_id
    ):
        not_open_workfile_reg_data = self._get_no_last_workfile_reg_data()
        return (
            not_open_workfile_reg_data
            .get(project_name, {})
            .get(folder_id, {})
            .get(task_id, {})
        )

    def _prepare_session(self, project_name, folder_id, task_id):
        folder_name = None
        if folder_id:
            folder = self._controller.get_folder_entity(
                project_name, folder_id)
            if folder:
                folder_name = folder["name"]

        task_name = None
        if task_id:
            task = self._controller.get_task_entity(project_name, task_id)
            if task:
                task_name = task["name"]

        return {
            "AVALON_PROJECT": project_name,
            "AVALON_ASSET": folder_name,
            "AVALON_TASK": task_name,
        }

    def _get_discovered_action_classes(self):
        if self._discovered_actions is None:
            self._discovered_actions = (
                discover_launcher_actions()
                + self._get_applications_action_classes()
            )
        return self._discovered_actions

    def _get_action_objects(self):
        if self._actions is None:
            actions = {}
            for cls in self._get_discovered_action_classes():
                obj = cls()
                identifier = getattr(obj, "identifier", None)
                if identifier is None:
                    identifier = cls.__name__
                actions[identifier] = obj
            self._actions = actions
        return self._actions

    def _get_action_items(self, project_name):
        action_items = self._action_items.get(project_name)
        if action_items is not None:
            return action_items

        project_entity = None
        if project_name:
            project_entity = self._controller.get_project_entity(project_name)
        project_settings = self._controller.get_project_settings(project_name)

        action_items = {}
        for identifier, action in self._get_action_objects().items():
            is_application = isinstance(action, ApplicationAction)
            if is_application:
                action.project_entities[project_name] = project_entity
                action.project_settings[project_name] = project_settings
            label = action.label or identifier
            variant_label = getattr(action, "label_variant", None)
            icon = get_action_icon(action)
            item = ActionItem(
                identifier,
                label,
                variant_label,
                icon,
                action.order,
                is_application,
                False
            )
            action_items[identifier] = item
        self._action_items[project_name] = action_items
        return action_items

    def _get_applications_action_classes(self):
        from openpype.lib.applications import (
            CUSTOM_LAUNCH_APP_GROUPS,
            ApplicationManager,
        )

        actions = []

        manager = ApplicationManager()
        for full_name, application in manager.applications.items():
            if (
                application.group.name in CUSTOM_LAUNCH_APP_GROUPS
                or not application.enabled
            ):
                continue

            action = type(
                "app_{}".format(full_name),
                (ApplicationAction,),
                {
                    "identifier": "application.{}".format(full_name),
                    "application": application,
                    "name": application.name,
                    "label": application.group.label,
                    "label_variant": application.label,
                    "group": None,
                    "icon": application.icon,
                    "color": getattr(application, "color", None),
                    "order": getattr(application, "order", None) or 0,
                    "data": {}
                }
            )
            actions.append(action)
        return actions
