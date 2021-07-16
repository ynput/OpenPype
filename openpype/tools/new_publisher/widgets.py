import os
import re
import copy
import collections
from Qt import QtWidgets, QtCore, QtGui

from openpype.widgets.attribute_defs import create_widget_for_attr_def
from constants import INSTANCE_ID_ROLE

SEPARATORS = ("---separator---", "---")


def get_default_thumbnail_image_path():
    dirpath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dirpath, "image_file.png")


class ReadWriteLineEdit(QtWidgets.QFrame):
    textChanged = QtCore.Signal(str)

    def __init__(self, parent):
        super(ReadWriteLineEdit, self).__init__(parent)

        read_widget = QtWidgets.QLabel(self)
        edit_widget = QtWidgets.QLineEdit(self)

        self._editable = False
        edit_widget.setVisible(self._editable)
        read_widget.setVisible(not self._editable)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(read_widget)
        layout.addWidget(edit_widget)

        edit_widget.textChanged.connect(self.textChanged)

        self.read_widget = read_widget
        self.edit_widget = edit_widget

    def set_editable(self, editable):
        if self._editable == editable:
            return
        self._editable = editable
        self.set_edit(False)

    def set_edit(self, edit=None):
        if edit is None:
            edit = not self.edit_widget.isVisible()

        if not self._editable and edit:
            return

        if self.edit_widget.isVisible() == edit:
            return

        self.read_widget.setVisible(not edit)
        self.edit_widget.setVisible(edit)

    def setText(self, text):
        self.read_widget.setText(text)
        if self.edit_widget.text() != text:
            self.edit_widget.setText(text)

    def text(self):
        if self.edit_widget.isVisible():
            return self.edit_widget.text()
        return self.read_widget.text()


class GlobalAttrsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(GlobalAttrsWidget, self).__init__(parent)

        variant_input = ReadWriteLineEdit(self)
        family_value_widget = QtWidgets.QLabel(self)
        asset_value_widget = QtWidgets.QLabel(self)
        task_value_widget = QtWidgets.QLabel(self)
        subset_value_widget = QtWidgets.QLabel(self)

        subset_value_widget.setText("")
        family_value_widget.setText("")
        asset_value_widget.setText("")
        task_value_widget.setText("")

        main_layout = QtWidgets.QFormLayout(self)
        main_layout.addRow("Name", variant_input)
        main_layout.addRow("Family", family_value_widget)
        main_layout.addRow("Asset", asset_value_widget)
        main_layout.addRow("Task", task_value_widget)
        main_layout.addRow("Subset", subset_value_widget)

        self.variant_input = variant_input
        self.family_value_widget = family_value_widget
        self.asset_value_widget = asset_value_widget
        self.task_value_widget = task_value_widget
        self.subset_value_widget = subset_value_widget

    def set_current_instances(self, instances):
        editable = False
        if len(instances) == 0:
            variant = ""
            family = ""
            asset_name = ""
            task_name = ""
            subset_name = ""

        elif len(instances) == 1:
            instance = instances[0]
            if instance.creator is not None:
                editable = True

            unknown = "N/A"

            variant = instance.data.get("variant") or unknown
            family = instance.data.get("family") or unknown
            asset_name = instance.data.get("asset") or unknown
            task_name = instance.data.get("task") or unknown
            subset_name = instance.data.get("subset") or unknown

        else:
            families = set()
            asset_names = set()
            task_names = set()
            for instance in instances:
                families.add(instance.data.get("family") or unknown)
                asset_names.add(instance.data.get("asset") or unknown)
                task_names.add(instance.data.get("task") or unknown)

            multiselection_text = "< Multiselection >"

            variant = multiselection_text
            family = multiselection_text
            asset_name = multiselection_text
            task_name = multiselection_text
            subset_name = multiselection_text
            if len(families) < 4:
                family = " / ".join(families)

            if len(asset_names) < 4:
                asset_name = " / ".join(asset_names)

            if len(task_names) < 4:
                task_name = " / ".join(task_names)

        self.variant_input.set_editable(editable)

        self.variant_input.setText(variant)
        self.family_value_widget.setText(family)
        self.asset_value_widget.setText(asset_name)
        self.task_value_widget.setText(task_name)
        self.subset_value_widget.setText(subset_name)


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
        global_attrs_widget = GlobalAttrsWidget(top_widget)
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


class CreateDialog(QtWidgets.QDialog):
    def __init__(self, controller, parent=None):
        super(CreateDialog, self).__init__(parent)

        self.controller = controller

        self._last_pos = None
        self._asset_doc = None
        self._subset_names = None
        self._selected_creator = None

        self._prereq_available = False
        family_view = QtWidgets.QListView(self)
        family_model = QtGui.QStandardItemModel()
        family_view.setModel(family_model)

        variant_input = QtWidgets.QLineEdit(self)
        variant_input.setObjectName("VariantInput")

        variant_hints_btn = QtWidgets.QPushButton(self)
        variant_hints_btn.setFixedWidth(18)

        variant_hints_menu = QtWidgets.QMenu(variant_hints_btn)
        variant_hints_group = QtWidgets.QActionGroup(variant_hints_menu)
        variant_hints_btn.setMenu(variant_hints_menu)

        variant_layout = QtWidgets.QHBoxLayout()
        variant_layout.setContentsMargins(0, 0, 0, 0)
        variant_layout.setSpacing(0)
        variant_layout.addWidget(variant_input, 1)
        variant_layout.addWidget(variant_hints_btn, 0)

        asset_name_input = QtWidgets.QLineEdit(self)
        asset_name_input.setEnabled(False)

        subset_name_input = QtWidgets.QLineEdit(self)
        subset_name_input.setEnabled(False)

        checkbox_inputs = QtWidgets.QWidget(self)
        auto_close_checkbox = QtWidgets.QCheckBox(
            "Auto-close", checkbox_inputs
        )
        use_selection_checkbox = QtWidgets.QCheckBox(
            "Use selection", checkbox_inputs
        )

        checkbox_layout = QtWidgets.QHBoxLayout(checkbox_inputs)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.addWidget(auto_close_checkbox)
        checkbox_layout.addWidget(use_selection_checkbox)

        create_btn = QtWidgets.QPushButton("Create", self)
        create_btn.setEnabled(False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Family:", self))
        layout.addWidget(family_view, 1)
        layout.addWidget(QtWidgets.QLabel("Asset:", self))
        layout.addWidget(asset_name_input, 0)
        layout.addWidget(QtWidgets.QLabel("Name:", self))
        layout.addLayout(variant_layout, 0)
        layout.addWidget(QtWidgets.QLabel("Subset:", self))
        layout.addWidget(subset_name_input, 0)
        layout.addWidget(checkbox_inputs, 0)
        layout.addWidget(create_btn, 0)

        create_btn.clicked.connect(self._on_create)
        variant_input.returnPressed.connect(self._on_create)
        variant_input.textChanged.connect(self._on_variant_change)
        family_view.selectionModel().currentChanged.connect(
            self._on_family_change
        )
        variant_hints_menu.triggered.connect(self._on_variant_action)

        controller.add_plugins_refresh_callback(self._on_plugins_refresh)

        self.asset_name_input = asset_name_input
        self.subset_name_input = subset_name_input

        self.variant_input = variant_input
        self.variant_hints_btn = variant_hints_btn
        self.variant_hints_menu = variant_hints_menu
        self.variant_hints_group = variant_hints_group

        self.family_model = family_model
        self.family_view = family_view
        self.auto_close_checkbox = auto_close_checkbox
        self.use_selection_checkbox = auto_close_checkbox
        self.create_btn = create_btn

    @property
    def dbcon(self):
        return self.controller.dbcon

    def refresh(self):
        self._prereq_available = True

        # Refresh data before update of creators
        self._refresh_asset()
        # Then refresh creators which may trigger callbacks using refreshed
        #   data
        self._refresh_creators()

        if self._asset_doc is None:
            self.asset_name_input.setText("< Asset is not set >")
            self._prereq_available = False

        if self.family_model.rowCount() < 1:
            self._prereq_available = False

        self.create_btn.setEnabled(self._prereq_available)
        self.family_view.setEnabled(self._prereq_available)
        self.variant_input.setEnabled(self._prereq_available)
        self.variant_hints_btn.setEnabled(self._prereq_available)

    def _refresh_asset(self):
        asset_name = self.dbcon.Session.get("AVALON_ASSET")

        # Skip if asset did not change
        if self._asset_doc and self._asset_doc["name"] == asset_name:
            return

        # Make sure `_asset_doc` and `_subset_names` variables are reset
        self._asset_doc = None
        self._subset_names = None
        if asset_name is None:
            return

        asset_doc = self.dbcon.find_one({
            "type": "asset",
            "name": asset_name
        })
        self._asset_doc = asset_doc

        if asset_doc:
            self.asset_name_input.setText(asset_doc["name"])
            subset_docs = self.dbcon.find(
                {
                    "type": "subset",
                    "parent": asset_doc["_id"]
                },
                {"name": 1}
            )
            self._subset_names = set(subset_docs.distinct("name"))

    def _refresh_creators(self):
        # Refresh creators and add their families to list
        existing_items = {}
        old_families = set()
        for row in range(self.family_model.rowCount()):
            item = self.family_model.item(row, 0)
            family = item.data(QtCore.Qt.DisplayRole)
            existing_items[family] = item
            old_families.add(family)

        # Add new families
        new_families = set()
        for family, creator in self.controller.creators.items():
            # TODO add details about creator
            new_families.add(family)
            if family not in existing_items:
                item = QtGui.QStandardItem(family)
                self.family_model.appendRow(item)

        # Remove families that are no more available
        for family in (old_families - new_families):
            item = existing_items[family]
            self.family_model.takeRow(item.row())

        if self.family_model.rowCount() < 1:
            return

        # Make sure there is a selection
        indexes = self.family_view.selectedIndexes()
        if not indexes:
            index = self.family_model.index(0, 0)
            self.family_view.setCurrentIndex(index)

    def _on_plugins_refresh(self):
        # Trigger refresh only if is visible
        if self.isVisible():
            self.refresh()

    def _on_family_change(self, new_index, _old_index):
        family = None
        if new_index.isValid():
            family = new_index.data(QtCore.Qt.DisplayRole)

        creator = self.controller.creators.get(family)
        self._selected_creator = creator
        if not creator:
            return

        default_variants = creator.get_default_variants()
        if not default_variants:
            default_variants = ["Main"]

        default_variant = creator.get_default_variant()
        if not default_variant:
            default_variant = default_variants[0]

        for action in tuple(self.variant_hints_menu.actions()):
            self.variant_hints_menu.removeAction(action)
            action.deleteLater()

        for variant in default_variants:
            if variant in SEPARATORS:
                self.variant_hints_menu.addSeparator()
            elif variant:
                self.variant_hints_menu.addAction(variant)

        self.variant_input.setText(default_variant or "Main")

    def _on_variant_action(self, action):
        value = action.text()
        if self.variant_input.text() != value:
            self.variant_input.setText(value)

    def _on_variant_change(self, variant_value):
        if not self._prereq_available or not self._selected_creator:
            if self.subset_name_input.text():
                self.subset_name_input.setText("")
            return

        project_name = self.dbcon.Session["AVALON_PROJECT"]
        task_name = self.dbcon.Session.get("AVALON_TASK")

        asset_doc = copy.deepcopy(self._asset_doc)
        # Calculate subset name with Creator plugin
        subset_name = self._selected_creator.get_subset_name(
            variant_value, task_name, asset_doc, project_name
        )
        self.subset_name_input.setText(subset_name)

        self._validate_subset_name(subset_name, variant_value)

    def _validate_subset_name(self, subset_name, variant_value):
        # Get all subsets of the current asset
        existing_subset_names = set(self._subset_names)
        existing_subset_names_low = set(
            _name.lower()
            for _name in existing_subset_names
        )

        # Replace
        compare_regex = re.compile(re.sub(
            variant_value, "(.+)", subset_name, flags=re.IGNORECASE
        ))
        variant_hints = set()
        if variant_value:
            for _name in existing_subset_names:
                _result = compare_regex.search(_name)
                if _result:
                    variant_hints |= set(_result.groups())

        # Remove previous hints from menu
        for action in tuple(self.variant_hints_group.actions()):
            self.variant_hints_group.removeAction(action)
            self.variant_hints_menu.removeAction(action)
            action.deleteLater()

        # Add separator if there are hints and menu already has actions
        if variant_hints and self.variant_hints_menu.actions():
            self.variant_hints_menu.addSeparator()

        # Add hints to actions
        for variant_hint in variant_hints:
            action = self.variant_hints_menu.addAction(variant_hint)
            self.variant_hints_group.addAction(action)

        # Indicate subset existence
        if not variant_value:
            property_value = "empty"

        elif subset_name.lower() in existing_subset_names_low:
            # validate existence of subset name with lowered text
            #   - "renderMain" vs. "rendermain" mean same path item for
            #   windows
            property_value = "exists"
        else:
            property_value = "new"

        current_value = self.variant_input.property("state")
        if current_value != property_value:
            self.variant_input.setProperty("state", property_value)
            self.variant_input.style().polish(self.variant_input)

        variant_is_valid = variant_value.strip() != ""
        if variant_is_valid != self.create_btn.isEnabled():
            self.create_btn.setEnabled(variant_is_valid)

    def moveEvent(self, event):
        super(CreateDialog, self).moveEvent(event)
        self._last_pos = self.pos()

    def showEvent(self, event):
        super(CreateDialog, self).showEvent(event)
        if self._last_pos is not None:
            self.move(self._last_pos)

        self.refresh()

    def _on_create(self):
        indexes = self.family_view.selectedIndexes()
        if not indexes or len(indexes) > 1:
            return

        if not self.create_btn.isEnabled():
            return

        index = indexes[0]
        family = index.data(QtCore.Qt.DisplayRole)
        subset_name = self.subset_name_input.text()
        variant = self.variant_input.text()
        asset_name = self._asset_doc["name"]
        task_name = self.dbcon.Session.get("AVALON_TASK")
        options = {
            "useSelection": self.use_selection_checkbox.isChecked()
        }
        # Where to define these data?
        # - what data show be stored?
        instance_data = {
            "asset": asset_name,
            "task": task_name,
            "variant": variant,
            "family": family
        }

        error_info = None
        try:
            self.controller.create(family, subset_name, instance_data, options)

        except Exception as exc:
            # TODO better handling
            print(str(exc))

        if self.auto_close_checkbox.isChecked():
            self.hide()


class InstanceCardWidget(QtWidgets.QWidget):
    active_changed = QtCore.Signal(str, bool)

    def __init__(self, instance, item, parent):
        super(InstanceCardWidget, self).__init__(parent)

        self.instance = instance
        self.item = item

        subset_name_label = QtWidgets.QLabel(instance.data["subset"], self)
        active_checkbox = QtWidgets.QCheckBox(self)
        active_checkbox.setStyleSheet("background: transparent;")
        active_checkbox.setChecked(instance.data["active"])

        expand_btn = QtWidgets.QToolButton(self)
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
        if instance_value == checkbox_value == new_value:
            return

        # First change instance value and them change checkbox
        # - prevent to trigger `active_changed` signal
        self.instance.data["active"] = new_value
        self.active_checkbox.setChecked(new_value)

    def update_instance(self, instance):
        self.instance = instance
        self.set_active(instance.data["active"])

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
                select_type = QtCore.QItemSelectionModel.SelectCurrent
            else:
                select_type = QtCore.QItemSelectionModel.Select
            selection_model.select(index, select_type)


class InstanceListView(_AbstractInstanceView):
    def __init__(self, controller, parent):
        super(InstanceListView, self).__init__(parent)

        self.controller = controller

        instance_view = QtWidgets.QTreeView(self)
        instance_view.setHeaderHidden(True)
        instance_view.setIndentation(0)
        instance_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        instance_model = QtGui.QStandardItemModel()

        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy_model.setFilterKeyColumn(0)
        proxy_model.setDynamicSortFilter(True)
        proxy_model.setSortRole(QtCore.Qt.DisplayRole)
        proxy_model.setSourceModel(instance_model)

        instance_view.setModel(proxy_model)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(instance_view)

        instance_view.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )

        self._group_items = {}
        self.instance_view = instance_view
        self.instance_model = instance_model
        self.proxy_model = proxy_model

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

            group_item = QtGui.QStandardItem(family)
            self._group_items[family] = group_item
            new_group_items.append(group_item)

        root_item = self.instance_model.invisibleRootItem()
        if new_group_items:
            root_item.appendRows(new_group_items)

        for family in tuple(self._group_items.keys()):
            if family in families:
                continue

            group_item = self._group_items.pop(family)
            root_item.removeRow(group_item.row())

        for family, group_item in self._group_items.items():
            to_remove = set()
            existing_mapping = {}

            for idx in range(group_item.rowCount()):
                index = group_item.index(idx, 0)
                instance_id = index.data(INSTANCE_ID_ROLE)
                to_remove.add(instance_id)
                existing_mapping[instance_id] = idx

            new_items = []
            for instance in instances_by_family[family]:
                instance_id = instance.data["uuid"]
                if instance_id in to_remove:
                    to_remove.remove(instance_id)
                    continue

                item = QtGui.QStandardItem(instance.data["subset"])
                item.setData(instance.data["uuid"], INSTANCE_ID_ROLE)
                new_items.append(item)

            idx_to_remove = []
            for instance_id in to_remove:
                idx_to_remove.append(existing_mapping[instance_id])

            for idx in reversed(sorted(idx_to_remove)):
                group_item.removeRows(idx, 1)

            if new_items:
                group_item.appendRows(new_items)

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

            group_index = model.index(group_item.row(), group_item.column())
            has_indexes = False
            for row in range(group_item.rowCount()):
                index = model.index(row, 0, group_index)
                instance_id = index.data(INSTANCE_ID_ROLE)
                if instance_id in selected_ids:
                    indexes.append(index)
                    has_indexes = True

            if has_indexes:
                self.instance_view.setExpanded(group_index, True)

        selection_model = self.instance_view.selectionModel()
        first_item = True
        for index in indexes:
            if first_item:
                first_item = False
                select_type = QtCore.QItemSelectionModel.SelectCurrent
            else:
                select_type = QtCore.QItemSelectionModel.Select
            selection_model.select(index, select_type)

    def _on_selection_change(self, *_args):
        self.selection_changed.emit()
