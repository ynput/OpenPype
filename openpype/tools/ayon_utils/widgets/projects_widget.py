from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.ayon_utils.models import PROJECTS_MODEL_SENDER
from .utils import RefreshThread, get_qt_icon

PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 1
PROJECT_IS_ACTIVE_ROLE = QtCore.Qt.UserRole + 2
PROJECT_IS_LIBRARY_ROLE = QtCore.Qt.UserRole + 3
PROJECT_IS_CURRENT_ROLE = QtCore.Qt.UserRole + 4
LIBRARY_PROJECT_SEPARATOR_ROLE = QtCore.Qt.UserRole + 5


class ProjectsQtModel(QtGui.QStandardItemModel):
    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(ProjectsQtModel, self).__init__()
        self._controller = controller

        self._project_items = {}
        self._has_libraries = False

        self._empty_item = None
        self._empty_item_added = False

        self._select_item = None
        self._select_item_added = False
        self._select_item_visible = None

        self._libraries_sep_item = None
        self._libraries_sep_item_added = False
        self._libraries_sep_item_visible = False

        self._current_context_project = None

        self._selected_project = None

        self._refresh_thread = None

    @property
    def is_refreshing(self):
        return self._refresh_thread is not None

    def refresh(self):
        self._refresh()

    def has_content(self):
        return len(self._project_items) > 0

    def set_select_item_visible(self, visible):
        if self._select_item_visible is visible:
            return
        self._select_item_visible = visible

        if self._selected_project is None:
            self._add_select_item()

    def set_libraries_separator_visible(self, visible):
        if self._libraries_sep_item_visible is visible:
            return
        self._libraries_sep_item_visible = visible

    def set_selected_project(self, project_name):
        if not self._select_item_visible:
            return

        self._selected_project = project_name
        if project_name is None:
            self._add_select_item()
        else:
            self._remove_select_item()

    def set_current_context_project(self, project_name):
        if project_name == self._current_context_project:
            return
        self._unset_current_context_project(self._current_context_project)
        self._current_context_project = project_name
        self._set_current_context_project(project_name)

    def _set_current_context_project(self, project_name):
        item = self._project_items.get(project_name)
        if item is None:
            return
        item.setData(True, PROJECT_IS_CURRENT_ROLE)

    def _unset_current_context_project(self, project_name):
        item = self._project_items.get(project_name)
        if item is None:
            return
        item.setData(False, PROJECT_IS_CURRENT_ROLE)

    def _add_empty_item(self):
        if self._empty_item_added:
            return
        self._empty_item_added = True
        item = self._get_empty_item()
        root_item = self.invisibleRootItem()
        root_item.appendRow(item)

    def _remove_empty_item(self):
        if not self._empty_item_added:
            return
        self._empty_item_added = False
        root_item = self.invisibleRootItem()
        item = self._get_empty_item()
        root_item.takeRow(item.row())

    def _get_empty_item(self):
        if self._empty_item is None:
            item = QtGui.QStandardItem("< No projects >")
            item.setFlags(QtCore.Qt.NoItemFlags)
            self._empty_item = item
        return self._empty_item

    def _get_library_sep_item(self):
        if self._libraries_sep_item is not None:
            return self._libraries_sep_item

        item = QtGui.QStandardItem()
        item.setData("Libraries", QtCore.Qt.DisplayRole)
        item.setData(True, LIBRARY_PROJECT_SEPARATOR_ROLE)
        item.setFlags(QtCore.Qt.NoItemFlags)
        self._libraries_sep_item = item
        return item

    def _add_library_sep_item(self):
        if (
            not self._libraries_sep_item_visible
            or self._libraries_sep_item_added
        ):
            return
        self._libraries_sep_item_added = True
        item = self._get_library_sep_item()
        root_item = self.invisibleRootItem()
        root_item.appendRow(item)

    def _remove_library_sep_item(self):
        if (
            not self._libraries_sep_item_added
        ):
            return
        self._libraries_sep_item_added = False
        item = self._get_library_sep_item()
        root_item = self.invisibleRootItem()
        root_item.takeRow(item.row())

    def _add_select_item(self):
        if self._select_item_added:
            return
        self._select_item_added = True
        item = self._get_select_item()
        root_item = self.invisibleRootItem()
        root_item.appendRow(item)

    def _remove_select_item(self):
        if not self._select_item_added:
            return
        self._select_item_added = False
        root_item = self.invisibleRootItem()
        item = self._get_select_item()
        root_item.takeRow(item.row())

    def _get_select_item(self):
        if self._select_item is None:
            item = QtGui.QStandardItem("< Select project >")
            item.setEditable(False)
            self._select_item = item
        return self._select_item

    def _refresh(self):
        if self._refresh_thread is not None:
            return

        refresh_thread = RefreshThread(
            "projects", self._query_project_items
        )
        refresh_thread.refresh_finished.connect(self._refresh_finished)

        self._refresh_thread = refresh_thread
        refresh_thread.start()

    def _query_project_items(self):
        return self._controller.get_project_items(
            sender=PROJECTS_MODEL_SENDER
        )

    def _refresh_finished(self):
        # TODO check if failed
        result = self._refresh_thread.get_result()
        if result is not None:
            self._fill_items(result)

        self._refresh_thread = None
        if result is None:
            self._refresh()
        else:
            self.refreshed.emit()

    def _fill_items(self, project_items):
        new_project_names = {
            project_item.name
            for project_item in project_items
        }

        # Handle "Select item" visibility
        if self._select_item_visible:
            # Add select project. if previously selected project is not in
            #   project items
            if self._selected_project not in new_project_names:
                self._add_select_item()
            else:
                self._remove_select_item()

        root_item = self.invisibleRootItem()

        items_to_remove = set(self._project_items.keys()) - new_project_names
        for project_name in items_to_remove:
            item = self._project_items.pop(project_name)
            root_item.takeRow(item.row())

        has_library_project = False
        new_items = []
        for project_item in project_items:
            project_name = project_item.name
            item = self._project_items.get(project_name)
            if project_item.is_library:
                has_library_project = True
            if item is None:
                item = QtGui.QStandardItem()
                item.setEditable(False)
                new_items.append(item)
            icon = get_qt_icon(project_item.icon)
            item.setData(project_name, QtCore.Qt.DisplayRole)
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setData(project_name, PROJECT_NAME_ROLE)
            item.setData(project_item.active, PROJECT_IS_ACTIVE_ROLE)
            item.setData(project_item.is_library, PROJECT_IS_LIBRARY_ROLE)
            is_current = project_name == self._current_context_project
            item.setData(is_current, PROJECT_IS_CURRENT_ROLE)
            self._project_items[project_name] = item

        self._set_current_context_project(self._current_context_project)

        self._has_libraries = has_library_project

        if new_items:
            root_item.appendRows(new_items)

        if self.has_content():
            # Make sure "No projects" item is removed
            self._remove_empty_item()
            if has_library_project:
                self._add_library_sep_item()
            else:
                self._remove_library_sep_item()
        else:
            # Keep only "No projects" item
            self._add_empty_item()
            self._remove_select_item()
            self._remove_library_sep_item()


class ProjectSortFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(ProjectSortFilterProxy, self).__init__(*args, **kwargs)
        self._filter_inactive = True
        self._filter_standard = False
        self._filter_library = False
        self._sort_by_type = True
        # Disable case sensitivity
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)

    def _type_sort(self, l_index, r_index):
        if not self._sort_by_type:
            return None

        l_is_library = l_index.data(PROJECT_IS_LIBRARY_ROLE)
        r_is_library = r_index.data(PROJECT_IS_LIBRARY_ROLE)
        # Both hare project items
        if l_is_library is not None and r_is_library is not None:
            if l_is_library is r_is_library:
                return None
            if l_is_library:
                return False
            return True

        if l_index.data(LIBRARY_PROJECT_SEPARATOR_ROLE):
            if r_is_library is None:
                return False
            return r_is_library

        if r_index.data(LIBRARY_PROJECT_SEPARATOR_ROLE):
            if l_is_library is None:
                return True
            return l_is_library
        return None

    def lessThan(self, left_index, right_index):
        # Current project always on top
        # - make sure this is always first, before any other sorting
        #   e.g. type sort would move the item lower
        if left_index.data(PROJECT_IS_CURRENT_ROLE):
            return True
        if right_index.data(PROJECT_IS_CURRENT_ROLE):
            return False

        # Library separator should be before library projects
        result = self._type_sort(left_index, right_index)
        if result is not None:
            return result

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
        project_name = index.data(PROJECT_NAME_ROLE)
        if project_name is None:
            return True

        string_pattern = self.filterRegularExpression().pattern()
        if string_pattern:
            return string_pattern.lower() in project_name.lower()

        # Current project keep always visible
        default = super(ProjectSortFilterProxy, self).filterAcceptsRow(
            source_row, source_parent
        )
        if not default:
            return default

        # Make sure current project is visible
        if index.data(PROJECT_IS_CURRENT_ROLE):
            return True

        if (
            self._filter_inactive
            and not index.data(PROJECT_IS_ACTIVE_ROLE)
        ):
            return False

        if (
            self._filter_standard
            and not index.data(PROJECT_IS_LIBRARY_ROLE)
        ):
            return False

        if (
            self._filter_library
            and index.data(PROJECT_IS_LIBRARY_ROLE)
        ):
            return False
        return True

    def _custom_index_filter(self, index):
        return bool(index.data(PROJECT_IS_ACTIVE_ROLE))

    def is_active_filter_enabled(self):
        return self._filter_inactive

    def set_active_filter_enabled(self, enabled):
        if self._filter_inactive == enabled:
            return
        self._filter_inactive = enabled
        self.invalidateFilter()

    def set_library_filter_enabled(self, enabled):
        if self._filter_library == enabled:
            return
        self._filter_library = enabled
        self.invalidateFilter()

    def set_standard_filter_enabled(self, enabled):
        if self._filter_standard == enabled:
            return
        self._filter_standard = enabled
        self.invalidateFilter()

    def set_sort_by_type(self, enabled):
        if self._sort_by_type is enabled:
            return
        self._sort_by_type = enabled
        self.invalidate()


class ProjectsCombobox(QtWidgets.QWidget):
    refreshed = QtCore.Signal()
    selection_changed = QtCore.Signal()

    def __init__(self, controller, parent, handle_expected_selection=False):
        super(ProjectsCombobox, self).__init__(parent)

        projects_combobox = QtWidgets.QComboBox(self)
        combobox_delegate = QtWidgets.QStyledItemDelegate(projects_combobox)
        projects_combobox.setItemDelegate(combobox_delegate)
        projects_model = ProjectsQtModel(controller)
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
        self._select_item_visible = False

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

    def get_selected_project_name(self):
        """Name of selected project.

        Returns:
            Union[str, None]: Name of selected project, or None if no project
        """

        idx = self._projects_combobox.currentIndex()
        if idx < 0:
            return None
        return self._projects_combobox.itemData(idx, PROJECT_NAME_ROLE)

    def set_current_context_project(self, project_name):
        self._projects_model.set_current_context_project(project_name)
        self._projects_proxy_model.invalidateFilter()

    def set_select_item_visible(self, visible):
        self._select_item_visible = visible
        self._projects_model.set_select_item_visible(visible)
        self._update_select_item_visiblity()

    def set_libraries_separator_visible(self, visible):
        self._projects_model.set_libraries_separator_visible(visible)

    def is_active_filter_enabled(self):
        return self._projects_proxy_model.is_active_filter_enabled()

    def set_active_filter_enabled(self, enabled):
        return self._projects_proxy_model.set_active_filter_enabled(enabled)

    def set_standard_filter_enabled(self, enabled):
        return self._projects_proxy_model.set_standard_filter_enabled(enabled)

    def set_library_filter_enabled(self, enabled):
        return self._projects_proxy_model.set_library_filter_enabled(enabled)

    def _update_select_item_visiblity(self, **kwargs):
        if not self._select_item_visible:
            return
        if "project_name" not in kwargs:
            project_name = self.get_selected_project_name()
        else:
            project_name = kwargs.get("project_name")

        # Hide the item if a project is selected
        self._projects_model.set_selected_project(project_name)

    def _on_current_index_changed(self, idx):
        if not self._listen_selection_change:
            return
        project_name = self._projects_combobox.itemData(
            idx, PROJECT_NAME_ROLE)
        self._update_select_item_visiblity(project_name=project_name)
        self._controller.set_selected_project(project_name)
        self.selection_changed.emit()

    def _on_model_refresh(self):
        self._projects_proxy_model.sort(0)
        self._projects_proxy_model.invalidateFilter()
        if self._expected_selection:
            self._set_expected_selection()
        self._update_select_item_visiblity()
        self.refreshed.emit()

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
            if project_name != self.get_selected_project_name():
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
