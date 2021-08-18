import os
import copy
import collections
from Qt import QtWidgets, QtCore, QtGui

from openpype.widgets.attribute_defs import create_widget_for_attr_def
from constants import (
    INSTANCE_ID_ROLE,
    SORT_VALUE_ROLE
)

from openpype.tools.flickcharm import FlickCharm


def get_default_thumbnail_image_path():
    dirpath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dirpath, "image_file.png")


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

    def set_asset_names(self, asset_names):
        self._asset_names = asset_names
        self.reset()

    def reset(self):
        if not self._asset_names:
            self._items_by_name = {}
            self.clear()
            return

        new_task_names = self._controller.get_task_names_for_asset_names(
            self._asset_names
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

    def setModel(self, model):
        self._model = model
        super(TreeComboBox, self).setModel(model)

    def showPopup(self):
        self.setRootModelIndex(QtCore.QModelIndex())
        super(TreeComboBox, self).showPopup()

    def hidePopup(self):
        # NOTE This would hide everything except parents
        # self.setRootModelIndex(self._tree_view.currentIndex().parent())
        # self.setCurrentIndex(self._tree_view.currentIndex().row())
        if self._skip_next_hide:
            self._skip_next_hide = False
        else:
            super(TreeComboBox, self).hidePopup()

    def selectIndex(self, index):
        self.setRootModelIndex(index.parent())
        self.setCurrentIndex(index.row())

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
            self.selectIndex(index)

        else:
            self.lineEdit().setText(item_name)


class AssetsTreeComboBox(TreeComboBox):
    value_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        model = AssetsHierarchyModel(controller)

        super(AssetsTreeComboBox, self).__init__(model, parent)

        self.currentIndexChanged.connect(self._on_index_change)

        self._ignore_index_change = False
        self._selected_items = []
        self._origin_value = []
        self._has_value_changed = False
        self._model = model

        self._multiselection_text = None

        model.reset()

    def set_multiselection_text(self, text):
        self._multiselection_text = text

    def _on_index_change(self):
        if self._ignore_index_change:
            return

        self._selected_items = [self.currentText()]
        self._has_value_changed = (
            self._origin_value != self._selected_items
        )
        self.value_changed.emit()

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
        if not asset_names:
            self.set_selected_item("")

        elif len(asset_names) == 1:
            self.set_selected_item(tuple(asset_names)[0])
        else:
            multiselection_text = self._multiselection_text
            if multiselection_text is None:
                multiselection_text = "|".join(asset_names)
            self.set_selected_item(multiselection_text)

        self._ignore_index_change = False

    def reset_to_origin(self):
        self.set_selected_items(self._origin_value)


class TasksCombobox(QtWidgets.QComboBox):
    value_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(TasksCombobox, self).__init__(parent)

        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        model = TasksModel(controller)
        self.setModel(model)

        self.currentIndexChanged.connect(self._on_index_change)

        self._model = model
        self._origin_value = []
        self._selected_items = []
        self._has_value_changed = False
        self._ignore_index_change = False
        self._multiselection_text = None

    def set_multiselection_text(self, text):
        self._multiselection_text = text

    def _on_index_change(self):
        if self._ignore_index_change:
            return

        self._selected_items = [self.currentText()]
        self._has_value_changed = (
            self._origin_value != self._selected_items
        )

        self.value_changed.emit()

    def has_value_changed(self):
        return self._has_value_changed

    def get_selected_items(self):
        return list(self._selected_items)

    def set_asset_names(self, asset_names):
        self._model.set_asset_names(asset_names)

    def set_selected_items(self, task_names=None):
        if task_names is None:
            task_names = []

        self._ignore_index_change = True

        self._has_value_changed = False
        self._origin_value = list(task_names)
        self._selected_items = list(task_names)
        # Reset current index
        self.setCurrentIndex(-1)
        if not task_names:
            self.set_selected_item("")

        elif len(task_names) == 1:
            task_name = tuple(task_names)[0]
            idx = self.findText(task_name)
            self.set_selected_item(task_name)

        else:
            valid_value = True
            for task_name in task_names:
                idx = self.findText(task_name)
                valid_value = not idx < 0
                if not valid_value:
                    break

            multiselection_text = self._multiselection_text
            if multiselection_text is None:
                multiselection_text = "|".join(task_names)
            self.set_selected_item(multiselection_text)

        self._ignore_index_change = False

        self.value_changed.emit()

    def set_selected_item(self, item_name):
        idx = self.findText(item_name)
        if idx < 0:
            self.lineEdit().setText(item_name)
        else:
            self.setCurrentIndex(idx)

    def reset_to_origin(self):
        self.set_selected_items(self._origin_value)


class VariantInputWidget(QtWidgets.QLineEdit):
    value_changed = QtCore.Signal()

    def __init__(self, parent):
        super(VariantInputWidget, self).__init__(parent)

        self._origin_value = []
        self._current_value = []

        self._ignore_value_change = False
        self._has_value_changed = False
        self._multiselection_text = None

        self.textChanged.connect(self._on_text_change)

    def set_multiselection_text(self, text):
        self._multiselection_text = text

    def has_value_changed(self):
        return self._has_value_changed

    def _on_text_change(self):
        if self._ignore_value_change:
            return

        self._current_value = [self.text()]
        self._has_value_changed = self._current_value != self._origin_value

    def reset_to_origin(self):
        self.set_value(self._origin_value)

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
    multiselection_text = "< Multiselection >"
    unknown_value = "N/A"

    def __init__(self, controller, parent):
        super(GlobalAttrsWidget, self).__init__(parent)

        self.controller = controller

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
        print("submit")
        self.cancel_btn.setEnabled(False)
        self.submit_btn.setEnabled(False)

    def _on_cancel(self):
        self.variant_input.reset_to_origin()
        self.asset_value_widget.reset_to_origin()
        self.task_value_widget.reset_to_origin()
        self.cancel_btn.setEnabled(False)
        self.submit_btn.setEnabled(False)

    def _on_value_change(self):
        any_changed = (
            self.variant_input.has_value_changed()
            or self.asset_value_widget.has_value_changed()
            or self.task_value_widget.has_value_changed()
        )

        self.cancel_btn.setEnabled(any_changed)
        self.submit_btn.setEnabled(any_changed)

    def _on_variant_change(self):
        self._on_value_change()

    def _on_asset_change(self):
        asset_names = self.asset_value_widget.get_selected_items()
        self.task_value_widget.set_asset_names(asset_names)
        self._on_value_change()

    def _on_task_change(self):
        self._on_value_change()

    def set_current_instances(self, instances):
        self.cancel_btn.setEnabled(False)
        self.submit_btn.setEnabled(False)

        asset_names = set()
        task_names = set()
        variants = set()
        families = set()
        subset_names = set()

        editable = True
        if len(instances) == 0:
            editable = False

        for instance in instances:
            if instance.creator is None:
                editable = False

            variants.add(instance.data.get("variant") or self.unknown_value)
            families.add(instance.data.get("family") or self.unknown_value)
            asset_names.add(instance.data.get("asset") or self.unknown_value)
            task_names.add(instance.data.get("task") or self.unknown_value)
            subset_names.add(instance.data.get("subset") or self.unknown_value)

        self.variant_input.set_value(variants)

        # Set context of asset widget
        self.asset_value_widget.set_selected_items(asset_names)
        # Set context of task widget
        self.task_value_widget.set_asset_names(asset_names)
        self.task_value_widget.set_selected_items(task_names)
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

    def set_current_instances(self, instances):
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
            instances
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

    def __init__(self, controller, parent):
        super(SubsetAttributesWidget, self).__init__(parent)

        # TOP PART
        top_widget = QtWidgets.QWidget(self)

        # Global attributes
        global_attrs_widget = GlobalAttrsWidget(controller, top_widget)
        thumbnail_widget = ThumbnailWidget(top_widget)

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

        self.controller = controller
        self.global_attrs_widget = global_attrs_widget
        self.family_attrs_widget = family_attrs_widget
        self.publish_attrs_widget = publish_attrs_widget
        self.thumbnail_widget = thumbnail_widget

    def set_current_instances(self, instances):
        self.global_attrs_widget.set_current_instances(instances)
        self.family_attrs_widget.set_current_instances(instances)
        self.publish_attrs_widget.set_current_instances(instances)


class ThumbnailWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ThumbnailWidget, self).__init__(parent)

        default_pix = QtGui.QPixmap(get_default_thumbnail_image_path())

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


class InstanceCardWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, item, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self.instance = instance
        self.item = item

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        active_checkbox = QtWidgets.QCheckBox(self)
        active_checkbox.setChecked(instance.data["active"])

        expand_btn = QtWidgets.QToolButton(self)
        expand_btn.setObjectName("ArrowBtn")
        expand_btn.setArrowType(QtCore.Qt.DownArrow)
        expand_btn.setMaximumWidth(14)
        expand_btn.setEnabled(False)

        detail_widget = QtWidgets.QWidget(self)
        detail_widget.setVisible(False)
        self.detail_widget = detail_widget

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(subset_name_label)
        top_layout.addStretch(1)
        top_layout.addWidget(active_checkbox)
        top_layout.addWidget(expand_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addLayout(top_layout)
        layout.addWidget(detail_widget)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        active_checkbox.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        expand_btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        active_checkbox.stateChanged.connect(self._on_active_change)
        expand_btn.clicked.connect(self._on_expend_clicked)

        self.subset_name_label = subset_name_label
        self.active_checkbox = active_checkbox
        self.expand_btn = expand_btn

    def set_active(self, new_value):
        checkbox_value = self.active_checkbox.isChecked()
        instance_value = self.instance.data["active"]

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        if instance_value != new_value:
            self.instance.data["active"] = new_value

        if checkbox_value != new_value:
            self.active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        self.instance = instance
        self.update_instance_values()

    def update_instance_values(self):
        self.set_active(self.instance.data["active"])

    def _set_expanded(self, expanded=None):
        if expanded is None:
            expanded = not self.detail_widget.isVisible()
        self.detail_widget.setVisible(expanded)
        self.item.setSizeHint(self.sizeHint())

    def showEvent(self, event):
        super(InstanceCardWidget, self).showEvent(event)
        self.item.setSizeHint(self.sizeHint())

    def _on_active_change(self):
        new_value = self.active_checkbox.isChecked()
        old_value = self.instance.data["active"]
        if new_value == old_value:
            return

        self.instance.data["active"] = new_value
        self.active_changed.emit(self.instance.data["uuid"], new_value)

    def _on_expend_clicked(self):
        self._set_expanded()


class _AbstractInstanceView(QtWidgets.QWidget):
    selection_changed = QtCore.Signal()

    def refresh(self):
        raise NotImplementedError((
            "{} Method 'refresh' is not implemented."
        ).format(self.__class__.__name__))

    def get_selected_instances(self):
        raise NotImplementedError((
            "{} Method 'get_selected_instances' is not implemented."
        ).format(self.__class__.__name__))

    def set_selected_instances(self, instances):
        raise NotImplementedError((
            "{} Method 'set_selected_instances' is not implemented."
        ).format(self.__class__.__name__))


class InstanceCardView(_AbstractInstanceView):
    def __init__(self, controller, parent):
        super(InstanceCardView, self).__init__(parent)

        self.controller = controller

        list_widget = QtWidgets.QListWidget(self)
        list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        list_widget.setResizeMode(QtWidgets.QListView.Adjust)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(list_widget, 1)

        list_widget.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )

        self._items_by_id = {}
        self._widgets_by_id = {}

        self.list_widget = list_widget

    def refresh(self):
        instances_by_id = {}
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        for instance_id in tuple(self._items_by_id.keys()):
            if instance_id not in instances_by_id:
                item = self._items_by_id.pop(instance_id)
                self.list_widget.removeItemWidget(item)
                widget = self._widgets_by_id.pop(instance_id)
                widget.deleteLater()
                row = self.list_widget.row(item)
                self.list_widget.takeItem(row)

        for instance_id, instance in instances_by_id.items():
            if instance_id in self._items_by_id:
                widget = self._widgets_by_id[instance_id]
                widget.update_instance(instance)

            else:
                item = QtWidgets.QListWidgetItem(self.list_widget)
                widget = InstanceCardWidget(instance, item, self)
                widget.active_changed.connect(self._on_active_changed)
                item.setData(INSTANCE_ID_ROLE, instance_id)
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)
                self._items_by_id[instance_id] = item
                self._widgets_by_id[instance_id] = widget

    def refresh_active_state(self):
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def _on_active_changed(self, changed_instance_id, new_value):
        selected_ids = set()
        found = False
        for item in self.list_widget.selectedItems():
            instance_id = item.data(INSTANCE_ID_ROLE)
            selected_ids.add(instance_id)
            if not found and instance_id == changed_instance_id:
                found = True

        if not found:
            return

        for instance_id in selected_ids:
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                widget.set_active(new_value)

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()

    def get_selected_instances(self):
        instances = []
        for item in self.list_widget.selectedItems():
            instance_id = item.data(INSTANCE_ID_ROLE)
            widget = self._widgets_by_id.get(instance_id)
            if widget:
                instances.append(widget.instance)
        return instances

    def set_selected_instances(self, instances):
        indexes = []
        model = self.list_widget.model()
        for instance in instances:
            instance_id = instance.data["uuid"]
            item = self._items_by_id.get(instance_id)
            if item:
                row = self.list_widget.row(item)
                index = model.index(row, 0)
                indexes.append(index)

        selection_model = self.list_widget.selectionModel()
        first_item = True
        for index in indexes:
            if first_item:
                first_item = False
                select_type = QtCore.QItemSelectionModel.ClearAndSelect
            else:
                select_type = QtCore.QItemSelectionModel.Select
            selection_model.select(index, select_type)


class InstanceListItemWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, parent):
        super(InstanceListItemWidget, self).__init__(parent)

        self.instance = instance

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        active_checkbox = QtWidgets.QCheckBox(self)
        active_checkbox.setChecked(instance.data["active"])

        layout = QtWidgets.QHBoxLayout(self)
        content_margins = layout.contentsMargins()
        layout.setContentsMargins(content_margins.left() + 2, 0, 2, 0)
        layout.addWidget(subset_name_label)
        layout.addStretch(1)
        layout.addWidget(active_checkbox)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        active_checkbox.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        active_checkbox.stateChanged.connect(self._on_active_change)

        self.subset_name_label = subset_name_label
        self.active_checkbox = active_checkbox

    def set_active(self, new_value):
        checkbox_value = self.active_checkbox.isChecked()
        instance_value = self.instance.data["active"]

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        if instance_value != new_value:
            self.instance.data["active"] = new_value

        if checkbox_value != new_value:
            self.active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        self.instance = instance
        self.update_instance_values()

    def update_instance_values(self):
        self.set_active(self.instance.data["active"])

    def _on_active_change(self):
        new_value = self.active_checkbox.isChecked()
        old_value = self.instance.data["active"]
        if new_value == old_value:
            return

        self.instance.data["active"] = new_value
        self.active_changed.emit(self.instance.data["uuid"], new_value)


class InstanceListGroupWidget(QtWidgets.QFrame):
    expand_changed = QtCore.Signal(str, bool)

    def __init__(self, family, parent):
        super(InstanceListGroupWidget, self).__init__(parent)
        self.setObjectName("InstanceListGroupWidget")

        self.family = family
        self._expanded = False

        subset_name_label = QtWidgets.QLabel(family, self)

        expand_btn = QtWidgets.QToolButton(self)
        expand_btn.setObjectName("ArrowBtn")
        expand_btn.setArrowType(QtCore.Qt.RightArrow)
        expand_btn.setMaximumWidth(14)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 2, 0)
        layout.addWidget(
            subset_name_label, 1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        layout.addWidget(expand_btn)

        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        subset_name_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        expand_btn.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        expand_btn.clicked.connect(self._on_expand_clicked)

        self.subset_name_label = subset_name_label
        self.expand_btn = expand_btn

    def _on_expand_clicked(self):
        self.expand_changed.emit(self.family, not self._expanded)

    def set_expanded(self, expanded):
        if self._expanded == expanded:
            return

        self._expanded = expanded
        if expanded:
            self.expand_btn.setArrowType(QtCore.Qt.DownArrow)
        else:
            self.expand_btn.setArrowType(QtCore.Qt.RightArrow)


class InstanceListView(_AbstractInstanceView):
    def __init__(self, controller, parent):
        super(InstanceListView, self).__init__(parent)

        self.controller = controller

        instance_view = QtWidgets.QTreeView(self)
        instance_view.setObjectName("InstanceListView")
        instance_view.setHeaderHidden(True)
        instance_view.setIndentation(0)
        instance_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        instance_model = QtGui.QStandardItemModel()

        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(instance_model)
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setSortRole(SORT_VALUE_ROLE)
        proxy_model.setFilterKeyColumn(0)
        proxy_model.setDynamicSortFilter(True)

        instance_view.setModel(proxy_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(instance_view)

        instance_view.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )
        instance_view.collapsed.connect(self._on_collapse)
        instance_view.expanded.connect(self._on_expand)

        self._group_items = {}
        self._group_widgets = {}
        self._widgets_by_id = {}
        self.instance_view = instance_view
        self.instance_model = instance_model
        self.proxy_model = proxy_model

    def _on_expand(self, index):
        family = index.data(SORT_VALUE_ROLE)
        group_widget = self._group_widgets.get(family)
        if group_widget:
            group_widget.set_expanded(True)

    def _on_collapse(self, index):
        family = index.data(SORT_VALUE_ROLE)
        group_widget = self._group_widgets.get(family)
        if group_widget:
            group_widget.set_expanded(False)

    def refresh(self):
        instances_by_family = collections.defaultdict(list)
        families = set()
        for instance in self.controller.instances:
            family = instance.data["family"]
            families.add(family)
            instances_by_family[family].append(instance)

        new_group_items = []
        for family in families:
            if family in self._group_items:
                continue

            group_item = QtGui.QStandardItem()
            group_item.setData(family, SORT_VALUE_ROLE)
            group_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self._group_items[family] = group_item
            new_group_items.append(group_item)

        sort_at_the_end = False
        root_item = self.instance_model.invisibleRootItem()
        if new_group_items:
            sort_at_the_end = True
            root_item.appendRows(new_group_items)

        for group_item in new_group_items:
            index = self.instance_model.index(
                group_item.row(), group_item.column()
            )
            proxy_index = self.proxy_model.mapFromSource(index)
            family = group_item.data(SORT_VALUE_ROLE)
            widget = InstanceListGroupWidget(family, self.instance_view)
            widget.expand_changed.connect(self._on_group_expand_request)
            self._group_widgets[family] = widget
            self.instance_view.setIndexWidget(proxy_index, widget)

        for family in tuple(self._group_items.keys()):
            if family in families:
                continue

            group_item = self._group_items.pop(family)
            root_item.removeRow(group_item.row())
            widget = self._group_widgets.pop(family)
            widget.deleteLater()

        for family, group_item in self._group_items.items():
            to_remove = set()
            existing_mapping = {}

            group_index = self.instance_model.index(
                group_item.row(), group_item.column()
            )

            for idx in range(group_item.rowCount()):
                index = self.instance_model.index(idx, 0, group_index)
                instance_id = index.data(INSTANCE_ID_ROLE)
                to_remove.add(instance_id)
                existing_mapping[instance_id] = idx

            new_items = []
            new_items_with_instance = []
            for instance in instances_by_family[family]:
                instance_id = instance.data["uuid"]
                if instance_id in to_remove:
                    to_remove.remove(instance_id)
                    widget = self._widgets_by_id[instance_id]
                    widget.update_instance(instance)
                    continue

                item = QtGui.QStandardItem()
                item.setData(instance.data["subset"], SORT_VALUE_ROLE)
                item.setData(instance.data["uuid"], INSTANCE_ID_ROLE)
                new_items.append(item)
                new_items_with_instance.append((item, instance))

            idx_to_remove = []
            for instance_id in to_remove:
                idx_to_remove.append(existing_mapping[instance_id])

            for idx in reversed(sorted(idx_to_remove)):
                group_item.removeRows(idx, 1)

            for instance_id in to_remove:
                widget = self._widgets_by_id.pop(instance_id)
                widget.deleteLater()

            if new_items:
                sort_at_the_end = True

                group_item.appendRows(new_items)

                for item, instance in new_items_with_instance:
                    item_index = self.instance_model.index(
                        item.row(),
                        item.column(),
                        group_index
                    )
                    proxy_index = self.proxy_model.mapFromSource(item_index)
                    widget = InstanceListItemWidget(
                        instance, self.instance_view
                    )
                    self.instance_view.setIndexWidget(proxy_index, widget)
                    self._widgets_by_id[instance.data["uuid"]] = widget

            # Trigger sort at the end of refresh
            if sort_at_the_end:
                self.proxy_model.sort(0)

    def refresh_active_state(self):
        for widget in self._widgets_by_id.values():
            widget.update_instance_values()

    def get_selected_instances(self):
        instances = []
        instances_by_id = {}
        for instance in self.controller.instances:
            instance_id = instance.data["uuid"]
            instances_by_id[instance_id] = instance

        for index in self.instance_view.selectionModel().selectedIndexes():
            instance_id = index.data(INSTANCE_ID_ROLE)
            if instance_id is not None:
                instance = instances_by_id.get(instance_id)
                if instance:
                    instances.append(instance)

        return instances

    def set_selected_instances(self, instances):
        model = self.instance_view.model()
        instance_ids_by_family = collections.defaultdict(set)
        for instance in instances:
            family = instance.data["family"]
            instance_id = instance.data["uuid"]
            instance_ids_by_family[family].add(instance_id)

        indexes = []
        for family, group_item in self._group_items.items():
            selected_ids = instance_ids_by_family[family]
            if not selected_ids:
                continue

            group_index = self.instance_model.index(
                group_item.row(), group_item.column()
            )
            proxy_group_index = self.proxy_model.mapFromSource(group_index)
            has_indexes = False
            for row in range(group_item.rowCount()):
                index = model.index(row, 0, proxy_group_index)
                instance_id = index.data(INSTANCE_ID_ROLE)
                if instance_id in selected_ids:
                    indexes.append(index)
                    has_indexes = True

            if has_indexes:
                self.instance_view.setExpanded(proxy_group_index, True)

        selection_model = self.instance_view.selectionModel()
        first_item = True
        for index in indexes:
            if first_item:
                first_item = False
                select_type = QtCore.QItemSelectionModel.ClearAndSelect
            else:
                select_type = QtCore.QItemSelectionModel.Select
            selection_model.select(index, select_type)

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()

    def _on_group_expand_request(self, family, expanded):
        group_item = self._group_items.get(family)
        if not group_item:
            return

        group_index = self.instance_model.index(
            group_item.row(), group_item.column()
        )
        proxy_index = self.proxy_model.mapFromSource(group_index)
        self.instance_view.setExpanded(proxy_index, expanded)


class PublishOverlayFrame(QtWidgets.QFrame):
    hide_requested = QtCore.Signal()

    def __init__(self, parent):
        super(PublishOverlayFrame, self).__init__(parent)

        self.setObjectName("PublishOverlayFrame")

        info_frame = QtWidgets.QFrame(self)
        info_frame.setObjectName("PublishOverlay")

        content_widget = QtWidgets.QWidget(info_frame)
        content_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        info_layout = QtWidgets.QVBoxLayout(info_frame)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(content_widget)

        hide_btn = QtWidgets.QPushButton("Hide", content_widget)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)
        top_layout.addWidget(hide_btn)

        main_label = QtWidgets.QLabel("Publishing...", content_widget)
        main_label.setAlignment(QtCore.Qt.AlignCenter)

        instance_label = QtWidgets.QLabel("<Instance name>", content_widget)
        instance_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        plugin_label = QtWidgets.QLabel("<Plugin name>", content_widget)
        plugin_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        instance_plugin_layout = QtWidgets.QHBoxLayout()
        instance_plugin_layout.addWidget(instance_label, 1)
        instance_plugin_layout.addWidget(plugin_label, 1)

        progress_widget = QtWidgets.QProgressBar(content_widget)

        copy_log_btn = QtWidgets.QPushButton("Copy log", content_widget)
        stop_btn = QtWidgets.QPushButton("Stop", content_widget)
        refresh_btn = QtWidgets.QPushButton("Refresh", content_widget)
        publish_btn = QtWidgets.QPushButton("Publish", content_widget)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addWidget(copy_log_btn, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(refresh_btn, 0)
        footer_layout.addWidget(stop_btn, 0)
        footer_layout.addWidget(publish_btn, 0)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignCenter)

        content_layout.addLayout(top_layout)
        content_layout.addWidget(main_label)
        content_layout.addStretch(1)
        content_layout.addLayout(instance_plugin_layout)
        content_layout.addWidget(progress_widget)
        content_layout.addStretch(1)
        content_layout.addLayout(footer_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addStretch(1)
        main_layout.addWidget(info_frame, 0)

        hide_btn.clicked.connect(self.hide_requested)

        self.hide_btn = hide_btn

        self.main_label = main_label
        self.info_frame = info_frame

        self.instance_label = instance_label
        self.plugin_label = plugin_label
        self.progress_widget = progress_widget

        self.copy_log_btn = copy_log_btn
        self.stop_btn = stop_btn
        self.refresh_btn = refresh_btn
        self.publish_btn = publish_btn

    def set_instance(self, instance_name):
        self.instance_label.setText(instance_name)

    def set_plugin(self, plugin_name):
        self.plugin_label.setText(plugin_name)

    def set_progress_range(self, max_value):
        self.progress_widget.setMaximum(max_value)

    def set_progress(self, value):
        self.progress_widget.setValue(value)
