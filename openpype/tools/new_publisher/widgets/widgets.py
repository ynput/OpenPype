import re
import copy
import collections
from Qt import QtWidgets, QtCore, QtGui

from openpype.widgets.attribute_defs import create_widget_for_attr_def
from openpype.tools.flickcharm import FlickCharm

from .icons import (
    get_pixmap,
    get_icon_path
)

from ..constants import (
    SUBSET_NAME_ALLOWED_SYMBOLS,
    VARIANT_TOOLTIP
)


class IconBtn(QtWidgets.QPushButton):
    """PushButton with icon and size of font.

    Using font metrics height as icon size reference.
    """
    def sizeHint(self):
        result = super().sizeHint()
        if not self.text():
            new_height = (
                result.height()
                - self.iconSize().height()
                + self.fontMetrics().height()
            )
            result.setHeight(new_height)
        return result


class PublishIconBtn(IconBtn):
    def __init__(self, pixmap_path, *args, **kwargs):
        super(PublishIconBtn, self).__init__(*args, **kwargs)

        loaded_image = QtGui.QImage(pixmap_path)

        pixmap = self.paint_image_with_color(loaded_image, QtCore.Qt.white)

        self._base_image = loaded_image
        self._enabled_icon = QtGui.QIcon(pixmap)
        self._disabled_icon = None

        self.setIcon(self._enabled_icon)

    def get_enabled_icon(self):
        return self._enabled_icon

    def get_disabled_icon(self):
        if self._disabled_icon is None:
            pixmap = self.paint_image_with_color(
                self._base_image, QtCore.Qt.gray
            )
            self._disabled_icon = QtGui.QIcon(pixmap)
        return self._disabled_icon

    @staticmethod
    def paint_image_with_color(image, color):
        width = image.width()
        height = image.height()
        partition = 8
        part_w = int(width / partition)
        part_h = int(height / partition)
        part_w -= part_w % 2
        part_h -= part_h % 2
        scaled_image = image.scaled(
            width - (2 * part_w),
            height - (2 * part_h)
        )
        alpha_mask = scaled_image.createAlphaMask()
        alpha_region = QtGui.QRegion(QtGui.QBitmap(alpha_mask))
        alpha_region.translate(part_w, part_h)

        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setClipRegion(alpha_region)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(color)
        painter.drawRect(QtCore.QRect(0, 0, width, height))
        painter.end()

        return pixmap

    def setEnabled(self, enabled):
        super(PublishIconBtn, self).setEnabled(enabled)
        if self.isEnabled():
            self.setIcon(self.get_enabled_icon())
        else:
            self.setIcon(self.get_disabled_icon())


class ResetBtn(PublishIconBtn):
    def __init__(self, parent=None):
        icon_path = get_icon_path("refresh")
        super(ResetBtn, self).__init__(icon_path, parent)
        self.setToolTip("Refresh publishing")


class StopBtn(PublishIconBtn):
    def __init__(self, parent):
        icon_path = get_icon_path("stop")
        super(StopBtn, self).__init__(icon_path, parent)
        self.setToolTip("Stop/Pause publishing")


class ValidateBtn(PublishIconBtn):
    def __init__(self, parent=None):
        icon_path = get_icon_path("validate")
        super(ValidateBtn, self).__init__(icon_path, parent)
        self.setToolTip("Validate")


class PublishBtn(PublishIconBtn):
    def __init__(self, parent=None):
        icon_path = get_icon_path("play")
        super(PublishBtn, self).__init__(icon_path, "Publish", parent)
        self.setToolTip("Publish")


class AssetsHierarchyModel(QtGui.QStandardItemModel):
    def __init__(self, controller):
        super(AssetsHierarchyModel, self).__init__()
        self._controller = controller

        self._items_by_name = {}

    def reset(self):
        self.clear()

        self._items_by_name = {}
        assets_by_parent_id = self._controller.get_asset_hierarchy()

        items_by_name = {}
        _queue = collections.deque()
        _queue.append((self.invisibleRootItem(), None))
        while _queue:
            parent_item, parent_id = _queue.popleft()
            children = assets_by_parent_id.get(parent_id)
            if not children:
                continue

            children_by_name = {
                child["name"]: child
                for child in children
            }
            items = []
            for name in sorted(children_by_name.keys()):
                child = children_by_name[name]
                item = QtGui.QStandardItem(name)
                items_by_name[name] = item
                items.append(item)
                _queue.append((item, child["_id"]))

            parent_item.appendRows(items)

        self._items_by_name = items_by_name

    def name_is_valid(self, item_name):
        return item_name in self._items_by_name

    def get_index_by_name(self, item_name):
        item = self._items_by_name.get(item_name)
        if item:
            return item.index()
        return QtCore.QModelIndex()


class TasksModel(QtGui.QStandardItemModel):
    def __init__(self, controller):
        super(TasksModel, self).__init__()
        self._controller = controller
        self._items_by_name = {}
        self._asset_names = []
        self._task_names_by_asset_name = {}

    def set_asset_names(self, asset_names):
        self._asset_names = asset_names
        self.reset()

    @staticmethod
    def get_intersection_of_tasks(task_names_by_asset_name):
        tasks = None
        for task_names in task_names_by_asset_name.values():
            if tasks is None:
                tasks = set(task_names)
            else:
                tasks &= set(task_names)

            if not tasks:
                break
        return tasks or set()

    def is_task_name_valid(self, asset_name, task_name):
        task_names = self._task_names_by_asset_name.get(asset_name)
        if task_names and task_name in task_names:
            return True
        return False

    def reset(self):
        if not self._asset_names:
            self._items_by_name = {}
            self._task_names_by_asset_name = {}
            self.clear()
            return

        task_names_by_asset_name = (
            self._controller.get_task_names_by_asset_names(self._asset_names)
        )
        self._task_names_by_asset_name = task_names_by_asset_name

        new_task_names = self.get_intersection_of_tasks(
            task_names_by_asset_name
        )
        old_task_names = set(self._items_by_name.keys())
        if new_task_names == old_task_names:
            return

        root_item = self.invisibleRootItem()
        for task_name in old_task_names:
            if task_name not in new_task_names:
                item = self._items_by_name.pop(task_name)
                root_item.removeRow(item.row())

        new_items = []
        for task_name in new_task_names:
            if task_name in self._items_by_name:
                continue

            item = QtGui.QStandardItem(task_name)
            self._items_by_name[task_name] = item
            new_items.append(item)
        root_item.appendRows(new_items)


class TreeComboBoxView(QtWidgets.QTreeView):
    visible_rows = 12

    def __init__(self, parent):
        super(TreeComboBoxView, self).__init__(parent)

        self.setHeaderHidden(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QTreeView.SelectRows)
        self.setWordWrap(True)
        self.setAllColumnsShowFocus(True)

    def showEvent(self, event):
        super(TreeComboBoxView, self).showEvent(event)

        row_sh = self.sizeHintForRow(0)
        current_height = self.height()
        height = (self.visible_rows * row_sh) + (current_height % row_sh)
        self.setMinimumHeight(height)


class TreeComboBox(QtWidgets.QComboBox):
    def __init__(self, model, parent):
        super(TreeComboBox, self).__init__(parent)

        tree_view = TreeComboBoxView(self)
        self.setView(tree_view)

        tree_view.viewport().installEventFilter(self)

        self._tree_view = tree_view
        self._model = None
        self._skip_next_hide = False

        if model:
            self.setModel(model)

        # Create `lineEdit` to be able set asset names that are not available
        #   or for multiselection.
        self.setEditable(True)
        # Set `lineEdit` to read only
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setAttribute(
            QtCore.Qt.WA_TransparentForMouseEvents, True
        )

    def setModel(self, model):
        self._model = model
        super(TreeComboBox, self).setModel(model)

    def showPopup(self):
        super(TreeComboBox, self).showPopup()

    def hidePopup(self):
        if self._skip_next_hide:
            self._skip_next_hide = False
        else:
            super(TreeComboBox, self).hidePopup()

    def select_index(self, index):
        parent_indexes = []
        parent_index = index.parent()
        while parent_index.isValid():
            parent_indexes.append(parent_index)
            parent_index = parent_index.parent()

        for parent_index in parent_indexes:
            self._tree_view.expand(parent_index)
        selection_model = self._tree_view.selectionModel()
        selection_model.setCurrentIndex(
            index, selection_model.ClearAndSelect
        )
        self.lineEdit().setText(index.data(QtCore.Qt.DisplayRole) or "")

    def eventFilter(self, obj, event):
        if (
            event.type() == QtCore.QEvent.MouseButtonPress
            and obj is self._tree_view.viewport()
        ):
            index = self._tree_view.indexAt(event.pos())
            self._skip_next_hide = not (
                self._tree_view.visualRect(index).contains(event.pos())
            )
        return False

    def set_selected_item(self, item_name):
        index = self._model.get_index_by_name(item_name)
        if index.isValid():
            self._tree_view.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.SelectCurrent
            )
            self.select_index(index)

        else:
            self.lineEdit().setText(item_name)


class AssetsTreeComboBox(TreeComboBox):
    value_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        model = AssetsHierarchyModel(controller)

        super(AssetsTreeComboBox, self).__init__(model, parent)
        self.setObjectName("AssetsTreeComboBox")

        self.currentIndexChanged.connect(self._on_index_change)

        self._ignore_index_change = False
        self._selected_items = []
        self._origin_value = []
        self._has_value_changed = False
        self._model = model
        self._is_valid = True

        self._multiselection_text = None

        model.reset()

    def set_multiselection_text(self, text):
        self._multiselection_text = text

    def _on_index_change(self):
        if self._ignore_index_change:
            return

        self._set_is_valid(True)
        self._selected_items = [self.currentText()]
        self._has_value_changed = (
            self._origin_value != self._selected_items
        )
        self.value_changed.emit()

    def _set_is_valid(self, valid):
        if valid == self._is_valid:
            return
        self._is_valid = valid
        state = ""
        if not valid:
            state = "invalid"
        self._set_state_property(state)

    def _set_state_property(self, state):
        current_value = self.property("state")
        if current_value != state:
            self.setProperty("state", state)
            self.style().polish(self)

    def is_valid(self):
        return self._is_valid

    def has_value_changed(self):
        return self._has_value_changed

    def get_selected_items(self):
        return list(self._selected_items)

    def set_selected_items(self, asset_names=None):
        if asset_names is None:
            asset_names = []

        self._ignore_index_change = True

        self._has_value_changed = False
        self._origin_value = list(asset_names)
        self._selected_items = list(asset_names)
        is_valid = True
        if not asset_names:
            self.set_selected_item("")

        elif len(asset_names) == 1:
            asset_name = tuple(asset_names)[0]
            is_valid = self._model.name_is_valid(asset_name)
            self.set_selected_item(asset_name)
        else:
            for asset_name in asset_names:
                is_valid = self._model.name_is_valid(asset_name)
                if not is_valid:
                    break

            multiselection_text = self._multiselection_text
            if multiselection_text is None:
                multiselection_text = "|".join(asset_names)
            self.set_selected_item(multiselection_text)

        self._set_is_valid(is_valid)

        self._ignore_index_change = False

    def reset_to_origin(self):
        self.set_selected_items(self._origin_value)


class TasksCombobox(QtWidgets.QComboBox):
    value_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(TasksCombobox, self).__init__(parent)
        self.setObjectName("TasksCombobox")

        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        delegate = QtWidgets.QStyledItemDelegate()
        self.setItemDelegate(delegate)

        model = TasksModel(controller)
        self.setModel(model)

        self.currentIndexChanged.connect(self._on_index_change)

        self._delegate = delegate
        self._model = model
        self._origin_value = []
        self._origin_selection = []
        self._selected_items = []
        self._has_value_changed = False
        self._ignore_index_change = False
        self._multiselection_text = None
        self._is_valid = True

    def set_multiselection_text(self, text):
        self._multiselection_text = text

    def _on_index_change(self):
        if self._ignore_index_change:
            return

        text = self.currentText()
        idx = self.findText(text)
        if idx < 0:
            return

        self._set_is_valid(True)
        self._selected_items = [text]
        self._has_value_changed = (
            self._origin_selection != self._selected_items
        )

        self.value_changed.emit()

    def is_valid(self):
        return self._is_valid

    def has_value_changed(self):
        return self._has_value_changed

    def _set_is_valid(self, valid):
        if valid == self._is_valid:
            return
        self._is_valid = valid
        state = ""
        if not valid:
            state = "invalid"
        self._set_state_property(state)

    def _set_state_property(self, state):
        current_value = self.property("state")
        if current_value != state:
            self.setProperty("state", state)
            self.style().polish(self)

    def get_selected_items(self):
        return list(self._selected_items)

    def set_asset_names(self, asset_names):
        self._ignore_index_change = True

        self._model.set_asset_names(asset_names)

        self._ignore_index_change = False

        # It is a bug if not exactly one asset got here
        if len(asset_names) != 1:
            self.set_selected_item("")
            self._set_is_valid(False)
            return

        asset_name = tuple(asset_names)[0]

        is_valid = False
        if self._selected_items:
            is_valid = True

        for task_name in self._selected_items:
            is_valid = self._model.is_task_name_valid(asset_name, task_name)
            if not is_valid:
                break

        if len(self._selected_items) == 0:
            self.set_selected_item("")

        elif len(self._selected_items) == 1:
            self.set_selected_item(self._selected_items[0])

        else:
            multiselection_text = self._multiselection_text
            if multiselection_text is None:
                multiselection_text = "|".join(self._selected_items)
            self.set_selected_item(multiselection_text)
        self._set_is_valid(is_valid)

    def set_selected_items(self, asset_task_combinations=None):
        if asset_task_combinations is None:
            asset_task_combinations = []

        task_names = set()
        task_names_by_asset_name = collections.defaultdict(set)
        for asset_name, task_name in asset_task_combinations:
            task_names.add(task_name)
            task_names_by_asset_name[asset_name].add(task_name)
        asset_names = set(task_names_by_asset_name.keys())

        self._ignore_index_change = True

        self._model.set_asset_names(asset_names)

        self._has_value_changed = False

        self._origin_value = copy.deepcopy(asset_task_combinations)

        self._origin_selection = list(task_names)
        self._selected_items = list(task_names)
        # Reset current index
        self.setCurrentIndex(-1)
        is_valid = True
        if not task_names:
            self.set_selected_item("")

        elif len(task_names) == 1:
            task_name = tuple(task_names)[0]
            idx = self.findText(task_name)
            is_valid = not idx < 0
            if not is_valid and len(asset_names) > 1:
                is_valid = self._validate_task_names_by_asset_names(
                    task_names_by_asset_name
                )
            self.set_selected_item(task_name)

        else:
            for task_name in task_names:
                idx = self.findText(task_name)
                is_valid = not idx < 0
                if not is_valid:
                    break

            if not is_valid and len(asset_names) > 1:
                is_valid = self._validate_task_names_by_asset_names(
                    task_names_by_asset_name
                )
            multiselection_text = self._multiselection_text
            if multiselection_text is None:
                multiselection_text = "|".join(task_names)
            self.set_selected_item(multiselection_text)

        self._set_is_valid(is_valid)

        self._ignore_index_change = False

        self.value_changed.emit()

    def _validate_task_names_by_asset_names(self, task_names_by_asset_name):
        for asset_name, task_names in task_names_by_asset_name.items():
            for task_name in task_names:
                if not self._model.is_task_name_valid(asset_name, task_name):
                    return False
        return True

    def set_selected_item(self, item_name):
        idx = self.findText(item_name)
        # Set current index (must be set to -1 if is invalid)
        self.setCurrentIndex(idx)
        if idx < 0:
            self.lineEdit().setText(item_name)

    def reset_to_origin(self):
        self.set_selected_items(self._origin_value)


class VariantInputWidget(QtWidgets.QLineEdit):
    value_changed = QtCore.Signal()

    def __init__(self, parent):
        super(VariantInputWidget, self).__init__(parent)

        self.setObjectName("VariantInput")
        self.setToolTip(VARIANT_TOOLTIP)

        name_pattern = "^[{}]*$".format(SUBSET_NAME_ALLOWED_SYMBOLS)
        self._name_pattern = name_pattern
        self._compiled_name_pattern = re.compile(name_pattern)

        self._origin_value = []
        self._current_value = []

        self._ignore_value_change = False
        self._has_value_changed = False
        self._multiselection_text = None

        self._is_valid = True

        self.textChanged.connect(self._on_text_change)

    def is_valid(self):
        return self._is_valid

    def has_value_changed(self):
        return self._has_value_changed

    def _set_state_property(self, state):
        current_value = self.property("state")
        if current_value != state:
            self.setProperty("state", state)
            self.style().polish(self)

    def set_multiselection_text(self, text):
        self._multiselection_text = text

    def _set_is_valid(self, valid):
        if valid == self._is_valid:
            return
        self._is_valid = valid
        state = ""
        if not valid:
            state = "invalid"
        self._set_state_property(state)

    def _on_text_change(self):
        if self._ignore_value_change:
            return

        is_valid = bool(self._compiled_name_pattern.match(self.text()))
        self._set_is_valid(is_valid)

        self._current_value = [self.text()]
        self._has_value_changed = self._current_value != self._origin_value

        self.value_changed.emit()

    def reset_to_origin(self):
        self.set_value(self._origin_value)

    def get_value(self):
        return copy.deepcopy(self._current_value)

    def set_value(self, variants=None):
        if variants is None:
            variants = []

        self._ignore_value_change = True

        self._origin_value = list(variants)
        self._current_value = list(variants)

        self.setPlaceholderText("")
        if not variants:
            self.setText("")

        elif len(variants) == 1:
            self.setText(self._current_value[0])

        else:
            multiselection_text = self._multiselection_text
            if multiselection_text is None:
                multiselection_text = "|".join(variants)
            self.setText("")
            self.setPlaceholderText(multiselection_text)

        self._ignore_value_change = False


class MultipleItemWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(MultipleItemWidget, self).__init__(parent)

        model = QtGui.QStandardItemModel()

        view = QtWidgets.QListView(self)
        view.setObjectName("MultipleItemView")
        view.setLayoutMode(QtWidgets.QListView.Batched)
        view.setViewMode(QtWidgets.QListView.IconMode)
        view.setResizeMode(QtWidgets.QListView.Adjust)
        view.setWrapping(False)
        view.setSpacing(2)
        view.setModel(model)
        view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        flick = FlickCharm(parent=view)
        flick.activateOn(view)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(view)

        self._view = view
        self._model = model

        self._value = []

    def showEvent(self, event):
        super(MultipleItemWidget, self).showEvent(event)
        tmp_item = None
        if not self._value:
            tmp_item = QtGui.QStandardItem("tmp")
            self._model.appendRow(tmp_item)

        height = self._view.sizeHintForRow(0)
        self.setMaximumHeight(height + (2 * self._view.spacing()))

        if tmp_item is not None:
            self._model.clear()

    def set_value(self, value=None):
        if value is None:
            value = []
        self._value = value

        self._model.clear()
        for item_text in value:
            item = QtGui.QStandardItem(item_text)
            item.setEditable(False)
            item.setSelectable(False)
            self._model.appendRow(item)


class GlobalAttrsWidget(QtWidgets.QWidget):
    instance_context_changed = QtCore.Signal()

    multiselection_text = "< Multiselection >"
    unknown_value = "N/A"

    def __init__(self, controller, parent):
        super(GlobalAttrsWidget, self).__init__(parent)

        self.controller = controller
        self._current_instances = []

        variant_input = VariantInputWidget(self)
        asset_value_widget = AssetsTreeComboBox(controller, self)
        task_value_widget = TasksCombobox(controller, self)
        family_value_widget = MultipleItemWidget(self)
        subset_value_widget = MultipleItemWidget(self)

        variant_input.set_multiselection_text(self.multiselection_text)
        asset_value_widget.set_multiselection_text(self.multiselection_text)
        task_value_widget.set_multiselection_text(self.multiselection_text)

        variant_input.set_value()
        asset_value_widget.set_selected_items()
        task_value_widget.set_selected_items()
        family_value_widget.set_value()
        subset_value_widget.set_value()

        submit_btn = QtWidgets.QPushButton("Submit", self)
        cancel_btn = QtWidgets.QPushButton("Cancel", self)
        submit_btn.setEnabled(False)
        cancel_btn.setEnabled(False)

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(submit_btn)
        btns_layout.addWidget(cancel_btn)

        main_layout = QtWidgets.QFormLayout(self)
        main_layout.addRow("Name", variant_input)
        main_layout.addRow("Asset", asset_value_widget)
        main_layout.addRow("Task", task_value_widget)
        main_layout.addRow("Family", family_value_widget)
        main_layout.addRow("Subset", subset_value_widget)
        main_layout.addRow(btns_layout)

        variant_input.value_changed.connect(self._on_variant_change)
        asset_value_widget.value_changed.connect(self._on_asset_change)
        task_value_widget.value_changed.connect(self._on_task_change)
        submit_btn.clicked.connect(self._on_submit)
        cancel_btn.clicked.connect(self._on_cancel)

        self.variant_input = variant_input
        self.asset_value_widget = asset_value_widget
        self.task_value_widget = task_value_widget
        self.family_value_widget = family_value_widget
        self.subset_value_widget = subset_value_widget
        self.submit_btn = submit_btn
        self.cancel_btn = cancel_btn

    def _on_submit(self):
        variant_value = None
        asset_name = None
        task_name = None
        if self.variant_input.has_value_changed():
            variant_value = self.variant_input.get_value()[0]

        if self.asset_value_widget.has_value_changed():
            asset_name = self.asset_value_widget.get_selected_items()[0]

        if self.task_value_widget.has_value_changed():
            task_name = self.task_value_widget.get_selected_items()[0]

        asset_docs_by_name = {}
        asset_names = set()
        if asset_name is None:
            for instance in self._current_instances:
                asset_names.add(instance.data.get("asset"))
        else:
            asset_names.add(asset_name)

        for asset_doc in self.controller.get_asset_docs():
            _asset_name = asset_doc["name"]
            if _asset_name in asset_names:
                asset_names.remove(_asset_name)
                asset_docs_by_name[_asset_name] = asset_doc

            if not asset_names:
                break

        project_name = self.controller.project_name
        subset_names = set()
        for instance in self._current_instances:
            if variant_value is not None:
                instance.data["variant"] = variant_value

            if asset_name is not None:
                instance.data["asset"] = asset_name
                instance.set_asset_invalid(False)

            if task_name is not None:
                instance.data["task"] = task_name
                instance.set_task_invalid(False)

            new_variant_value = instance.data.get("variant")
            new_asset_name = instance.data.get("asset")
            new_task_name = instance.data.get("task")

            asset_doc = asset_docs_by_name[new_asset_name]

            new_subset_name = instance.creator.get_subset_name(
                new_variant_value, new_task_name, asset_doc, project_name
            )
            subset_names.add(new_subset_name)
            instance.data["subset"] = new_subset_name

        self.subset_value_widget.set_value(subset_names)

        self._set_btns_enabled(False)
        self._set_btns_visible(False)

        self.instance_context_changed.emit()

    def _on_cancel(self):
        self.variant_input.reset_to_origin()
        self.asset_value_widget.reset_to_origin()
        self.task_value_widget.reset_to_origin()
        self._set_btns_enabled(False)

    def _on_value_change(self):
        any_invalid = (
            not self.variant_input.is_valid()
            or not self.asset_value_widget.is_valid()
            or not self.task_value_widget.is_valid()
        )
        any_changed = (
            self.variant_input.has_value_changed()
            or self.asset_value_widget.has_value_changed()
            or self.task_value_widget.has_value_changed()
        )
        self._set_btns_visible(any_changed or any_invalid)
        self.cancel_btn.setEnabled(any_changed)
        self.submit_btn.setEnabled(not any_invalid)

    def _on_variant_change(self):
        self._on_value_change()

    def _on_asset_change(self):
        asset_names = self.asset_value_widget.get_selected_items()
        self.task_value_widget.set_asset_names(asset_names)
        self._on_value_change()

    def _on_task_change(self):
        self._on_value_change()

    def _set_btns_visible(self, visible):
        self.cancel_btn.setVisible(visible)
        self.submit_btn.setVisible(visible)

    def _set_btns_enabled(self, enabled):
        self.cancel_btn.setEnabled(enabled)
        self.submit_btn.setEnabled(enabled)

    def set_current_instances(self, instances):
        self._set_btns_visible(False)

        self._current_instances = instances

        asset_names = set()
        variants = set()
        families = set()
        subset_names = set()

        editable = True
        if len(instances) == 0:
            editable = False

        asset_task_combinations = []
        for instance in instances:
            if instance.creator is None:
                editable = False

            variants.add(instance.data.get("variant") or self.unknown_value)
            families.add(instance.data.get("family") or self.unknown_value)
            asset_name = instance.data.get("asset") or self.unknown_value
            task_name = instance.data.get("task") or self.unknown_value
            asset_names.add(asset_name)
            asset_task_combinations.append((asset_name, task_name))
            subset_names.add(instance.data.get("subset") or self.unknown_value)

        self.variant_input.set_value(variants)

        # Set context of asset widget
        self.asset_value_widget.set_selected_items(asset_names)
        # Set context of task widget
        self.task_value_widget.set_selected_items(asset_task_combinations)
        self.family_value_widget.set_value(families)
        self.subset_value_widget.set_value(subset_names)

        self.variant_input.setEnabled(editable)
        self.asset_value_widget.setEnabled(editable)
        self.task_value_widget.setEnabled(editable)


class FamilyAttrsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(FamilyAttrsWidget, self).__init__(parent)

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll_area, 1)

        self._main_layout = main_layout

        self.controller = controller
        self._scroll_area = scroll_area

        self._attr_def_id_to_instances = {}
        self._attr_def_id_to_attr_def = {}

        # To store content of scroll area to prevend garbage collection
        self._content_widget = None

    def set_instances_valid(self, valid):
        if (
            self._content_widget is not None
            and self._content_widget.isEnabled() != valid
        ):
            self._content_widget.setEnabled(valid)

    def set_current_instances(self, instances):
        prev_content_widget = self._scroll_area.widget()
        if prev_content_widget:
            self._scroll_area.takeWidget()
            prev_content_widget.hide()
            prev_content_widget.deleteLater()

        self._content_widget = None
        self._attr_def_id_to_instances = {}
        self._attr_def_id_to_attr_def = {}

        result = self.controller.get_family_attribute_definitions(
            instances
        )

        content_widget = QtWidgets.QWidget(self._scroll_area)
        content_layout = QtWidgets.QFormLayout(content_widget)
        for attr_def, attr_instances, values in result:
            widget = create_widget_for_attr_def(attr_def, content_widget)
            if len(values) == 1:
                value = values[0]
                if value is not None:
                    widget.set_value(values[0])
            else:
                widget.set_value(values, True)

            label = attr_def.label or attr_def.key
            content_layout.addRow(label, widget)
            widget.value_changed.connect(self._input_value_changed)

            self._attr_def_id_to_instances[attr_def.id] = attr_instances
            self._attr_def_id_to_attr_def[attr_def.id] = attr_def

        self._scroll_area.setWidget(content_widget)
        self._content_widget = content_widget

    def _input_value_changed(self, value, attr_id):
        instances = self._attr_def_id_to_instances.get(attr_id)
        attr_def = self._attr_def_id_to_attr_def.get(attr_id)
        if not instances or not attr_def:
            return

        for instance in instances:
            family_attributes = instance.data["family_attributes"]
            if attr_def.key in family_attributes:
                family_attributes[attr_def.key] = value


class PublishPluginAttrsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(PublishPluginAttrsWidget, self).__init__(parent)

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll_area, 1)

        self._main_layout = main_layout

        self.controller = controller
        self._scroll_area = scroll_area

        self._attr_def_id_to_instances = {}
        self._attr_def_id_to_attr_def = {}
        self._attr_def_id_to_plugin_name = {}

        # Store content of scroll area to prevend garbage collection
        self._content_widget = None

    def set_instances_valid(self, valid):
        if (
            self._content_widget is not None
            and self._content_widget.isEnabled() != valid
        ):
            self._content_widget.setEnabled(valid)

    def set_current_instances(self, instances, context_selected):
        prev_content_widget = self._scroll_area.widget()
        if prev_content_widget:
            self._scroll_area.takeWidget()
            prev_content_widget.hide()
            prev_content_widget.deleteLater()

        self._content_widget = None

        self._attr_def_id_to_instances = {}
        self._attr_def_id_to_attr_def = {}
        self._attr_def_id_to_plugin_name = {}

        result = self.controller.get_publish_attribute_definitions(
            instances, context_selected
        )

        content_widget = QtWidgets.QWidget(self._scroll_area)
        content_layout = QtWidgets.QFormLayout(content_widget)
        for plugin_name, attr_defs, all_plugin_values in result:
            plugin_values = all_plugin_values[plugin_name]

            for attr_def in attr_defs:
                widget = create_widget_for_attr_def(
                    attr_def, content_widget
                )
                label = attr_def.label or attr_def.key
                content_layout.addRow(label, widget)

                widget.value_changed.connect(self._input_value_changed)

                attr_values = plugin_values[attr_def.key]
                multivalue = len(attr_values) > 1
                values = []
                instances = []
                for instance, value in attr_values:
                    values.append(value)
                    instances.append(instance)

                self._attr_def_id_to_attr_def[attr_def.id] = attr_def
                self._attr_def_id_to_instances[attr_def.id] = instances
                self._attr_def_id_to_plugin_name[attr_def.id] = plugin_name

                if multivalue:
                    widget.set_value(values, multivalue)
                else:
                    widget.set_value(values[0])

        self._scroll_area.setWidget(content_widget)
        self._content_widget = content_widget

    def _input_value_changed(self, value, attr_id):
        instances = self._attr_def_id_to_instances.get(attr_id)
        attr_def = self._attr_def_id_to_attr_def.get(attr_id)
        plugin_name = self._attr_def_id_to_plugin_name.get(attr_id)
        if not instances or not attr_def or not plugin_name:
            return

        for instance in instances:
            plugin_val = instance.publish_attributes[plugin_name]
            plugin_val[attr_def.key] = value


class SubsetAttributesWidget(QtWidgets.QWidget):
    """Widget where attributes of instance/s are modified.
     _____________________________
    |                 |           |
    |     Global      | Thumbnail |
    |     attributes  |           | TOP
    |_________________|___________|
    |              |              |
    |              |  Publish     |
    |  Family      |  plugin      |
    |  attributes  |  attributes  | BOTTOM
    |______________|______________|
    """
    instance_context_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(SubsetAttributesWidget, self).__init__(parent)

        # TOP PART
        top_widget = QtWidgets.QWidget(self)

        # Global attributes
        global_attrs_widget = GlobalAttrsWidget(controller, top_widget)
        thumbnail_widget = ThumbnailWidget(top_widget)
        thumbnail_widget.setVisible(False)

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(global_attrs_widget, 7)
        top_layout.addWidget(thumbnail_widget, 3)

        # BOTTOM PART
        bottom_widget = QtWidgets.QWidget(self)
        family_attrs_widget = FamilyAttrsWidget(
            controller, bottom_widget
        )
        publish_attrs_widget = PublishPluginAttrsWidget(
            controller, bottom_widget
        )

        bottom_separator = QtWidgets.QWidget(bottom_widget)
        bottom_separator.setObjectName("Separator")
        bottom_separator.setMinimumWidth(1)

        bottom_layout = QtWidgets.QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(family_attrs_widget, 1)
        bottom_layout.addWidget(bottom_separator, 0)
        bottom_layout.addWidget(publish_attrs_widget, 1)

        top_bottom = QtWidgets.QWidget(self)
        top_bottom.setObjectName("Separator")
        top_bottom.setMinimumHeight(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(top_widget, 0)
        layout.addWidget(top_bottom, 0)
        layout.addWidget(bottom_widget, 1)

        self._current_instances = None
        self._context_selected = False
        self._all_instances_valid = True

        global_attrs_widget.instance_context_changed.connect(
            self._on_instance_context_changed
        )

        self.controller = controller

        self.global_attrs_widget = global_attrs_widget

        self.family_attrs_widget = family_attrs_widget
        self.publish_attrs_widget = publish_attrs_widget
        self.thumbnail_widget = thumbnail_widget

        self.top_bottom = top_bottom
        self.bottom_separator = bottom_separator

    def _on_instance_context_changed(self):
        all_valid = True
        for instance in self._current_instances:
            if not instance.has_valid_context:
                all_valid = False
                break

        self._all_instances_valid = all_valid
        self.family_attrs_widget.set_instances_valid(all_valid)
        self.publish_attrs_widget.set_instances_valid(all_valid)

        self.instance_context_changed.emit()

    def set_current_instances(self, instances, context_selected):
        all_valid = True
        for instance in instances:
            if not instance.has_valid_context:
                all_valid = False
                break

        self._current_instances = instances
        self._context_selected = context_selected
        self._all_instances_valid = all_valid

        self.global_attrs_widget.set_current_instances(instances)
        self.family_attrs_widget.set_current_instances(instances)
        self.publish_attrs_widget.set_current_instances(
            instances, context_selected
        )
        self.family_attrs_widget.set_instances_valid(all_valid)
        self.publish_attrs_widget.set_instances_valid(all_valid)


class ThumbnailWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ThumbnailWidget, self).__init__(parent)

        default_pix = get_pixmap("thumbnail")

        thumbnail_label = QtWidgets.QLabel(self)
        thumbnail_label.setPixmap(
            default_pix.scaled(
                200, 100,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(thumbnail_label, alignment=QtCore.Qt.AlignCenter)

        self.thumbnail_label = thumbnail_label
        self.default_pix = default_pix
        self.current_pix = None
