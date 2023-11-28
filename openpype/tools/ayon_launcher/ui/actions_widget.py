import time
import collections

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.flickcharm import FlickCharm
from openpype.tools.ayon_utils.widgets import get_qt_icon

from .resources import get_options_image_path

ANIMATION_LEN = 7

ACTION_ID_ROLE = QtCore.Qt.UserRole + 1
ACTION_IS_APPLICATION_ROLE = QtCore.Qt.UserRole + 2
ACTION_IS_GROUP_ROLE = QtCore.Qt.UserRole + 3
ACTION_SORT_ROLE = QtCore.Qt.UserRole + 4
ANIMATION_START_ROLE = QtCore.Qt.UserRole + 5
ANIMATION_STATE_ROLE = QtCore.Qt.UserRole + 6
FORCE_NOT_OPEN_WORKFILE_ROLE = QtCore.Qt.UserRole + 7


def _variant_label_sort_getter(action_item):
    """Get variant label value for sorting.

    Make sure the output value is a string.

    Args:
        action_item (ActionItem): Action item.

    Returns:
        str: Variant label or empty string.
    """

    return action_item.variant_label or ""


class ActionsQtModel(QtGui.QStandardItemModel):
    """Qt model for actions.

    Args:
        controller (AbstractLauncherFrontEnd): Controller instance.
    """

    refreshed = QtCore.Signal()

    def __init__(self, controller):
        super(ActionsQtModel, self).__init__()

        controller.register_event_callback(
            "selection.project.changed",
            self._on_selection_project_changed,
        )
        controller.register_event_callback(
            "selection.folder.changed",
            self._on_selection_folder_changed,
        )
        controller.register_event_callback(
            "selection.task.changed",
            self._on_selection_task_changed,
        )

        self._controller = controller

        self._items_by_id = {}
        self._action_items_by_id = {}
        self._groups_by_id = {}

        self._selected_project_name = None
        self._selected_folder_id = None
        self._selected_task_id = None

    def get_selected_project_name(self):
        return self._selected_project_name

    def get_selected_folder_id(self):
        return self._selected_folder_id

    def get_selected_task_id(self):
        return self._selected_task_id

    def get_group_items(self, action_id):
        return self._groups_by_id[action_id]

    def get_item_by_id(self, action_id):
        return self._items_by_id.get(action_id)

    def get_action_item_by_id(self, action_id):
        return self._action_items_by_id.get(action_id)

    def _clear_items(self):
        self._items_by_id = {}
        self._action_items_by_id = {}
        self._groups_by_id = {}
        root = self.invisibleRootItem()
        root.removeRows(0, root.rowCount())

    def refresh(self):
        items = self._controller.get_action_items(
            self._selected_project_name,
            self._selected_folder_id,
            self._selected_task_id,
        )
        if not items:
            self._clear_items()
            self.refreshed.emit()
            return

        root_item = self.invisibleRootItem()

        all_action_items_info = []
        items_by_label = collections.defaultdict(list)
        for item in items:
            if not item.variant_label:
                all_action_items_info.append((item, False))
            else:
                items_by_label[item.label].append(item)

        groups_by_id = {}
        for action_items in items_by_label.values():
            action_items.sort(key=_variant_label_sort_getter, reverse=True)
            first_item = next(iter(action_items))
            all_action_items_info.append((first_item, len(action_items) > 1))
            groups_by_id[first_item.identifier] = action_items

        new_items = []
        items_by_id = {}
        action_items_by_id = {}
        for action_item_info in all_action_items_info:
            action_item, is_group = action_item_info
            icon = get_qt_icon(action_item.icon)
            if is_group:
                label = action_item.label
            else:
                label = action_item.full_label

            item = self._items_by_id.get(action_item.identifier)
            if item is None:
                item = QtGui.QStandardItem()
                item.setData(action_item.identifier, ACTION_ID_ROLE)
                new_items.append(item)

            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setData(label, QtCore.Qt.DisplayRole)
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setData(is_group, ACTION_IS_GROUP_ROLE)
            item.setData(action_item.order, ACTION_SORT_ROLE)
            item.setData(
                action_item.is_application, ACTION_IS_APPLICATION_ROLE)
            item.setData(
                action_item.force_not_open_workfile,
                FORCE_NOT_OPEN_WORKFILE_ROLE)
            items_by_id[action_item.identifier] = item
            action_items_by_id[action_item.identifier] = action_item

        if new_items:
            root_item.appendRows(new_items)

        to_remove = set(self._items_by_id.keys()) - set(items_by_id.keys())
        for identifier in to_remove:
            item = self._items_by_id.pop(identifier)
            self._action_items_by_id.pop(identifier)
            root_item.removeRow(item.row())

        self._groups_by_id = groups_by_id
        self._items_by_id = items_by_id
        self._action_items_by_id = action_items_by_id
        self.refreshed.emit()

    def _on_selection_project_changed(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_id = None
        self._selected_task_id = None
        self.refresh()

    def _on_selection_folder_changed(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_id = event["folder_id"]
        self._selected_task_id = None
        self.refresh()

    def _on_selection_task_changed(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_id = event["folder_id"]
        self._selected_task_id = event["task_id"]
        self.refresh()


class ActionDelegate(QtWidgets.QStyledItemDelegate):
    _cached_extender = {}

    def __init__(self, *args, **kwargs):
        super(ActionDelegate, self).__init__(*args, **kwargs)
        self._anim_start_color = QtGui.QColor(178, 255, 246)
        self._anim_end_color = QtGui.QColor(5, 44, 50)

    def _draw_animation(self, painter, option, index):
        grid_size = option.widget.gridSize()
        x_offset = int(
            (grid_size.width() / 2)
            - (option.rect.width() / 2)
        )
        item_x = option.rect.x() - x_offset
        rect_offset = grid_size.width() / 20
        size = grid_size.width() - (rect_offset * 2)
        anim_rect = QtCore.QRect(
            item_x + rect_offset,
            option.rect.y() + rect_offset,
            size,
            size
        )

        painter.save()

        painter.setBrush(QtCore.Qt.transparent)

        gradient = QtGui.QConicalGradient()
        gradient.setCenter(QtCore.QPointF(anim_rect.center()))
        gradient.setColorAt(0, self._anim_start_color)
        gradient.setColorAt(1, self._anim_end_color)

        time_diff = time.time() - index.data(ANIMATION_START_ROLE)

        # Repeat 4 times
        part_anim = 2.5
        part_time = time_diff % part_anim
        offset = (part_time / part_anim) * 360
        angle = (offset + 90) % 360

        gradient.setAngle(-angle)

        pen = QtGui.QPen(QtGui.QBrush(gradient), rect_offset)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            anim_rect,
            -16 * (angle + 10),
            -16 * offset
        )

        painter.restore()

    @classmethod
    def _get_extender_pixmap(cls, size):
        pix = cls._cached_extender.get(size)
        if pix is not None:
            return pix
        pix = QtGui.QPixmap(get_options_image_path()).scaled(
            size, size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        cls._cached_extender[size] = pix
        return pix

    def paint(self, painter, option, index):
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )

        if index.data(ANIMATION_STATE_ROLE):
            self._draw_animation(painter, option, index)

        super(ActionDelegate, self).paint(painter, option, index)

        if index.data(FORCE_NOT_OPEN_WORKFILE_ROLE):
            rect = QtCore.QRectF(
                option.rect.x(), option.rect.height(), 5, 5)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(200, 0, 0))
            painter.drawEllipse(rect)

        if not index.data(ACTION_IS_GROUP_ROLE):
            return

        grid_size = option.widget.gridSize()
        x_offset = int(
            (grid_size.width() / 2)
            - (option.rect.width() / 2)
        )
        item_x = option.rect.x() - x_offset

        tenth_size = int(grid_size.width() / 10)
        extender_size = int(tenth_size * 2.4)

        extender_x = item_x + tenth_size
        extender_y = option.rect.y() + tenth_size

        pix = self._get_extender_pixmap(extender_size)
        painter.drawPixmap(extender_x, extender_y, pix)


class ActionsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(ActionsWidget, self).__init__(parent)

        self._controller = controller

        view = QtWidgets.QListView(self)
        view.setProperty("mode", "icon")
        view.setObjectName("IconView")
        view.setViewMode(QtWidgets.QListView.IconMode)
        view.setResizeMode(QtWidgets.QListView.Adjust)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        view.setWrapping(True)
        view.setGridSize(QtCore.QSize(70, 75))
        view.setIconSize(QtCore.QSize(30, 30))
        view.setSpacing(0)
        view.setWordWrap(True)

        # Make view flickable
        flick = FlickCharm(parent=view)
        flick.activateOn(view)

        model = ActionsQtModel(controller)

        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setSortRole(ACTION_SORT_ROLE)

        proxy_model.setSourceModel(model)
        view.setModel(proxy_model)

        delegate = ActionDelegate(self)
        view.setItemDelegate(delegate)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)

        animation_timer = QtCore.QTimer()
        animation_timer.setInterval(40)
        animation_timer.timeout.connect(self._on_animation)

        view.clicked.connect(self._on_clicked)
        view.customContextMenuRequested.connect(self._on_context_menu)
        model.refreshed.connect(self._on_model_refresh)

        self._animated_items = set()
        self._animation_timer = animation_timer

        self._context_menu = None

        self._flick = flick
        self._view = view
        self._model = model
        self._proxy_model = proxy_model

        self._set_row_height(1)

    def refresh(self):
        self._model.refresh()

    def _set_row_height(self, rows):
        self.setMinimumHeight(rows * 75)

    def _on_model_refresh(self):
        self._proxy_model.sort(0)

    def _on_animation(self):
        time_now = time.time()
        for action_id in tuple(self._animated_items):
            item = self._model.get_item_by_id(action_id)
            if item is None:
                self._animated_items.discard(action_id)
                continue

            start_time = item.data(ANIMATION_START_ROLE)
            if start_time is None or (time_now - start_time) > ANIMATION_LEN:
                item.setData(0, ANIMATION_STATE_ROLE)
                self._animated_items.discard(action_id)

        if not self._animated_items:
            self._animation_timer.stop()

        self.update()

    def _start_animation(self, index):
        # Offset refresh timout
        model_index = self._proxy_model.mapToSource(index)
        if not model_index.isValid():
            return
        action_id = model_index.data(ACTION_ID_ROLE)
        self._model.setData(model_index, time.time(), ANIMATION_START_ROLE)
        self._model.setData(model_index, 1, ANIMATION_STATE_ROLE)
        self._animated_items.add(action_id)
        self._animation_timer.start()

    def _on_context_menu(self, point):
        """Creates menu to force skip opening last workfile."""
        index = self._view.indexAt(point)
        if not index.isValid():
            return

        if not index.data(ACTION_IS_APPLICATION_ROLE):
            return

        menu = QtWidgets.QMenu(self._view)
        checkbox = QtWidgets.QCheckBox(
            "Skip opening last workfile.", menu)
        if index.data(FORCE_NOT_OPEN_WORKFILE_ROLE):
            checkbox.setChecked(True)

        action_id = index.data(ACTION_ID_ROLE)
        is_group = index.data(ACTION_IS_GROUP_ROLE)
        if is_group:
            action_items = self._model.get_group_items(action_id)
        else:
            action_items = [self._model.get_action_item_by_id(action_id)]
        action_ids = {action_item.identifier for action_item in action_items}
        checkbox.stateChanged.connect(
            lambda: self._on_checkbox_changed(
                action_ids, checkbox.isChecked()
            )
        )
        action = QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(checkbox)

        menu.addAction(action)

        self._context_menu = menu
        global_point = self.mapToGlobal(point)
        menu.exec_(global_point)
        self._context_menu = None

    def _on_checkbox_changed(self, action_ids, is_checked):
        if self._context_menu is not None:
            self._context_menu.close()

        project_name = self._model.get_selected_project_name()
        folder_id = self._model.get_selected_folder_id()
        task_id = self._model.get_selected_task_id()
        self._controller.set_application_force_not_open_workfile(
            project_name, folder_id, task_id, action_ids, is_checked)
        self._model.refresh()

    def _on_clicked(self, index):
        if not index or not index.isValid():
            return

        is_group = index.data(ACTION_IS_GROUP_ROLE)
        action_id = index.data(ACTION_ID_ROLE)

        project_name = self._model.get_selected_project_name()
        folder_id = self._model.get_selected_folder_id()
        task_id = self._model.get_selected_task_id()

        if not is_group:
            self._controller.trigger_action(
                project_name, folder_id, task_id, action_id
            )
            self._start_animation(index)
            return

        action_items = self._model.get_group_items(action_id)

        menu = QtWidgets.QMenu(self)
        actions_mapping = {}

        for action_item in action_items:
            menu_action = QtWidgets.QAction(action_item.full_label)
            menu.addAction(menu_action)
            actions_mapping[menu_action] = action_item

        result = menu.exec_(QtGui.QCursor.pos())
        if not result:
            return

        action_item = actions_mapping[result]

        self._controller.trigger_action(
            project_name, folder_id, task_id, action_item.identifier
        )
        self._start_animation(index)
