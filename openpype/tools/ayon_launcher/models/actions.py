import os

from openpype import resources
from openpype.lib import Logger
from openpype.pipeline import discover_launcher_actions


class ActionItem:
    def __init__(
        self,
        identifier,
        label,
        variant_label,
        icon,
        overlay_image=None,
        full_label=None
    ):
        self.identifier = identifier
        self.label = label
        self.variant_label = variant_label
        self.icon = icon
        self.overlay_image = overlay_image
        self._full_label = full_label

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
            "overlay_image": self.overlay_image,
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

    icon_name = action.icon
    if not icon_name:
        return {
            "type": "awesome",
            "name": "fa.cube",
            "color": "white"
        }

    icon_path = resources.get_resource(icon_name)
    if not os.path.exists(icon_path):
        try:
            icon_path = icon_name.format(resources.RESOURCES_DIR)
        except Exception:
            pass

    if os.path.exists(icon_path):
        return {
            "type": "path",
            "path": icon_path,
        }

    return {
        "type": "awesome",
        "name": icon_name,
        "color": action.color or "white"
    }


class ActionsModel:
    """Actions model.

    Args:
        controller (AbstractLauncherBackend): Controller instance.
    """

    def __init__(self, controller):
        self._controller = controller

        self._log = None

        self._discovered_actions = None
        self._actions = None
        self._action_items = None

    @property
    def log(self):
        if self._log is None:
            self._log = Logger.get_logger(self.__class__.__name__)
        return self._log

    def reset(self):
        self._discovered_actions = None
        self._actions = None
        self._action_items = None

        self._controller.emit_event("actions.refresh.started")
        self._get_action_items()
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

        session = self._prepare_session(project_name, folder_id, task_id)
        output = []
        action_items = self._get_action_items()
        for identifier, action in self._get_actions().items():
            if action.is_compatible(session):
                output.append(action_items[identifier])
        return output

    def trigger_action(self, project_name, folder_id, task_id, identifier):
        session = self._prepare_session(project_name, folder_id, task_id)
        failed = False
        try:
            self._controller.emit_event(
                "action.trigger.started",
                {"identifier": identifier,}
            )
            self._actions[identifier].process(session)
        except Exception:
            self.log.warning("Action trigger failed.", exc_info=True)
            failed = True

        self._controller.emit_event(
            "action.trigger.finished",
            {"identifier": identifier, "failed": failed,}
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
            self._discovered_actions = discover_launcher_actions()
        return self._discovered_actions

    def _get_actions(self):
        if self._actions is None:
            actions = {}
            for cls in self._get_discovered_action_classes():
                obj = cls()
                actions[obj.get_identifier()] = obj
            self._actions = actions
        return self._actions

    def _get_action_items(self):
        if self._action_items is not None:
            return self._action_items

        action_items = {}
        for identifier, action in self._get_actions().items():
            label = action.label or identifier
            variant_label = action.label_variant
            icon = get_action_icon(action)
            item = ActionItem(
                identifier,
                label,
                variant_label,
                icon,
            )
            action_items[identifier] = item
        self._action_items = action_items
        return action_items
