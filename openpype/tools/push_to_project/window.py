import collections

from qtpy import QtWidgets, QtGui, QtCore

from openpype.style import load_stylesheet, get_app_icon_path
from openpype.tools.utils import (
    PlaceholderLineEdit,
    SeparatorWidget,
    get_asset_icon_by_name,
    set_style_property,
)
from openpype.tools.utils.views import DeselectableTreeView

from .control_context import PushToContextController

PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
ASSET_ID_ROLE = QtCore.Qt.UserRole + 3
TASK_NAME_ROLE = QtCore.Qt.UserRole + 4
TASK_TYPE_ROLE = QtCore.Qt.UserRole + 5


class ProjectsModel(QtGui.QStandardItemModel):
    empty_text = "< Empty >"
    refreshing_text = "< Refreshing >"
    select_project_text = "< Select Project >"

    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(ProjectsModel, self).__init__()
        self._controller = controller

        self.event_system.add_callback(
            "projects.refresh.finished", self._on_refresh_finish
        )

        placeholder_item = QtGui.QStandardItem(self.empty_text)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])
        items = {None: placeholder_item}

        self._placeholder_item = placeholder_item
        self._items = items

    @property
    def event_system(self):
        return self._controller.event_system

    def _on_refresh_finish(self):
        root_item = self.invisibleRootItem()
        project_names = self._controller.model.get_projects()

        if not project_names:
            placeholder_text = self.empty_text
        else:
            placeholder_text = self.select_project_text
        self._placeholder_item.setData(placeholder_text, QtCore.Qt.DisplayRole)

        new_items = []
        if None not in self._items:
            new_items.append(self._placeholder_item)

        current_project_names = set(self._items.keys())
        for project_name in current_project_names - set(project_names):
            if project_name is None:
                continue
            item = self._items.pop(project_name)
            root_item.takeRow(item.row())

        for project_name in project_names:
            if project_name in self._items:
                continue
            item = QtGui.QStandardItem(project_name)
            item.setData(project_name, PROJECT_NAME_ROLE)
            new_items.append(item)

        if new_items:
            root_item.appendRows(new_items)
        self.refreshed.emit()


class ProjectProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self):
        super(ProjectProxyModel, self).__init__()
        self._filter_empty_projects = False

    def set_filter_empty_project(self, filter_empty_projects):
        if filter_empty_projects == self._filter_empty_projects:
            return
        self._filter_empty_projects = filter_empty_projects
        self.invalidate()

    def filterAcceptsRow(self, row, parent):
        if not self._filter_empty_projects:
            return True
        model = self.sourceModel()
        source_index = model.index(row, self.filterKeyColumn(), parent)
        if model.data(source_index, PROJECT_NAME_ROLE) is None:
            return False
        return True


class AssetsModel(QtGui.QStandardItemModel):
    items_changed = QtCore.Signal()
    empty_text = "< Empty >"

    def __init__(self, controller):
        super(AssetsModel, self).__init__()
        self._controller = controller

        placeholder_item = QtGui.QStandardItem(self.empty_text)
        placeholder_item.setFlags(QtCore.Qt.ItemIsEnabled)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])

        self.event_system.add_callback(
            "project.changed", self._on_project_change
        )
        self.event_system.add_callback(
            "assets.refresh.started", self._on_refresh_start
        )
        self.event_system.add_callback(
            "assets.refresh.finished", self._on_refresh_finish
        )

        self._items = {None: placeholder_item}

        self._placeholder_item = placeholder_item
        self._last_project = None

    @property
    def event_system(self):
        return self._controller.event_system

    def _clear(self):
        placeholder_in = False
        root_item = self.invisibleRootItem()
        for row in reversed(range(root_item.rowCount())):
            item = root_item.child(row)
            asset_id = item.data(ASSET_ID_ROLE)
            if asset_id is None:
                placeholder_in = True
                continue
            root_item.removeRow(item.row())

        for key in tuple(self._items.keys()):
            if key is not None:
                self._items.pop(key)

        if not placeholder_in:
            root_item.appendRows([self._placeholder_item])
        self._items[None] = self._placeholder_item

    def _on_project_change(self, event):
        project_name = event["project_name"]
        if project_name == self._last_project:
            return

        self._last_project = project_name
        self._clear()
        self.items_changed.emit()

    def _on_refresh_start(self, event):
        pass

    def _on_refresh_finish(self, event):
        event_project_name = event["project_name"]
        project_name = self._controller.selection_model.project_name
        if event_project_name != project_name:
            return

        self._last_project = event["project_name"]
        if project_name is None:
            if None not in self._items:
                self._clear()
                self.items_changed.emit()
            return

        asset_items_by_id = self._controller.model.get_assets(project_name)
        if not asset_items_by_id:
            self._clear()
            self.items_changed.emit()
            return

        assets_by_parent_id = collections.defaultdict(list)
        for asset_item in asset_items_by_id.values():
            assets_by_parent_id[asset_item.parent_id].append(asset_item)

        root_item = self.invisibleRootItem()
        if None in self._items:
            self._items.pop(None)
            root_item.takeRow(self._placeholder_item.row())

        items_to_remove = set(self._items) - set(asset_items_by_id.keys())
        hierarchy_queue = collections.deque()
        hierarchy_queue.append((None, root_item))
        while hierarchy_queue:
            parent_id, parent_item = hierarchy_queue.popleft()
            new_items = []
            for asset_item in assets_by_parent_id[parent_id]:
                item = self._items.get(asset_item.id)
                if item is None:
                    item = QtGui.QStandardItem()
                    item.setFlags(
                        QtCore.Qt.ItemIsSelectable
                        | QtCore.Qt.ItemIsEnabled
                    )
                    new_items.append(item)
                    self._items[asset_item.id] = item

                elif item.parent() is not parent_item:
                    new_items.append(item)

                icon = get_asset_icon_by_name(
                    asset_item.icon_name, asset_item.icon_color
                )
                item.setData(asset_item.name, QtCore.Qt.DisplayRole)
                item.setData(icon, QtCore.Qt.DecorationRole)
                item.setData(asset_item.id, ASSET_ID_ROLE)

                hierarchy_queue.append((asset_item.id, item))

            if new_items:
                parent_item.appendRows(new_items)

        for item_id in items_to_remove:
            item = self._items.pop(item_id, None)
            if item is None:
                continue
            row = item.row()
            if row < 0:
                continue
            parent = item.parent()
            if parent is None:
                parent = root_item
            parent.takeRow(row)

        self.items_changed.emit()


class TasksModel(QtGui.QStandardItemModel):
    items_changed = QtCore.Signal()
    empty_text = "< Empty >"

    def __init__(self, controller):
        super(TasksModel, self).__init__()
        self._controller = controller

        placeholder_item = QtGui.QStandardItem(self.empty_text)
        placeholder_item.setFlags(QtCore.Qt.ItemIsEnabled)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])

        self.event_system.add_callback(
            "project.changed", self._on_project_change
        )
        self.event_system.add_callback(
            "assets.refresh.finished", self._on_asset_refresh_finish
        )
        self.event_system.add_callback(
            "asset.changed", self._on_asset_change
        )

        self._items = {None: placeholder_item}

        self._placeholder_item = placeholder_item
        self._last_project = None

    @property
    def event_system(self):
        return self._controller.event_system

    def _clear(self):
        placeholder_in = False
        root_item = self.invisibleRootItem()
        for row in reversed(range(root_item.rowCount())):
            item = root_item.child(row)
            task_name = item.data(TASK_NAME_ROLE)
            if task_name is None:
                placeholder_in = True
                continue
            root_item.removeRow(item.row())

        for key in tuple(self._items.keys()):
            if key is not None:
                self._items.pop(key)

        if not placeholder_in:
            root_item.appendRows([self._placeholder_item])
        self._items[None] = self._placeholder_item

    def _on_project_change(self, event):
        project_name = event["project_name"]
        if project_name == self._last_project:
            return

        self._last_project = project_name
        self._clear()
        self.items_changed.emit()

    def _on_asset_refresh_finish(self, event):
        self._refresh(event["project_name"])

    def _on_asset_change(self, event):
        self._refresh(event["project_name"])

    def _refresh(self, new_project_name):
        project_name = self._controller.selection_model.project_name
        if new_project_name != project_name:
            return

        self._last_project = project_name
        if project_name is None:
            if None not in self._items:
                self._clear()
                self.items_changed.emit()
            return

        asset_id = self._controller.selection_model.asset_id
        task_items = self._controller.model.get_tasks(
            project_name, asset_id
        )
        if not task_items:
            self._clear()
            self.items_changed.emit()
            return

        root_item = self.invisibleRootItem()
        if None in self._items:
            self._items.pop(None)
            root_item.takeRow(self._placeholder_item.row())

        new_items = []
        task_names = set()
        for task_item in task_items:
            task_name = task_item.name
            item = self._items.get(task_name)
            if item is None:
                item = QtGui.QStandardItem()
                item.setFlags(
                    QtCore.Qt.ItemIsSelectable
                    | QtCore.Qt.ItemIsEnabled
                )
                new_items.append(item)
                self._items[task_name] = item

            item.setData(task_name, QtCore.Qt.DisplayRole)
            item.setData(task_name, TASK_NAME_ROLE)
            item.setData(task_item.task_type, TASK_TYPE_ROLE)

        if new_items:
            root_item.appendRows(new_items)

        items_to_remove = set(self._items) - task_names
        for item_id in items_to_remove:
            item = self._items.pop(item_id, None)
            if item is None:
                continue
            parent = item.parent()
            if parent is not None:
                parent.removeRow(item.row())

        self.items_changed.emit()


class PushToContextSelectWindow(QtWidgets.QDialog):
    def __init__(
        self, controller=None, library_filter=True, context_only=False
    ):
        super(PushToContextSelectWindow, self).__init__()
        if controller is None:
            controller = PushToContextController(library_filter=library_filter)
        self._controller = controller
        self.context_only = context_only
        self.context = None

        self.setWindowTitle("Push to project (select context)")
        self.setWindowIcon(QtGui.QIcon(get_app_icon_path()))

        main_context_widget = QtWidgets.QWidget(self)

        header_widget = QtWidgets.QWidget(main_context_widget)

        header_label = QtWidgets.QLabel(controller.src_label, header_widget)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(header_label)

        main_splitter = QtWidgets.QSplitter(
            QtCore.Qt.Horizontal, main_context_widget
        )

        context_widget = QtWidgets.QWidget(main_splitter)

        project_combobox = QtWidgets.QComboBox(context_widget)
        project_model = ProjectsModel(controller)
        project_proxy = ProjectProxyModel()
        project_proxy.setSourceModel(project_model)
        project_proxy.setDynamicSortFilter(True)
        project_delegate = QtWidgets.QStyledItemDelegate()
        project_combobox.setItemDelegate(project_delegate)
        project_combobox.setModel(project_proxy)

        asset_task_splitter = QtWidgets.QSplitter(
            QtCore.Qt.Vertical, context_widget
        )

        asset_view = DeselectableTreeView(asset_task_splitter)
        asset_view.setHeaderHidden(True)
        asset_model = AssetsModel(controller)
        asset_proxy = QtCore.QSortFilterProxyModel()
        asset_proxy.setSourceModel(asset_model)
        asset_proxy.setDynamicSortFilter(True)
        asset_view.setModel(asset_proxy)

        task_view = QtWidgets.QListView(asset_task_splitter)
        task_proxy = QtCore.QSortFilterProxyModel()
        task_model = TasksModel(controller)
        task_proxy.setSourceModel(task_model)
        task_proxy.setDynamicSortFilter(True)
        task_view.setModel(task_proxy)

        asset_task_splitter.addWidget(asset_view)
        asset_task_splitter.addWidget(task_view)

        context_layout = QtWidgets.QVBoxLayout(context_widget)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.addWidget(project_combobox, 0)
        context_layout.addWidget(asset_task_splitter, 1)

        # --- Inputs widget ---
        inputs_widget = QtWidgets.QWidget(main_splitter)

        asset_name_input = PlaceholderLineEdit(inputs_widget)
        asset_name_input.setPlaceholderText("< Name of new asset >")
        asset_name_input.setObjectName("ValidatedLineEdit")

        variant_input = PlaceholderLineEdit(inputs_widget)
        variant_input.setPlaceholderText("< Variant >")
        variant_input.setObjectName("ValidatedLineEdit")

        comment_input = PlaceholderLineEdit(inputs_widget)
        comment_input.setPlaceholderText("< Publish comment >")

        inputs_layout = QtWidgets.QFormLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.addRow("New asset name", asset_name_input)
        inputs_layout.addRow("Variant", variant_input)
        inputs_layout.addRow("Comment", comment_input)

        main_splitter.addWidget(context_widget)
        main_splitter.addWidget(inputs_widget)

        # --- Buttons widget ---
        btns_widget = QtWidgets.QWidget(self)
        cancel_btn = QtWidgets.QPushButton("Cancel", btns_widget)
        push_btn = QtWidgets.QPushButton("Push", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(cancel_btn, 0)
        btns_layout.addWidget(push_btn, 0)

        sep_1 = SeparatorWidget(parent=main_context_widget)
        sep_2 = SeparatorWidget(parent=main_context_widget)
        main_context_layout = QtWidgets.QVBoxLayout(main_context_widget)
        main_context_layout.addWidget(header_widget, 0)
        main_context_layout.addWidget(sep_1, 0)
        main_context_layout.addWidget(main_splitter, 1)
        main_context_layout.addWidget(sep_2, 0)
        main_context_layout.addWidget(btns_widget, 0)

        # NOTE This was added in hurry
        # - should be reorganized and changed styles
        overlay_widget = QtWidgets.QFrame(self)
        overlay_widget.setObjectName("OverlayFrame")

        overlay_label = QtWidgets.QLabel(overlay_widget)
        overlay_label.setAlignment(QtCore.Qt.AlignCenter)

        overlay_btns_widget = QtWidgets.QWidget(overlay_widget)
        overlay_btns_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Add try again button (requires changes in controller)
        overlay_try_btn = QtWidgets.QPushButton(
            "Try again", overlay_btns_widget
        )
        overlay_close_btn = QtWidgets.QPushButton(
            "Close", overlay_btns_widget
        )

        overlay_btns_layout = QtWidgets.QHBoxLayout(overlay_btns_widget)
        overlay_btns_layout.addStretch(1)
        overlay_btns_layout.addWidget(overlay_try_btn, 0)
        overlay_btns_layout.addWidget(overlay_close_btn, 0)
        overlay_btns_layout.addStretch(1)

        overlay_layout = QtWidgets.QVBoxLayout(overlay_widget)
        overlay_layout.addWidget(overlay_label, 0)
        overlay_layout.addWidget(overlay_btns_widget, 0)
        overlay_layout.setAlignment(QtCore.Qt.AlignCenter)

        main_layout = QtWidgets.QStackedLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_context_widget)
        main_layout.addWidget(overlay_widget)
        main_layout.setStackingMode(QtWidgets.QStackedLayout.StackAll)
        main_layout.setCurrentWidget(main_context_widget)

        show_timer = QtCore.QTimer()
        show_timer.setInterval(1)

        main_thread_timer = QtCore.QTimer()
        main_thread_timer.setInterval(10)

        user_input_changed_timer = QtCore.QTimer()
        user_input_changed_timer.setInterval(200)
        user_input_changed_timer.setSingleShot(True)

        main_thread_timer.timeout.connect(self._on_main_thread_timer)
        show_timer.timeout.connect(self._on_show_timer)
        user_input_changed_timer.timeout.connect(self._on_user_input_timer)
        asset_name_input.textChanged.connect(self._on_new_asset_change)
        variant_input.textChanged.connect(self._on_variant_change)
        comment_input.textChanged.connect(self._on_comment_change)
        project_model.refreshed.connect(self._on_projects_refresh)
        project_combobox.currentIndexChanged.connect(self._on_project_change)
        asset_view.selectionModel().selectionChanged.connect(
            self._on_asset_change
        )
        asset_model.items_changed.connect(self._on_asset_model_change)
        task_view.selectionModel().selectionChanged.connect(
            self._on_task_change
        )
        task_model.items_changed.connect(self._on_task_model_change)
        push_btn.clicked.connect(self._on_select_click)
        cancel_btn.clicked.connect(self._on_close_click)
        overlay_close_btn.clicked.connect(self._on_close_click)
        overlay_try_btn.clicked.connect(self._on_try_again_click)

        controller.event_system.add_callback(
            "new_asset_name.changed", self._on_controller_new_asset_change
        )
        controller.event_system.add_callback(
            "variant.changed", self._on_controller_variant_change
        )
        controller.event_system.add_callback(
            "comment.changed", self._on_controller_comment_change
        )
        controller.event_system.add_callback(
            "submission.enabled.changed", self._on_submission_change
        )
        controller.event_system.add_callback(
            "source.changed", self._on_controller_source_change
        )
        controller.event_system.add_callback(
            "submit.started", self._on_controller_submit_start
        )
        controller.event_system.add_callback(
            "submit.finished", self._on_controller_submit_end
        )
        controller.event_system.add_callback(
            "push.message.added", self._on_push_message
        )

        self._main_layout = main_layout

        self._main_context_widget = main_context_widget

        self._header_label = header_label
        self._main_splitter = main_splitter

        self._project_combobox = project_combobox
        self._project_model = project_model
        self._project_proxy = project_proxy
        self._project_delegate = project_delegate

        self._asset_view = asset_view
        self._asset_model = asset_model
        self._asset_proxy_model = asset_proxy

        self._task_view = task_view
        self._task_proxy_model = task_proxy

        self._variant_input = variant_input
        self._asset_name_input = asset_name_input
        self._comment_input = comment_input

        self._push_btn = push_btn

        self._overlay_widget = overlay_widget
        self._overlay_close_btn = overlay_close_btn
        self._overlay_try_btn = overlay_try_btn
        self._overlay_label = overlay_label

        self._user_input_changed_timer = user_input_changed_timer
        # Store current value on input text change
        #   The value is unset when is passed to controller
        # The goal is to have controll over changes happened during user change
        #   in UI and controller auto-changes
        self._variant_input_text = None
        self._new_asset_name_input_text = None
        self._comment_input_text = None
        self._show_timer = show_timer
        self._show_counter = 2
        self._first_show = True

        self._main_thread_timer = main_thread_timer
        self._main_thread_timer_can_stop = True
        self._last_submit_message = None
        self._process_item = None

        push_btn.setEnabled(False)
        overlay_close_btn.setVisible(False)
        overlay_try_btn.setVisible(False)

        if controller.user_values.new_asset_name:
            asset_name_input.setText(controller.user_values.new_asset_name)
        if controller.user_values.variant:
            variant_input.setText(controller.user_values.variant)
        self._invalidate_variant()
        self._invalidate_new_asset_name()

    @property
    def controller(self):
        return self._controller

    def showEvent(self, event):
        super(PushToContextSelectWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(load_stylesheet())
            self._invalidate_variant()
            self._show_timer.start()

    def _on_show_timer(self):
        if self._show_counter == 0:
            self._show_timer.stop()
            return

        self._show_counter -= 1
        if self._show_counter == 1:
            width = 740
            height = 640
            inputs_width = 360
            self.resize(width, height)
            self._main_splitter.setSizes([width - inputs_width, inputs_width])

        if self._show_counter > 0:
            return

        self._controller.model.refresh_projects()

    def _on_new_asset_change(self, text):
        self._new_asset_name_input_text = text
        self._user_input_changed_timer.start()

    def _on_variant_change(self, text):
        self._variant_input_text = text
        self._user_input_changed_timer.start()

    def _on_comment_change(self, text):
        self._comment_input_text = text
        self._user_input_changed_timer.start()

    def _on_user_input_timer(self):
        asset_name = self._new_asset_name_input_text
        if asset_name is not None:
            self._new_asset_name_input_text = None
            self._controller.user_values.set_new_asset(asset_name)

        variant = self._variant_input_text
        if variant is not None:
            self._variant_input_text = None
            self._controller.user_values.set_variant(variant)

        comment = self._comment_input_text
        if comment is not None:
            self._comment_input_text = None
            self._controller.user_values.set_comment(comment)

    def _on_controller_new_asset_change(self, event):
        asset_name = event["changes"]["new_asset_name"]["new"]
        if (
            self._new_asset_name_input_text is None
            and asset_name != self._asset_name_input.text()
        ):
            self._asset_name_input.setText(asset_name)

        self._invalidate_new_asset_name()

    def _on_controller_variant_change(self, event):
        is_valid_changes = event["changes"]["is_valid"]
        variant = event["changes"]["variant"]["new"]
        if (
            self._variant_input_text is None
            and variant != self._variant_input.text()
        ):
            self._variant_input.setText(variant)

        if is_valid_changes["old"] != is_valid_changes["new"]:
            self._invalidate_variant()

    def _on_controller_comment_change(self, event):
        comment = event["comment"]
        if (
            self._comment_input_text is None
            and comment != self._comment_input.text()
        ):
            self._comment_input.setText(comment)

    def _on_controller_source_change(self):
        self._header_label.setText(self._controller.src_label)

    def _invalidate_new_asset_name(self):
        asset_name = self._controller.user_values.new_asset_name
        self._task_view.setVisible(not asset_name)

        valid = None
        if asset_name:
            valid = self._controller.user_values.is_new_asset_name_valid

        state = ""
        if valid is True:
            state = "valid"
        elif valid is False:
            state = "invalid"
        set_style_property(self._asset_name_input, "state", state)

    def _invalidate_variant(self):
        valid = self._controller.user_values.is_variant_valid
        state = "invalid"
        if valid is True:
            state = "valid"
        set_style_property(self._variant_input, "state", state)

    def _on_projects_refresh(self):
        self._project_proxy.sort(0, QtCore.Qt.AscendingOrder)

    def _on_project_change(self):
        idx = self._project_combobox.currentIndex()
        if idx < 0:
            self._project_proxy.set_filter_empty_project(False)
            return

        project_name = self._project_combobox.itemData(idx, PROJECT_NAME_ROLE)
        self._project_proxy.set_filter_empty_project(project_name is not None)
        self._controller.selection_model.select_project(project_name)

    def _on_asset_change(self):
        indexes = self._asset_view.selectedIndexes()
        index = next(iter(indexes), None)
        asset_id = None
        if index is not None:
            model = self._asset_view.model()
            asset_id = model.data(index, ASSET_ID_ROLE)
        self._controller.selection_model.select_asset(asset_id)

    def _on_asset_model_change(self):
        self._asset_proxy_model.sort(0, QtCore.Qt.AscendingOrder)

    def _on_task_model_change(self):
        self._task_proxy_model.sort(0, QtCore.Qt.AscendingOrder)

    def _on_task_change(self):
        indexes = self._task_view.selectedIndexes()
        index = next(iter(indexes), None)
        task_name = None
        if index is not None:
            model = self._task_view.model()
            task_name = model.data(index, TASK_NAME_ROLE)
        self._controller.selection_model.select_task(task_name)

    def _on_submission_change(self, event):
        self._push_btn.setEnabled(event["enabled"])

    def _on_close_click(self):
        self.close()

    def _on_select_click(self):
        result = self._controller.submit(
            wait=True, context_only=self.context_only
        )

        if self.context_only:
            self.context = {
                "project_name": self._controller.selection_model.project_name,
                "asset_id": self._controller.selection_model.asset_id,
                "task_name": self._controller.selection_model.task_name,
                "variant": self._controller.user_values.variant,
                "comment": self._controller.user_values.comment,
                "asset_name": self._controller.user_values.new_asset_name
            }
            self.close()

        self._process_item = result

    def _on_try_again_click(self):
        self._process_item = None
        self._last_submit_message = None

        self._overlay_close_btn.setVisible(False)
        self._overlay_try_btn.setVisible(False)
        self._main_layout.setCurrentWidget(self._main_context_widget)

    def _on_main_thread_timer(self):
        if self._last_submit_message:
            self._overlay_label.setText(self._last_submit_message)
            self._last_submit_message = None

        process_status = self._process_item.status
        push_failed = process_status.failed
        fail_traceback = process_status.traceback
        if self._main_thread_timer_can_stop:
            self._main_thread_timer.stop()
            self._overlay_close_btn.setVisible(True)
            if push_failed and not fail_traceback:
                self._overlay_try_btn.setVisible(True)

        if push_failed:
            message = "Push Failed:\n{}".format(process_status.fail_reason)
            if fail_traceback:
                message += "\n{}".format(fail_traceback)
            self._overlay_label.setText(message)
            set_style_property(self._overlay_close_btn, "state", "error")

        if self._main_thread_timer_can_stop:
            # Join thread in controller
            self._controller.wait_for_process_thread()
            # Reset process item to None
            self._process_item = None

    def _on_controller_submit_start(self):
        self._main_thread_timer_can_stop = False
        self._main_thread_timer.start()
        self._main_layout.setCurrentWidget(self._overlay_widget)
        self._overlay_label.setText("Submittion started")

    def _on_controller_submit_end(self):
        self._main_thread_timer_can_stop = True

    def _on_push_message(self, event):
        self._last_submit_message = event["message"]
