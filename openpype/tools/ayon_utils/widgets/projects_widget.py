from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.ayon_utils.models import PROJECTS_MODEL_SENDER
from .utils import RefreshThread

PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 1
PROJECT_IS_ACTIVE_ROLE = QtCore.Qt.UserRole + 2


class ProjectsModel(QtGui.QStandardItemModel):
    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(ProjectsModel, self).__init__()
        self._controller = controller

        self._project_items = {}

        self._empty_item = None
        self._empty_item_added = False

        self._is_refreshing = False
        self._refresh_thread = None

    @property
    def is_refreshing(self):
        return self._is_refreshing

    def refresh(self):
        self._refresh()

    def has_content(self):
        return len(self._project_items) > 0

    def _add_empty_item(self):
        item = self._get_empty_item()
        if not self._empty_item_added:
            root_item = self.invisibleRootItem()
            root_item.appendRow(item)
            self._empty_item_added = True

    def _remove_empty_item(self):
        if not self._empty_item_added:
            return

        root_item = self.invisibleRootItem()
        item = self._get_empty_item()
        root_item.takeRow(item.row())
        self._empty_item_added = False

    def _get_empty_item(self):
        if self._empty_item is None:
            item = QtGui.QStandardItem("< No projects >")
            item.setFlags(QtCore.Qt.NoItemFlags)
            self._empty_item = item
        return self._empty_item

    def _refresh(self):
        if self._is_refreshing:
            return
        self._is_refreshing = True
        refresh_thread = RefreshThread(
            "projects", self._query_project_items
        )
        refresh_thread.refresh_finished.connect(self._refresh_finished)
        refresh_thread.start()
        self._refresh_thread = refresh_thread

    def _query_project_items(self):
        return self._controller.get_project_items()

    def _refresh_finished(self):
        # TODO check if failed
        result = self._refresh_thread.get_result()
        self._refresh_thread = None

        self._fill_items(result)

        self._is_refreshing = False
        self.refreshed.emit()

    def _fill_items(self, project_items):
        items_to_remove = set(self._project_items.keys())
        new_items = []
        for project_item in project_items:
            project_name = project_item.name
            items_to_remove.discard(project_name)
            item = self._project_items.get(project_name)
            if item is None:
                item = QtGui.QStandardItem(project_name)
                new_items.append(item)
            item.setData(project_name, PROJECT_NAME_ROLE)
            item.setData(project_item.active, PROJECT_IS_ACTIVE_ROLE)
            self._project_items[project_name] = item

        root_item = self.invisibleRootItem()
        if new_items:
            root_item.appendRows(new_items)

        for project_name in items_to_remove:
            item = self._project_items.pop(project_name)
            root_item.removeRow(item.row())

        if self.has_content():
            self._remove_empty_item()
        else:
            self._add_empty_item()


class ProjectSortFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(ProjectSortFilterProxy, self).__init__(*args, **kwargs)
        self._filter_inactive = True
        # Disable case sensitivity
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def lessThan(self, left_index, right_index):
        if left_index.data(PROJECT_NAME_ROLE) is None:
            return True

        if right_index.data(PROJECT_NAME_ROLE) is None:
            return False

        left_is_active = left_index.data(PROJECT_IS_ACTIVE_ROLE)
        right_is_active = right_index.data(PROJECT_IS_ACTIVE_ROLE)
        if right_is_active == left_is_active:
            return super(ProjectSortFilterProxy, self).lessThan(
                left_index, right_index
            )

        if left_is_active:
            return True
        return False

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        string_pattern = self.filterRegularExpression().pattern()
        if (
            self._filter_inactive
            and not index.data(PROJECT_IS_ACTIVE_ROLE)
        ):
            return False

        if string_pattern:
            project_name = index.data(PROJECT_IS_ACTIVE_ROLE)
            if project_name is not None:
                return string_pattern.lower() in project_name.lower()

        return super(ProjectSortFilterProxy, self).filterAcceptsRow(
            source_row, source_parent
        )

    def _custom_index_filter(self, index):
        return bool(index.data(PROJECT_IS_ACTIVE_ROLE))

    def is_active_filter_enabled(self):
        return self._filter_inactive

    def set_active_filter_enabled(self, value):
        if self._filter_inactive == value:
            return
        self._filter_inactive = value
        self.invalidateFilter()


class ProjectsCombobox(QtWidgets.QWidget):
    def __init__(self, controller, parent, handle_expected_selection=False):
        super(ProjectsCombobox, self).__init__(parent)

        projects_combobox = QtWidgets.QComboBox(self)
        combobox_delegate = QtWidgets.QStyledItemDelegate(projects_combobox)
        projects_combobox.setItemDelegate(combobox_delegate)
        projects_model = ProjectsModel(controller)
        projects_proxy_model = ProjectSortFilterProxy()
        projects_proxy_model.setSourceModel(projects_model)
        projects_combobox.setModel(projects_proxy_model)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(projects_combobox, 1)

        projects_model.refreshed.connect(self._on_model_refresh)

        controller.register_event_callback(
            "projects.refresh.finished",
            self._on_projects_refresh_finished
        )
        controller.register_event_callback(
            "controller.refresh.finished",
            self._on_controller_refresh
        )
        controller.register_event_callback(
            "expected_selection_changed",
            self._on_expected_selection_change
        )

        projects_combobox.currentIndexChanged.connect(
            self._on_current_index_changed
        )

        self._controller = controller
        self._listen_selection_change = True

        self._handle_expected_selection = handle_expected_selection
        self._expected_selection = None

        self._projects_combobox = projects_combobox
        self._projects_model = projects_model
        self._projects_proxy_model = projects_proxy_model
        self._combobox_delegate = combobox_delegate

    def refresh(self):
        self._projects_model.refresh()

    def set_selection(self, project_name):
        """Set selection to a given project.

        Selection change is ignored if project is not found.

        Args:
            project_name (str): Name of project.

        Returns:
            bool: True if selection was changed, False otherwise. NOTE:
                Selection may not be changed if project is not found, or if
                project is already selected.
        """

        idx = self._projects_combobox.findData(
            project_name, PROJECT_NAME_ROLE)
        if idx < 0:
            return False
        if idx != self._projects_combobox.currentIndex():
            self._projects_combobox.setCurrentIndex(idx)
            return True
        return False

    def set_listen_to_selection_change(self, listen):
        """Disable listening to changes of the selection.

        Because combobox is triggering selection change when it's model
        is refreshed, it's necessary to disable listening to selection for
        some cases, e.g. when is on a different page of UI and should be just
        refreshed.

        Args:
            listen (bool): Enable or disable listening to selection changes.
        """

        self._listen_selection_change = listen

    def get_current_project_name(self):
        """Name of selected project.

        Returns:
            Union[str, None]: Name of selected project, or None if no project
        """

        idx = self._projects_combobox.currentIndex()
        if idx < 0:
            return None
        return self._projects_combobox.itemData(idx, PROJECT_NAME_ROLE)

    def _on_current_index_changed(self, idx):
        if not self._listen_selection_change:
            return
        project_name = self._projects_combobox.itemData(
            idx, PROJECT_NAME_ROLE)
        self._controller.set_selected_project(project_name)

    def _on_model_refresh(self):
        self._projects_proxy_model.sort(0)
        if self._expected_selection:
            self._set_expected_selection()

    def _on_projects_refresh_finished(self, event):
        if event["sender"] != PROJECTS_MODEL_SENDER:
            self._projects_model.refresh()

    def _on_controller_refresh(self):
        self._update_expected_selection()

    # Expected selection handling
    def _on_expected_selection_change(self, event):
        self._update_expected_selection(event.data)

    def _set_expected_selection(self):
        if not self._handle_expected_selection:
            return
        project_name = self._expected_selection
        if project_name is not None:
            if project_name != self.get_current_project_name():
                self.set_selection(project_name)
            else:
                # Fake project change
                self._on_current_index_changed(
                    self._projects_combobox.currentIndex()
                )

        self._controller.expected_project_selected(project_name)

    def _update_expected_selection(self, expected_data=None):
        if not self._handle_expected_selection:
            return
        if expected_data is None:
            expected_data = self._controller.get_expected_selection_data()

        project_data = expected_data.get("project")
        if (
            not project_data
            or not project_data["current"]
            or project_data["selected"]
        ):
            return
        self._expected_selection = project_data["name"]
        if not self._projects_model.is_refreshing:
            self._set_expected_selection()


class ProjectsWidget(QtWidgets.QWidget):
    # TODO implement
    pass
