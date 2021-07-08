import os
import re
import copy
from Qt import QtWidgets, QtCore, QtGui

SEPARATORS = ("---separator---", "---")


def get_default_thumbnail_image_path():
    dirpath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dirpath, "image_file.png")


class GlobalAttrsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(GlobalAttrsWidget, self).__init__(parent)

        variant_input = QtWidgets.QLineEdit(self)
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
        if len(instances) == 1:
            instance = instances[0]
            unknown = "N/A"

            variant = instance.data.get("variant") or unknown
            family = instance.data.get("family") or unknown
            asset_name = instance.data.get("asset") or unknown
            task_name = instance.data.get("task") or unknown
            subset_name = instance.data.get("subset") or unknown

            self.variant_input.setText(variant)
            self.family_value_widget.setText(family)
            self.asset_value_widget.setText(asset_name)
            self.task_value_widget.setText(task_name)
            self.subset_value_widget.setText(subset_name)
            return
        # TODO what to do when mulsiselection?


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
        # TODO they should be scrollable
        family_attrs_widget = QtWidgets.QWidget(bottom_widget)
        publish_attrs_widget = QtWidgets.QWidget(bottom_widget)

        bottom_layout = QtWidgets.QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(family_attrs_widget, 1)
        bottom_layout.addWidget(publish_attrs_widget, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(top_widget, 0)
        layout.addWidget(bottom_widget, 1)

        self.controller = controller
        self.global_attrs_widget = global_attrs_widget
        self.thumbnail_widget = thumbnail_widget

    def set_current_instances(self, instances):
        self.global_attrs_widget.set_current_instances(instances)


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

        controller.add_on_reset_callback(self._on_control_reset)

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

    def _on_control_reset(self):
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
