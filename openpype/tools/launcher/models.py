import uuid
import copy
import logging
import collections

from Qt import QtCore, QtGui
from openpype.lib import ApplicationManager
from openpype.tools.utils.lib import DynamicQThread

from . import lib
from .constants import (
    ACTION_ROLE,
    GROUP_ROLE,
    VARIANT_GROUP_ROLE,
    ACTION_ID_ROLE
)
from .actions import ApplicationAction
from avalon.vendor import qtawesome
from avalon import style, api

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
                    "order": getattr(app, "order", None) or 0
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

        items = []
        for order in sorted(items_by_order.keys()):
            for item in items_by_order[order]:
                item_id = str(uuid.uuid4())
                item.setData(item_id, ACTION_ID_ROLE)
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


class LauncherModel(QtCore.QObject):
    # Refresh interval of projects
    refresh_interval = 10000

    # Signals
    # Current project has changed
    project_changed = QtCore.Signal(str)
    # Filters has changed (any)
    filters_changed = QtCore.Signal()

    # Projects were refreshed
    projects_refreshed = QtCore.Signal()

    # Signals ONLY for assets model!
    # - other objects should listen to asset model signals
    # Asset refresh started
    assets_refresh_started = QtCore.Signal()
    # Assets refresh finished
    assets_refreshed = QtCore.Signal()

    # Refresh timer timeout
    #   - give ability to tell parent window that this timer still runs
    timer_timeout = QtCore.Signal()

    # Duplication from AssetsModel with "data.tasks"
    _asset_projection = {
        "name": 1,
        "parent": 1,
        "data.visualParent": 1,
        "data.label": 1,
        "data.icon": 1,
        "data.color": 1,
        "data.tasks": 1
    }

    def __init__(self, dbcon):
        super(LauncherModel, self).__init__()
        # Refresh timer
        #   - should affect only projects
        refresh_timer = QtCore.QTimer()
        refresh_timer.setInterval(self.refresh_interval)
        refresh_timer.timeout.connect(self._on_timeout)

        self._refresh_timer = refresh_timer

        # Launcher is active
        self._active = False

        # Global data
        self._dbcon = dbcon
        # Available project names
        self._project_names = set()

        # Context data
        self._asset_docs = []
        self._asset_docs_by_id = {}
        self._asset_filter_data_by_id = {}
        self._assignees = set()
        self._task_types = set()

        # Filters
        self._asset_name_filter = ""
        self._assignee_filters = set()
        self._task_type_filters = set()

        # Last project for which were assets queried
        self._last_project_name = None
        # Asset refresh thread is running
        self._refreshing_assets = False
        # Asset refresh thread
        self._asset_refresh_thread = None

    def _on_timeout(self):
        """Refresh timer timeout."""
        if self._active:
            self.timer_timeout.emit()
            self.refresh_projects()

    def set_active(self, active):
        """Window change active state."""
        self._active = active

    def start_refresh_timer(self, trigger=False):
        """Start refresh timer."""
        self._refresh_timer.start()
        if trigger:
            self._on_timeout()

    def stop_refresh_timer(self):
        """Stop refresh timer."""
        self._refresh_timer.stop()

    @property
    def project_name(self):
        """Current project name."""
        return self._dbcon.Session.get("AVALON_PROJECT")

    @property
    def refreshing_assets(self):
        """Refreshing thread is running."""
        return self._refreshing_assets

    @property
    def asset_docs(self):
        """Access to asset docs."""
        return self._asset_docs

    @property
    def project_names(self):
        """Available project names."""
        return self._project_names

    @property
    def asset_filter_data_by_id(self):
        """Prepared filter data by asset id."""
        return self._asset_filter_data_by_id

    @property
    def assignees(self):
        """All assignees for all assets in current project."""
        return self._assignees

    @property
    def task_types(self):
        """All task types for all assets in current project.

        TODO: This could be maybe taken from project document where are all
        task types...
        """
        return self._task_types

    @property
    def task_type_filters(self):
        """Currently set task type filters."""
        return self._task_type_filters

    @property
    def assignee_filters(self):
        """Currently set assignee filters."""
        return self._assignee_filters

    @property
    def asset_name_filter(self):
        """Asset name filter (can be used as regex filter)."""
        return self._asset_name_filter

    def get_asset_doc(self, asset_id):
        """Get single asset document by id."""
        return self._asset_docs_by_id.get(asset_id)

    def set_project_name(self, project_name):
        """Change project name and refresh asset documents."""
        if project_name == self.project_name:
            return
        self._dbcon.Session["AVALON_PROJECT"] = project_name
        self.project_changed.emit(project_name)

        self.refresh_assets(force=True)

    def refresh(self):
        """Trigger refresh of whole model."""
        self.refresh_projects()
        self.refresh_assets(force=False)

    def refresh_projects(self):
        """Refresh projects."""
        current_project = self.project_name
        project_names = set()
        for project_doc in self._dbcon.projects(only_active=True):
            project_names.add(project_doc["name"])

        self._project_names = project_names
        self.projects_refreshed.emit()
        if (
            current_project is not None
            and current_project not in project_names
        ):
            self.set_project_name(None)

    def _set_asset_docs(self, asset_docs=None):
        """Set asset documents and all related data.

        Method extract and prepare data needed for assets and tasks widget and
        prepare filtering data.
        """
        if asset_docs is None:
            asset_docs = []

        all_task_types = set()
        all_assignees = set()
        asset_docs_by_id = {}
        asset_filter_data_by_id = {}
        for asset_doc in asset_docs:
            task_types = set()
            assignees = set()
            asset_id = asset_doc["_id"]
            asset_docs_by_id[asset_id] = asset_doc
            asset_tasks = asset_doc.get("data", {}).get("tasks")
            asset_filter_data_by_id[asset_id] = {
                "assignees": assignees,
                "task_types": task_types
            }
            if not asset_tasks:
                continue

            for task_data in asset_tasks.values():
                task_assignees = set()
                _task_assignees = task_data.get("assignees")
                if _task_assignees:
                    for assignee in _task_assignees:
                        task_assignees.add(assignee["username"])

                task_type = task_data.get("type")
                if task_assignees:
                    assignees |= set(task_assignees)
                if task_type:
                    task_types.add(task_type)

            all_task_types |= task_types
            all_assignees |= assignees

        self._asset_docs_by_id = asset_docs_by_id
        self._asset_docs = asset_docs
        self._asset_filter_data_by_id = asset_filter_data_by_id
        self._assignees = all_assignees
        self._task_types = all_task_types

        self.assets_refreshed.emit()

    def set_task_type_filter(self, task_types):
        """Change task type filter.

        Args:
            task_types (set): Set of task types that should be visible.
                Pass empty set to turn filter off.
        """
        self._task_type_filters = task_types
        self.filters_changed.emit()

    def set_assignee_filter(self, assignees):
        """Change assignees filter.

        Args:
            assignees (set): Set of assignees that should be visible.
                Pass empty set to turn filter off.
        """
        self._assignee_filters = assignees
        self.filters_changed.emit()

    def set_asset_name_filter(self, text_filter):
        """Change asset name filter.

        Args:
            text_filter (str): Asset name filter. Pass empty string to
            turn filter off.
        """
        self._asset_name_filter = text_filter
        self.filters_changed.emit()

    def refresh_assets(self, force=True):
        """Refresh assets."""
        self.assets_refresh_started.emit()

        if self.project_name is None:
            self._set_asset_docs()
            return

        if (
            not force
            and self._last_project_name == self.project_name
        ):
            return

        self._stop_fetch_thread()

        self._refreshing_assets = True
        self._last_project_name = self.project_name
        self._asset_refresh_thread = DynamicQThread(self._refresh_assets)
        self._asset_refresh_thread.start()

    def _stop_fetch_thread(self):
        self._refreshing_assets = False
        if self._asset_refresh_thread is not None:
            while self._asset_refresh_thread.isRunning():
                time.sleep(0.01)
            self._asset_refresh_thread = None

    def _refresh_assets(self):
        asset_docs = list(self._dbcon.find(
            {"type": "asset"},
            self._asset_projection
        ))
        time.sleep(5)
        if not self._refreshing_assets:
            return
        self._refreshing_assets = False
        self._set_asset_docs(asset_docs)


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
