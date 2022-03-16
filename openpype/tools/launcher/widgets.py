import copy
import time
import collections
from Qt import QtWidgets, QtCore, QtGui
import qtawesome

from openpype.tools.flickcharm import FlickCharm
from openpype.tools.utils.assets_widget import SingleSelectAssetsWidget
from openpype.tools.utils.tasks_widget import TasksWidget

from .delegates import ActionDelegate
from . import lib
from .models import (
    ActionModel,
    ProjectModel,
    LauncherAssetsModel,
    AssetRecursiveSortFilterModel,
    LauncherTaskModel,
    LauncherTasksProxyModel
)
from .actions import ApplicationAction
from .constants import (
    ACTION_ROLE,
    GROUP_ROLE,
    VARIANT_GROUP_ROLE,
    ACTION_ID_ROLE,
    ANIMATION_START_ROLE,
    ANIMATION_STATE_ROLE,
    ANIMATION_LEN,
    FORCE_NOT_OPEN_WORKFILE_ROLE
)


class ProjectBar(QtWidgets.QWidget):
    def __init__(self, launcher_model, parent=None):
        super(ProjectBar, self).__init__(parent)

        project_combobox = QtWidgets.QComboBox(self)
        # Change delegate so stylysheets are applied
        project_delegate = QtWidgets.QStyledItemDelegate(project_combobox)
        project_combobox.setItemDelegate(project_delegate)
        model = ProjectModel(launcher_model)
        project_combobox.setModel(model)
        project_combobox.setRootModelIndex(QtCore.QModelIndex())

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(project_combobox)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Maximum
        )

        self._launcher_model = launcher_model
        self.project_delegate = project_delegate
        self.project_combobox = project_combobox
        self._model = model

        # Signals
        self.project_combobox.currentIndexChanged.connect(self.on_index_change)
        launcher_model.project_changed.connect(self._on_project_change)

        # Set current project by default if it's set.
        project_name = launcher_model.project_name
        if project_name:
            self.set_project(project_name)

    def _on_project_change(self, project_name):
        if self.get_current_project() == project_name:
            return
        self.set_project(project_name)

    def get_current_project(self):
        return self.project_combobox.currentText()

    def set_project(self, project_name):
        index = self.project_combobox.findText(project_name)
        if index < 0:
            # Try refresh combobox model
            self._launcher_model.refresh_projects()
            index = self.project_combobox.findText(project_name)

        if index >= 0:
            self.project_combobox.setCurrentIndex(index)

    def on_index_change(self, idx):
        if not self.isVisible():
            return

        project_name = self.get_current_project()
        self._launcher_model.set_project_name(project_name)


class LauncherTaskWidget(TasksWidget):
    def __init__(self, launcher_model, *args, **kwargs):
        self._launcher_model = launcher_model

        super(LauncherTaskWidget, self).__init__(*args, **kwargs)

    def _create_source_model(self):
        return LauncherTaskModel(self._launcher_model, self._dbcon)

    def _create_proxy_model(self, source_model):
        proxy = LauncherTasksProxyModel(self._launcher_model)
        proxy.setSourceModel(source_model)
        return proxy


class LauncherAssetsWidget(SingleSelectAssetsWidget):
    def __init__(self, launcher_model, *args, **kwargs):
        self._launcher_model = launcher_model

        super(LauncherAssetsWidget, self).__init__(*args, **kwargs)

        launcher_model.assets_refresh_started.connect(self._on_refresh_start)

        self.set_current_asset_btn_visibility(False)

    def _on_refresh_start(self):
        self._set_loading_state(loading=True, empty=True)
        self.refresh_triggered.emit()

    @property
    def refreshing(self):
        return self._model.refreshing

    def refresh(self):
        self._launcher_model.refresh_assets(force=True)

    def stop_refresh(self):
        raise ValueError("bug stop_refresh called")

    def _refresh_model(self, clear=False):
        raise ValueError("bug _refresh_model called")

    def _create_source_model(self):
        model = LauncherAssetsModel(self._launcher_model, self.dbcon)
        model.refreshed.connect(self._on_model_refresh)
        return model

    def _create_proxy_model(self, source_model):
        proxy = AssetRecursiveSortFilterModel(self._launcher_model)
        proxy.setSourceModel(source_model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        return proxy

    def _on_model_refresh(self, has_item):
        self._proxy.sort(0)
        self._set_loading_state(loading=False, empty=not has_item)
        self.refreshed.emit()

    def _on_filter_text_change(self, new_text):
        self._launcher_model.set_asset_name_filter(new_text)


class ActionBar(QtWidgets.QWidget):
    """Launcher interface"""

    action_clicked = QtCore.Signal(object)

    def __init__(self, launcher_model, dbcon, parent=None):
        super(ActionBar, self).__init__(parent)

        self._launcher_model = launcher_model
        self.dbcon = dbcon

        view = QtWidgets.QListView(self)
        view.setProperty("mode", "icon")
        view.setObjectName("IconView")
        view.setViewMode(QtWidgets.QListView.IconMode)
        view.setResizeMode(QtWidgets.QListView.Adjust)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setEditTriggers(QtWidgets.QListView.NoEditTriggers)
        view.setWrapping(True)
        view.setGridSize(QtCore.QSize(70, 75))
        view.setIconSize(QtCore.QSize(30, 30))
        view.setSpacing(0)
        view.setWordWrap(True)

        model = ActionModel(self.dbcon, self)
        view.setModel(model)

        # TODO better group delegate
        delegate = ActionDelegate(
            [GROUP_ROLE, VARIANT_GROUP_ROLE],
            self
        )
        view.setItemDelegate(delegate)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)

        self.model = model
        self.view = view

        self._animated_items = set()

        animation_timer = QtCore.QTimer()
        animation_timer.setInterval(50)
        animation_timer.timeout.connect(self._on_animation)
        self._animation_timer = animation_timer

        # Make view flickable
        flick = FlickCharm(parent=view)
        flick.activateOn(view)

        self.set_row_height(1)

        launcher_model.projects_refreshed.connect(self._on_projects_refresh)
        view.clicked.connect(self.on_clicked)
        view.customContextMenuRequested.connect(self.on_context_menu)

        self._context_menu = None
        self._discover_on_menu = False

    def discover_actions(self):
        if self._context_menu is not None:
            self._discover_on_menu = True
            return

        if self._animation_timer.isActive():
            self._animation_timer.stop()
        self.model.discover()

    def filter_actions(self):
        if self._animation_timer.isActive():
            self._animation_timer.stop()
        self.model.filter_actions()

    def set_row_height(self, rows):
        self.setMinimumHeight(rows * 75)

    def _on_projects_refresh(self):
        self.discover_actions()

    def _on_animation(self):
        time_now = time.time()
        for action_id in tuple(self._animated_items):
            item = self.model.items_by_id.get(action_id)
            if not item:
                self._animated_items.remove(action_id)
                continue

            start_time = item.data(ANIMATION_START_ROLE)
            if (time_now - start_time) > ANIMATION_LEN:
                item.setData(0, ANIMATION_STATE_ROLE)
                self._animated_items.remove(action_id)

        if not self._animated_items:
            self._animation_timer.stop()

        self.update()

    def _start_animation(self, index):
        # Offset refresh timout
        self._launcher_model.start_refresh_timer()
        action_id = index.data(ACTION_ID_ROLE)
        item = self.model.items_by_id.get(action_id)
        if item:
            item.setData(time.time(), ANIMATION_START_ROLE)
            item.setData(1, ANIMATION_STATE_ROLE)
            self._animated_items.add(action_id)
            self._animation_timer.start()

    def on_context_menu(self, point):
        """Creates menu to force skip opening last workfile."""
        index = self.view.indexAt(point)
        if not index.isValid():
            return

        action_item = index.data(ACTION_ROLE)
        if not self.model.is_application_action(action_item):
            return

        menu = QtWidgets.QMenu(self.view)
        checkbox = QtWidgets.QCheckBox("Skip opening last workfile.",
                                       menu)
        if index.data(FORCE_NOT_OPEN_WORKFILE_ROLE):
            checkbox.setChecked(True)

        action_id = index.data(ACTION_ID_ROLE)
        checkbox.stateChanged.connect(
            lambda: self.on_checkbox_changed(checkbox.isChecked(),
                                             action_id))
        action = QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(checkbox)

        menu.addAction(action)

        self._context_menu = menu
        global_point = self.mapToGlobal(point)
        menu.exec_(global_point)
        self._context_menu = None
        if self._discover_on_menu:
            self._discover_on_menu = False
            self.discover_actions()

    def on_checkbox_changed(self, is_checked, action_id):
        self.model.update_force_not_open_workfile_settings(is_checked,
                                                           action_id)
        self.view.update()
        if self._context_menu is not None:
            self._context_menu.close()

    def on_clicked(self, index):
        if not index or not index.isValid():
            return

        is_group = index.data(GROUP_ROLE)
        is_variant_group = index.data(VARIANT_GROUP_ROLE)
        if not is_group and not is_variant_group:
            action = index.data(ACTION_ROLE)
            # Change data of application action
            if issubclass(action, ApplicationAction):
                if index.data(FORCE_NOT_OPEN_WORKFILE_ROLE):
                    action.data["start_last_workfile"] = False
                else:
                    action.data.pop("start_last_workfile", None)
            self._start_animation(index)
            self.action_clicked.emit(action)
            return

        # Offset refresh timout
        self._launcher_model.start_refresh_timer()

        actions = index.data(ACTION_ROLE)

        menu = QtWidgets.QMenu(self)
        actions_mapping = {}

        if is_variant_group:
            for action in actions:
                menu_action = QtWidgets.QAction(
                    lib.get_action_label(action)
                )
                menu.addAction(menu_action)
                actions_mapping[menu_action] = action
        else:
            by_variant_label = collections.defaultdict(list)
            orders = []
            for action in actions:
                # Label variants
                label = getattr(action, "label", None)
                label_variant = getattr(action, "label_variant", None)
                if label_variant and not label:
                    label_variant = None

                if not label_variant:
                    orders.append(action)
                    continue

                if label not in orders:
                    orders.append(label)
                by_variant_label[label].append(action)

            for action_item in orders:
                actions = by_variant_label.get(action_item)
                if not actions:
                    action = action_item
                elif len(actions) == 1:
                    action = actions[0]
                else:
                    action = None

                if action:
                    menu_action = QtWidgets.QAction(
                        lib.get_action_label(action)
                    )
                    menu.addAction(menu_action)
                    actions_mapping[menu_action] = action
                    continue

                sub_menu = QtWidgets.QMenu(label, menu)
                for action in actions:
                    menu_action = QtWidgets.QAction(
                        lib.get_action_label(action)
                    )
                    sub_menu.addAction(menu_action)
                    actions_mapping[menu_action] = action

                menu.addMenu(sub_menu)

        result = menu.exec_(QtGui.QCursor.pos())
        if result:
            action = actions_mapping[result]
            self._start_animation(index)
            self.action_clicked.emit(action)


class ActionHistory(QtWidgets.QPushButton):
    trigger_history = QtCore.Signal(tuple)

    def __init__(self, parent=None):
        super(ActionHistory, self).__init__(parent=parent)

        self.max_history = 15

        self.setFixedWidth(25)
        self.setFixedHeight(25)

        self.setIcon(qtawesome.icon("fa.history", color="#CCCCCC"))
        self.setIconSize(QtCore.QSize(15, 15))

        self._history = []
        self.clicked.connect(self.show_history)

    def show_history(self):
        # Show history popup
        if not self._history:
            return

        widget = QtWidgets.QListWidget()
        widget.setSelectionMode(widget.NoSelection)
        widget.setStyleSheet("""
        * {
            font-family: "Courier New";
        }
        """)

        largest_label_num_chars = 0
        largest_action_label = max(len(x[0].label) for x in self._history)
        action_session_role = QtCore.Qt.UserRole + 1

        for action, session in reversed(self._history):
            project = session.get("AVALON_PROJECT")
            asset = session.get("AVALON_ASSET")
            task = session.get("AVALON_TASK")
            breadcrumb = " > ".join(x for x in [project, asset, task] if x)

            m = "{{action:{0}}} | {{breadcrumb}}".format(largest_action_label)
            label = m.format(action=action.label, breadcrumb=breadcrumb)

            icon = lib.get_action_icon(action)
            item = QtWidgets.QListWidgetItem(icon, label)
            item.setData(action_session_role, (action, session))

            largest_label_num_chars = max(largest_label_num_chars, len(label))

            widget.addItem(item)

        # Show history
        dialog = QtWidgets.QDialog(parent=self)
        dialog.setWindowTitle("Action History")
        dialog.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup
        )
        dialog.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored
        )

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

        def on_clicked(index):
            data = index.data(action_session_role)
            self.trigger_history.emit(data)
            dialog.close()

        widget.clicked.connect(on_clicked)

        # padding + icon + text
        width = 40 + (largest_label_num_chars * 7)
        entry_height = 21
        height = entry_height * len(self._history)

        point = QtGui.QCursor().pos()
        dialog.setGeometry(
            point.x() - width,
            point.y() - height,
            width,
            height
        )
        dialog.exec_()

        self.widget_popup = widget

    def add_action(self, action, session):
        key = (action, copy.deepcopy(session))

        # Remove entry if already exists
        if key in self._history:
            self._history.remove(key)

        self._history.append(key)

        # Slice the end of the list if we exceed the max history
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def clear_history(self):
        self._history.clear()


class SlidePageWidget(QtWidgets.QStackedWidget):
    """Stacked widget that nicely slides between its pages"""

    directions = {
        "left": QtCore.QPoint(-1, 0),
        "right": QtCore.QPoint(1, 0),
        "up": QtCore.QPoint(0, 1),
        "down": QtCore.QPoint(0, -1)
    }

    def slide_view(self, index, direction="right"):
        if self.currentIndex() == index:
            return

        offset_direction = self.directions.get(direction)
        if offset_direction is None:
            print("BUG: invalid slide direction: {}".format(direction))
            return

        width = self.frameRect().width()
        height = self.frameRect().height()
        offset = QtCore.QPoint(
            offset_direction.x() * width,
            offset_direction.y() * height
        )

        new_page = self.widget(index)
        new_page.setGeometry(0, 0, width, height)
        curr_pos = new_page.pos()
        new_page.move(curr_pos + offset)
        new_page.show()
        new_page.raise_()

        current_page = self.currentWidget()

        b_pos = QtCore.QByteArray(b"pos")

        anim_old = QtCore.QPropertyAnimation(current_page, b_pos, self)
        anim_old.setDuration(250)
        anim_old.setStartValue(curr_pos)
        anim_old.setEndValue(curr_pos - offset)
        anim_old.setEasingCurve(QtCore.QEasingCurve.OutQuad)

        anim_new = QtCore.QPropertyAnimation(new_page, b_pos, self)
        anim_new.setDuration(250)
        anim_new.setStartValue(curr_pos + offset)
        anim_new.setEndValue(curr_pos)
        anim_new.setEasingCurve(QtCore.QEasingCurve.OutQuad)

        anim_group = QtCore.QParallelAnimationGroup(self)
        anim_group.addAnimation(anim_old)
        anim_group.addAnimation(anim_new)

        def slide_finished():
            self.setCurrentWidget(new_page)

        anim_group.finished.connect(slide_finished)
        anim_group.start()
