import os
from Qt import QtWidgets, QtCore, QtGui


def get_default_thumbnail_image_path():
    dirpath = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dirpath, "image_file.png")


class SubsetAttributesWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(SubsetAttributesWidget, self).__init__(parent)

        """
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
