import os
import time
import collections

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.flickcharm import FlickCharm
from openpype.tools.utils.lib import get_qta_icon_by_name_and_color

ANIMATION_LEN = 7

ACTION_ID_ROLE = QtCore.Qt.UserRole + 1
ACTION_IS_APPLICATION_ROLE = QtCore.Qt.UserRole + 2
ACTION_IS_GROUP_ROLE = QtCore.Qt.UserRole + 3
ANIMATION_START_ROLE = QtCore.Qt.UserRole + 4
ANIMATION_STATE_ROLE = QtCore.Qt.UserRole + 5
FORCE_NOT_OPEN_WORKFILE_ROLE = QtCore.Qt.UserRole + 6


class _IconsCache:
    """Cache for icons."""

    _cache = {}
    _default = None

    @classmethod
    def _get_cache_key(cls, icon_def):
        parts = []
        icon_type = icon_def["type"]
        if icon_type == "path":
            parts = [icon_type, icon_def["path"]]

        elif icon_type == "awesome":
            parts = [icon_type, icon_def["name"], icon_def["color"]]
        return "|".join(parts)

    @classmethod
    def get_icon(cls, icon_def):
        icon_type = icon_def["type"]
        cache_key = cls._get_cache_key(icon_def)
        cache = cls._cache.get(cache_key)
        if cache is not None:
            return cache

        icon = None
        if icon_type == "path":
            path = icon_def["path"]
            if os.path.exists(path):
                icon = QtGui.QPixmap(path)
        elif icon_type == "awesome":
            icon = get_qta_icon_by_name_and_color(
                icon_def["name"], icon_def["color"])
        if icon is None:
            icon = cls.get_default()
        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def get_default(cls):
        return QtGui.QPixmap()


class ActionsQtModel(QtGui.QStandardItemModel):
    """Qt model for actions.

    Args:
        controller (AbstractLauncherFrontEnd): Controller instance.
    """

    def __init__(self, controller):
        super(ActionsQtModel, self).__init__()


        controller.register_event_callback(
            "controller.refresh.finished",
            self._on_controller_refresh_finished,
        )
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
        self._groups_by_id = {}

        self._selected_project_name = None
        self._selected_folder_id = None
        self._seleted_task_id = None

    def _clear_items(self):
        self._items_by_id = {}
        self._groups_by_id = {}
        root = self.invisibleRootItem()
        root.removeRows(0, root.rowCount())

    def refresh(self):
        items = self._controller.get_action_items(
            self._selected_project_name,
            self._selected_folder_id,
            self._seleted_task_id,
        )
        self._clear_items()
        if not items:
            return

        root_item = self.invisibleRootItem()

        single_variant_items = []
        items_by_label = collections.defaultdict(list)
        for item in items:
            if not item.variant_label:
                single_variant_items.append(item)
            else:
                items_by_label[item.label].append(item)

        new_items = []
        groups_by_id = {}
        items_by_id = {}
        for label, action_items in items_by_label.items():
            first_item = next(iter(action_items))
            if len(action_items) == 1:
                single_variant_items.append(first_item)
                continue
            icon = _IconsCache.get_icon(first_item.icon)
            item = QtGui.QStandardItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setData(first_item.label, QtCore.Qt.DisplayRole)
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setData(True, ACTION_IS_GROUP_ROLE)
            item.setData(first_item.identifier, ACTION_ID_ROLE)
            groups_by_id[first_item.identifier] = item
            new_items.append(item)

        for action_item in single_variant_items:
            icon = _IconsCache.get_icon(action_item.icon)

            item = QtGui.QStandardItem()
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setData(action_item.full_label, QtCore.Qt.DisplayRole)
            item.setData(icon, QtCore.Qt.DecorationRole)
            item.setData(False, ACTION_IS_GROUP_ROLE)
            item.setData(action_item.identifier, ACTION_ID_ROLE)
            items_by_id[action_item.identifier] = item
            new_items.append(item)

        if new_items:
            root_item.appendRows(new_items)

        self._groups_by_id = groups_by_id
        self._items_by_id = items_by_id

    def _on_controller_refresh_finished(self):
        self._selected_project_name = None
        self._selected_folder_id = None
        self._seleted_task_id = None
        self.refresh()

    def _on_selection_project_changed(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_id = None
        self._seleted_task_id = None
        self.refresh()

    def _on_selection_folder_changed(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_id = event["folder_id"]
        self._seleted_task_id = None
        self.refresh()

    def _on_selection_task_changed(self, event):
        self._selected_project_name = event["project_name"]
        self._selected_folder_id = event["folder_id"]
        self._seleted_task_id = event["task_id"]
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

        model = ActionsQtModel(controller)
        view.setModel(model)

        delegate = ActionDelegate(self)
        view.setItemDelegate(delegate)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)

        self._animated_items = set()

        animation_timer = QtCore.QTimer()
        animation_timer.setInterval(50)
        animation_timer.timeout.connect(self._on_animation)
        self._animation_timer = animation_timer

        # Make view flickable
        flick = FlickCharm(parent=view)
        flick.activateOn(view)

        self.set_row_height(1)

        view.clicked.connect(self._on_clicked)
        view.customContextMenuRequested.connect(self._on_context_menu)

        self._context_menu = None
        self._discover_on_menu = False
        self._flick = flick
        self._view = view
        self._model = model

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
            item = self._model.items_by_id.get(action_id)
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
        action_id = index.data(ACTION_ID_ROLE)
        item = self.model.items_by_id.get(action_id)
        if item:
            item.setData(time.time(), ANIMATION_START_ROLE)
            item.setData(1, ANIMATION_STATE_ROLE)
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
        self._model.update_force_not_open_workfile_settings(
            is_checked, action_id)
        self._view.update()
        if self._context_menu is not None:
            self._context_menu.close()

    def _on_clicked(self, index):
        if not index or not index.isValid():
            return

        is_group = index.data(ACTION_IS_GROUP_ROLE)
        if not is_group:
            action_id = index.data(ACTION_ID_ROLE)
            self._controller.trigger_action(
                project_name, folder_id, task_name, action_id)
            self._start_animation(index)
            return

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
                    menu_action = QtWidgets.QAction(action.full_label)
                    menu.addAction(menu_action)
                    actions_mapping[menu_action] = action
                    continue

                sub_menu = QtWidgets.QMenu(label, menu)
                for action in actions:
                    menu_action = QtWidgets.QAction(action.full_label)
                    sub_menu.addAction(menu_action)
                    actions_mapping[menu_action] = action

                menu.addMenu(sub_menu)

        result = menu.exec_(QtGui.QCursor.pos())
        if not result:
            return

        action = actions_mapping[result]

        self._start_animation(index)
        self.action_clicked.emit(action)
