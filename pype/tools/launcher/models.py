import copy
import logging
import collections

from . import lib
from Qt import QtCore, QtGui
from avalon.vendor import qtawesome
from avalon import style, api

log = logging.getLogger(__name__)


class TaskModel(QtGui.QStandardItemModel):
    """A model listing the tasks combined for a list of assets"""

    def __init__(self, dbcon, parent=None):
        super(TaskModel, self).__init__(parent=parent)
        self.dbcon = dbcon

        self._num_assets = 0

        self.default_icon = qtawesome.icon(
            "fa.male", color=style.colors.default
        )
        self.no_task_icon = qtawesome.icon(
            "fa.exclamation-circle", color=style.colors.mid
        )

        self._icons = {}

        self._get_task_icons()

    def _get_task_icons(self):
        if not self.dbcon.Session.get("AVALON_PROJECT"):
            return

        # Get the project configured icons from database
        project = self.dbcon.find_one({"type": "project"})
        for task in project["config"].get("tasks") or []:
            icon_name = task.get("icon")
            if icon_name:
                self._icons[task["name"]] = qtawesome.icon(
                    "fa.{}".format(icon_name), color=style.colors.default
                )

    def set_assets(self, asset_ids=None, asset_docs=None):
        """Set assets to track by their database id

        Arguments:
            asset_ids (list): List of asset ids.
            asset_docs (list): List of asset entities from MongoDB.

        """

        if asset_docs is None and asset_ids is not None:
            # find assets in db by query
            asset_docs = list(self.dbcon.find({
                "type": "asset",
                "_id": {"$in": asset_ids}
            }))
            db_assets_ids = tuple(asset_doc["_id"] for asset_doc in asset_docs)

            # check if all assets were found
            not_found = tuple(
                str(asset_id)
                for asset_id in asset_ids
                if asset_id not in db_assets_ids
            )

            assert not not_found, "Assets not found by id: {0}".format(
                ", ".join(not_found)
            )

        self.clear()

        if not asset_docs:
            return

        task_names = set()
        for asset_doc in asset_docs:
            asset_tasks = asset_doc.get("data", {}).get("tasks") or set()
            task_names.update(asset_tasks)

        self.beginResetModel()

        if not task_names:
            item = QtGui.QStandardItem(self.no_task_icon, "No task")
            item.setEnabled(False)
            self.appendRow(item)

        else:
            for task_name in sorted(task_names):
                icon = self._icons.get(task_name, self.default_icon)
                item = QtGui.QStandardItem(icon, task_name)
                self.appendRow(item)

        self.endResetModel()

    def headerData(self, section, orientation, role):
        if (
            role == QtCore.Qt.DisplayRole
            and orientation == QtCore.Qt.Horizontal
            and section == 0
        ):
            return "Tasks"
        return super(TaskModel, self).headerData(section, orientation, role)


class ActionModel(QtGui.QStandardItemModel):
    ACTION_ROLE = QtCore.Qt.UserRole
    GROUP_ROLE = QtCore.Qt.UserRole + 1
    VARIANT_GROUP_ROLE = QtCore.Qt.UserRole + 2

    def __init__(self, dbcon, parent=None):
        super(ActionModel, self).__init__(parent=parent)
        self.dbcon = dbcon

        self._session = {}
        self._groups = {}
        self.default_icon = qtawesome.icon("fa.cube", color="white")
        # Cache of available actions
        self._registered_actions = list()

        self.discover()

    def discover(self):
        """Set up Actions cache. Run this for each new project."""
        if not self.dbcon.Session.get("AVALON_PROJECT"):
            self._registered_actions = list()
            return

        # Discover all registered actions
        actions = api.discover(api.Action)

        # Get available project actions and the application actions
        project_doc = self.dbcon.find_one({"type": "project"})
        app_actions = lib.get_application_actions(project_doc)
        actions.extend(app_actions)

        self._registered_actions = actions

    def get_icon(self, action, skip_default=False):
        icon = lib.get_action_icon(action)
        if not icon and not skip_default:
            return self.default_icon
        return icon

    def refresh(self):
        # Validate actions based on compatibility
        self.clear()

        self._groups.clear()

        actions = self.filter_compatible_actions(self._registered_actions)

        self.beginResetModel()

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

            item = QtGui.QStandardItem(icon, action.label)
            item.setData(actions, self.ACTION_ROLE)
            item.setData(True, self.VARIANT_GROUP_ROLE)
            items_by_order[order].append(item)

        for action in single_actions:
            icon = self.get_icon(action)
            item = QtGui.QStandardItem(icon, lib.get_action_label(action))
            item.setData(action, self.ACTION_ROLE)
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
            item.setData(actions, self.ACTION_ROLE)
            item.setData(True, self.GROUP_ROLE)

            items_by_order[order].append(item)

        for order in sorted(items_by_order.keys()):
            for item in items_by_order[order]:
                self.appendRow(item)

        self.endResetModel()

    def set_session(self, session):
        assert isinstance(session, dict)
        self._session = copy.deepcopy(session)
        self.refresh()

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
        for action in actions:
            if action().is_compatible(self._session):
                compatible.append(action)

        # Sort by order and name
        return sorted(
            compatible,
            key=lambda action: (action.order, action.name)
        )


class ProjectModel(QtGui.QStandardItemModel):
    """List of projects"""

    def __init__(self, dbcon, parent=None):
        super(ProjectModel, self).__init__(parent=parent)

        self.dbcon = dbcon

        self.hide_invisible = False
        self.project_icon = qtawesome.icon("fa.map", color="white")

    def refresh(self):
        self.clear()
        self.beginResetModel()

        for project_doc in self.get_projects():
            item = QtGui.QStandardItem(self.project_icon, project_doc["name"])
            self.appendRow(item)

        self.endResetModel()

    def get_projects(self):
        project_docs = []
        for project_doc in sorted(
            self.dbcon.projects(), key=lambda x: x["name"]
        ):
            if (
                self.hide_invisible
                and not project_doc["data"].get("visible", True)
            ):
                continue
            project_docs.append(project_doc)

        return project_docs
