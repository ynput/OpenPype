import os
from Qt import QtWidgets, QtCore, QtGui

SEPARATORS = ("---separator---", "---")


def get_default_thumbnail_image_path():
    dirpath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dirpath, "image_file.png")


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

    def __init__(self, parent):
        super(SubsetAttributesWidget, self).__init__(parent)

        # TOP PART
        top_widget = QtWidgets.QWidget(self)

        # Global attributes
        global_attrs_widget = QtWidgets.QWidget(top_widget)

        variant_input = QtWidgets.QLineEdit(global_attrs_widget)
        subset_value_widget = QtWidgets.QLabel(global_attrs_widget)
        family_value_widget = QtWidgets.QLabel(global_attrs_widget)
        asset_value_widget = QtWidgets.QLabel(global_attrs_widget)
        task_value_widget = QtWidgets.QLabel(global_attrs_widget)

        subset_value_widget.setText("<Subset>")
        family_value_widget.setText("<Family>")
        asset_value_widget.setText("<Asset>")
        task_value_widget.setText("<Task>")

        global_attrs_layout = QtWidgets.QFormLayout(global_attrs_widget)
        global_attrs_layout.addRow("Name", variant_input)
        global_attrs_layout.addRow("Family", family_value_widget)
        global_attrs_layout.addRow("Asset", asset_value_widget)
        global_attrs_layout.addRow("Task", task_value_widget)
        global_attrs_layout.addRow("Subset", subset_value_widget)

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

        self.global_attrs_widget = global_attrs_widget
        self.thumbnail_widget = thumbnail_widget


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
        family_view = QtWidgets.QListView(self)
        family_model = QtGui.QStandardItemModel()
        family_view.setModel(family_model)

        variant_input = QtWidgets.QLineEdit(self)

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

        controller.add_reset_callback(self._on_control_reset)

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
        self._refresh_asset()

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

    def _on_control_reset(self):
        self.refresh()

    def moveEvent(self, event):
        super(CreateDialog, self).moveEvent(event)
        self._last_pos = self.pos()

    def showEvent(self, event):
        super(CreateDialog, self).showEvent(event)
        if self._last_pos is not None:
            self.move(self._last_pos)

    def _on_create(self):
        # TODO do some stuff
        if self.auto_close_checkbox.isChecked():
            self.hide()
