import uuid
import copy
import logging
import collections
import appdirs

from . import lib
from .constants import (
    ACTION_ROLE,
    GROUP_ROLE,
    VARIANT_GROUP_ROLE,
    ACTION_ID_ROLE,
    FORCE_NOT_OPEN_WORKFILE_ROLE
)
from .actions import ApplicationAction
from Qt import QtCore, QtGui
from avalon.vendor import qtawesome
from avalon import style, api
from openpype.lib import ApplicationManager, JSONSettingRegistry

log = logging.getLogger(__name__)


class ActionModel(QtGui.QStandardItemModel):
    def __init__(self, dbcon, parent=None):
        super(ActionModel, self).__init__(parent=parent)
        self.dbcon = dbcon

        self.application_manager = ApplicationManager()

        self.default_icon = qtawesome.icon("fa.cube", color="white")
        # Cache of available actions
        self._registered_actions = list()
        self.items_by_id = {}
        path = appdirs.user_data_dir("openpype", "pype_club")
        self.launcher_registry = JSONSettingRegistry("launcher", path)

        try:
            _ = self.launcher_registry.get_item("force_not_open_workfile")
        except ValueError:
            self.launcher_registry.set_item("force_not_open_workfile", [])

    def discover(self):
        """Set up Actions cache. Run this for each new project."""
        # Discover all registered actions
        actions = api.discover(api.Action)

        # Get available project actions and the application actions
        app_actions = self.get_application_actions()
        actions.extend(app_actions)

        self._registered_actions = actions

        self.filter_actions()

    def get_application_actions(self):
        actions = []
        if not self.dbcon.Session.get("AVALON_PROJECT"):
            return actions

        project_doc = self.dbcon.find_one(
            {"type": "project"},
            {"config.apps": True}
        )
        if not project_doc:
            return actions

        self.application_manager.refresh()
        for app_def in project_doc["config"]["apps"]:
            app_name = app_def["name"]
            app = self.application_manager.applications.get(app_name)
            if not app or not app.enabled:
                continue

            # Get from app definition, if not there from app in project
            action = type(
                "app_{}".format(app_name),
                (ApplicationAction,),
                {
                    "application": app,
                    "name": app.name,
                    "label": app.group.label,
                    "label_variant": app.label,
                    "group": None,
                    "icon": app.icon,
                    "color": getattr(app, "color", None),
                    "order": getattr(app, "order", None) or 0,
                    "data": {}
                }
            )

            actions.append(action)
        return actions

    def get_icon(self, action, skip_default=False):
        icon = lib.get_action_icon(action)
        if not icon and not skip_default:
            return self.default_icon
        return icon

    def filter_actions(self):
        self.items_by_id.clear()
        # Validate actions based on compatibility
        self.clear()

        actions = self.filter_compatible_actions(self._registered_actions)

        single_actions = []
        varianted_actions = collections.defaultdict(list)
        grouped_actions = collections.defaultdict(list)
        for action in actions:
            # Groups
            group_name = getattr(action, "group", None)

            # Lable variants
            label = getattr(action, "label", None)
            label_variant = getattr(action, "label_variant", None)
            if label_variant and not label:
                print((
                    "Invalid action \"{}\" has set `label_variant` to \"{}\""
                    ", but doesn't have set `label` attribute"
                ).format(action.name, label_variant))
                action.label_variant = None
                label_variant = None

            if group_name:
                grouped_actions[group_name].append(action)

            elif label_variant:
                varianted_actions[label].append(action)
            else:
                single_actions.append(action)

        items_by_order = collections.defaultdict(list)
        for label, actions in tuple(varianted_actions.items()):
            if len(actions) == 1:
                varianted_actions.pop(label)
                single_actions.append(actions[0])
                continue

            icon = None
            order = None
            for action in actions:
                if icon is None:
                    _icon = lib.get_action_icon(action)
                    if _icon:
                        icon = _icon

                if order is None or action.order < order:
                    order = action.order

            if icon is None:
                icon = self.default_icon

            item = QtGui.QStandardItem(icon, label)
            item.setData(label, QtCore.Qt.ToolTipRole)
            item.setData(actions, ACTION_ROLE)
            item.setData(True, VARIANT_GROUP_ROLE)
            items_by_order[order].append(item)

        for action in single_actions:
            icon = self.get_icon(action)
            label = lib.get_action_label(action)
            item = QtGui.QStandardItem(icon, label)
            item.setData(label, QtCore.Qt.ToolTipRole)
            item.setData(action, ACTION_ROLE)
            items_by_order[action.order].append(item)

        for group_name, actions in grouped_actions.items():
            icon = None
            order = None
            for action in actions:
                if order is None or action.order < order:
                    order = action.order

                if icon is None:
                    _icon = lib.get_action_icon(action)
                    if _icon:
                        icon = _icon

            if icon is None:
                icon = self.default_icon

            item = QtGui.QStandardItem(icon, group_name)
            item.setData(actions, ACTION_ROLE)
            item.setData(True, GROUP_ROLE)

            items_by_order[order].append(item)

        self.beginResetModel()

        stored = self.launcher_registry.get_item("force_not_open_workfile")
        items = []
        for order in sorted(items_by_order.keys()):
            for item in items_by_order[order]:
                item_id = str(uuid.uuid4())
                item.setData(item_id, ACTION_ID_ROLE)

                if self.is_force_not_open_workfile(item,
                                                   stored):
                    label = item.text()
                    label += " (Not opening last workfile)"
                    item.setData(label, QtCore.Qt.ToolTipRole)
                    item.setData(True, FORCE_NOT_OPEN_WORKFILE_ROLE)

                self.items_by_id[item_id] = item
                items.append(item)

        self.invisibleRootItem().appendRows(items)

        self.endResetModel()

    def filter_compatible_actions(self, actions):
        """Collect all actions which are compatible with the environment

        Each compatible action will be translated to a dictionary to ensure
        the action can be visualized in the launcher.

        Args:
            actions (list): list of classes

        Returns:
            list: collection of dictionaries sorted on order int he
        """

        compatible = []
        _session = copy.deepcopy(self.dbcon.Session)
        session = {
            key: value
            for key, value in _session.items()
            if value
        }

        for action in actions:
            if action().is_compatible(session):
                compatible.append(action)

        # Sort by order and name
        return sorted(
            compatible,
            key=lambda action: (action.order, action.name)
        )

    def update_force_not_open_workfile_settings(self, is_checked, action):
        """Store/remove config for forcing to skip opening last workfile.

        Args:
            is_checked (bool): True to add, False to remove
            action (ApplicationAction)
        """
        actual_data = self._prepare_compare_data(action)

        stored = self.launcher_registry.get_item("force_not_open_workfile")
        if is_checked:
            stored.append(actual_data)
        else:
            final_values = []
            for config in stored:
                if config != actual_data:
                    final_values.append(config)
            stored = final_values

        self.launcher_registry.set_item("force_not_open_workfile", stored)

    def is_force_not_open_workfile(self, item, stored):
        """Checks if application for task is marked to not open workfile

        There might be specific tasks where is unwanted to open workfile right
        always (broken file, low performance). This allows artist to mark to
        skip opening for combination (project, asset, task_name, app)

        Args:
            item (QStandardItem)
            stored (list) of dict
        """
        action = item.data(ACTION_ROLE)
        if isinstance(action, list) and action:
            action = action[0]

        if ApplicationAction not in action.__bases__:
            return False

        actual_data = self._prepare_compare_data(action)
        for config in stored:
            if config == actual_data:
                return True

        return False

    def _prepare_compare_data(self, action):
        if isinstance(action, list) and action:
            action = action[0]

        _session = copy.deepcopy(self.dbcon.Session)
        session = {
            key: value
            for key, value in _session.items()
            if value
        }

        actual_data = {
            "app_label": action.label.lower(),
            "project_name": session["AVALON_PROJECT"],
            "asset": session["AVALON_ASSET"],
            "task_name": session["AVALON_TASK"]
        }

        return actual_data


class ProjectModel(QtGui.QStandardItemModel):
    """List of projects"""

    def __init__(self, dbcon, parent=None):
        super(ProjectModel, self).__init__(parent=parent)

        self.dbcon = dbcon
        self.project_icon = qtawesome.icon("fa.map", color="white")
        self._project_names = set()

    def refresh(self):
        project_names = set()
        for project_doc in self.get_projects():
            project_names.add(project_doc["name"])

        origin_project_names = set(self._project_names)
        self._project_names = project_names

        project_names_to_remove = origin_project_names - project_names
        if project_names_to_remove:
            row_counts = {}
            continuous = None
            for row in range(self.rowCount()):
                index = self.index(row, 0)
                index_name = index.data(QtCore.Qt.DisplayRole)
                if index_name in project_names_to_remove:
                    if continuous is None:
                        continuous = row
                        row_counts[continuous] = 0
                    row_counts[continuous] += 1
                else:
                    continuous = None

            for row in reversed(sorted(row_counts.keys())):
                count = row_counts[row]
                self.removeRows(row, count)

        continuous = None
        row_counts = {}
        for idx, project_name in enumerate(sorted(project_names)):
            if project_name in origin_project_names:
                continuous = None
                continue

            if continuous is None:
                continuous = idx
                row_counts[continuous] = []

            row_counts[continuous].append(project_name)

        for row in reversed(sorted(row_counts.keys())):
            items = []
            for project_name in row_counts[row]:
                item = QtGui.QStandardItem(self.project_icon, project_name)
                items.append(item)

            self.invisibleRootItem().insertRows(row, items)

    def get_projects(self):
        return sorted(self.dbcon.projects(only_active=True),
                      key=lambda x: x["name"])
