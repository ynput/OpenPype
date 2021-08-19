import os
import copy
import json
import collections
from Qt import QtWidgets, QtCore, QtGui

from openpype.pipeline import KnownPublishError

from openpype.widgets.attribute_defs import create_widget_for_attr_def

from openpype.tools.flickcharm import FlickCharm

from .icons import (
    get_icon,
    get_pixmap
)


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

        delegate = QtWidgets.QStyledItemDelegate()
        self.setItemDelegate(delegate)

        model = TasksModel(controller)
        self.setModel(model)

        self.currentIndexChanged.connect(self._on_index_change)

        self._delegate = delegate
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
        for instance in self._current_instances:
            if variant_value is not None:
                instance.data["variant"] = variant_value

            if asset_name is not None:
                instance.data["asset"] = asset_name

            if task_name is not None:
                instance.data["task"] = task_name

            new_variant_value = instance.data.get("variant")
            new_asset_name = instance.data.get("asset")
            new_task_name = instance.data.get("task")

            asset_doc = asset_docs_by_name[new_asset_name]

            new_subset_name = instance.creator.get_subset_name(
                new_variant_value, new_task_name, asset_doc, project_name
            )
            instance.data["subset"] = new_subset_name

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
        self.set_btns_visible(any_changed)

    def _on_variant_change(self):
        self._on_value_change()

    def _on_asset_change(self):
        asset_names = self.asset_value_widget.get_selected_items()
        self.task_value_widget.set_asset_names(asset_names)
        self._on_value_change()

    def _on_task_change(self):
        self._on_value_change()

    def set_btns_visible(self, visible):
        self.cancel_btn.setVisible(visible)
        self.submit_btn.setVisible(visible)

    def set_btns_enabled(self, enabled):
        self.cancel_btn.setEnabled(enabled)
        self.submit_btn.setEnabled(enabled)

    def set_current_instances(self, instances):
        self.set_btns_visible(False)

        self._current_instances = instances

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


class PublishOverlayFrame(QtWidgets.QFrame):
    hide_requested = QtCore.Signal()

    def __init__(self, controller, parent):
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

        main_label = QtWidgets.QLabel(content_widget)
        main_label.setObjectName("PublishOverlayMainLabel")
        main_label.setAlignment(QtCore.Qt.AlignCenter)

        message_label = QtWidgets.QLabel(content_widget)
        message_label.setAlignment(QtCore.Qt.AlignCenter)

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
        copy_log_btn.setVisible(False)

        stop_btn = QtWidgets.QPushButton(content_widget)
        stop_btn.setIcon(get_icon("stop"))

        refresh_btn = QtWidgets.QPushButton(content_widget)
        refresh_btn.setIcon(get_icon("refresh"))

        validate_btn = QtWidgets.QPushButton(content_widget)
        validate_btn.setIcon(get_icon("validate"))

        publish_btn = QtWidgets.QPushButton(content_widget)
        publish_btn.setIcon(get_icon("play"))

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addWidget(copy_log_btn, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(refresh_btn, 0)
        footer_layout.addWidget(stop_btn, 0)
        footer_layout.addWidget(validate_btn, 0)
        footer_layout.addWidget(publish_btn, 0)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(5)
        content_layout.setAlignment(QtCore.Qt.AlignCenter)

        content_layout.addLayout(top_layout)
        content_layout.addWidget(main_label)
        content_layout.addStretch(1)
        content_layout.addWidget(message_label)
        content_layout.addStretch(1)
        content_layout.addLayout(instance_plugin_layout)
        content_layout.addWidget(progress_widget)
        content_layout.addStretch(1)
        content_layout.addLayout(footer_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addStretch(1)
        main_layout.addWidget(info_frame, 0)

        hide_btn.clicked.connect(self.hide_requested)
        copy_log_btn.clicked.connect(self._on_copy_log)

        controller.add_instance_change_callback(self._on_instance_change)
        controller.add_plugin_change_callback(self._on_plugin_change)
        controller.add_plugins_refresh_callback(self._on_publish_reset)
        controller.add_publish_started_callback(self._on_publish_start)
        controller.add_publish_stopped_callback(self._on_publish_stop)

        self.controller = controller

        self.hide_btn = hide_btn

        self.main_label = main_label
        self.message_label = message_label
        self.info_frame = info_frame

        self.instance_label = instance_label
        self.plugin_label = plugin_label
        self.progress_widget = progress_widget

        self.copy_log_btn = copy_log_btn
        self.stop_btn = stop_btn
        self.refresh_btn = refresh_btn
        self.validate_btn = validate_btn
        self.publish_btn = publish_btn

    def set_progress_range(self, max_value):
        # TODO implement triggers for this method
        self.progress_widget.setMaximum(max_value)

    def set_progress(self, value):
        # TODO implement triggers for this method
        self.progress_widget.setValue(value)

    def _on_publish_reset(self):
        self._set_success_property("")
        self.main_label.setText("Hit publish! (if you want)")
        self.message_label.setText("")
        self.copy_log_btn.setVisible(False)

    def _on_publish_start(self):
        self._set_success_property(-1)
        self.main_label.setText("Publishing...")

    def _on_instance_change(self, context, instance):
        """Change instance label when instance is going to be processed."""
        if instance is None:
            new_name = (
                context.data.get("label")
                or getattr(context, "label", None)
                or context.data.get("name")
                or "Context"
            )
        else:
            new_name = (
                instance.data.get("label")
                or getattr(instance, "label", None)
                or instance.data["name"]
            )

        self.instance_label.setText(new_name)
        QtWidgets.QApplication.processEvents()

    def _on_plugin_change(self, plugin):
        """Change plugin label when instance is going to be processed."""
        plugin_name = plugin.__name__
        if hasattr(plugin, "label") and plugin.label:
            plugin_name = plugin.label

        self.plugin_label.setText(plugin_name)
        QtWidgets.QApplication.processEvents()

    def _on_publish_stop(self):
        error = self.controller.get_publish_crash_error()
        if error:
            self._set_error(error)
            return

        validation_errors = self.controller.get_validation_errors()
        if validation_errors:
            self._set_validation_errors(validation_errors)
            return

        if self.controller.has_finished:
            self._set_finished()

    def _set_error(self, error):
        self.main_label.setText("Error happened")
        if isinstance(error, KnownPublishError):
            msg = str(error)
        else:
            msg = (
                "Something went wrong. Send report"
                " to your supervisor or OpenPype."
            )
        self.message_label.setText(msg)
        self._set_success_property(0)
        self.copy_log_btn.setVisible(True)

    def _set_validation_errors(self, validation_errors):
        # TODO implement
        pass

    def _set_finished(self):
        self.main_label.setText("Finished")
        self._set_success_property(1)

    def _set_success_property(self, success):
        self.info_frame.setProperty("success", str(success))
        self.info_frame.style().polish(self.info_frame)

    def _on_copy_log(self):
        logs = self.controller.get_publish_logs()
        logs_string = json.dumps(logs, indent=4)

        mime_data = QtCore.QMimeData()
        mime_data.setText(logs_string)
        QtWidgets.QApplication.instance().clipboard().setMimeData(
            mime_data
        )
