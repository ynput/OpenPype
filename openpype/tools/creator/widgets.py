from ...vendor.Qt import QtWidgets, QtCore
from ... import style


class CreateErrorMessageBox(QtWidgets.QDialog):
    def __init__(
        self,
        family,
        subset_name,
        asset_name,
        exc_msg,
        formatted_traceback,
        parent=None
    ):
        super(CreateErrorMessageBox, self).__init__(parent)
        self.setWindowTitle("Creation failed")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        self.setStyleSheet(style.load_stylesheet())

        body_layout = QtWidgets.QVBoxLayout(self)

        main_label = (
            "<span style='font-size:18pt;'>Failed to create</span>"
        )
        main_label_widget = QtWidgets.QLabel(main_label, self)
        body_layout.addWidget(main_label_widget)

        item_name_template = (
            "<span style='font-weight:bold;'>Family:</span> {}<br>"
            "<span style='font-weight:bold;'>Subset:</span> {}<br>"
            "<span style='font-weight:bold;'>Asset:</span> {}<br>"
        )
        exc_msg_template = "<span style='font-weight:bold'>{}</span>"

        line = self._create_line()
        body_layout.addWidget(line)

        item_name = item_name_template.format(family, subset_name, asset_name)
        item_name_widget = QtWidgets.QLabel(
            item_name.replace("\n", "<br>"), self
        )
        body_layout.addWidget(item_name_widget)

        exc_msg = exc_msg_template.format(exc_msg.replace("\n", "<br>"))
        message_label_widget = QtWidgets.QLabel(exc_msg, self)
        body_layout.addWidget(message_label_widget)

        if formatted_traceback:
            tb_widget = QtWidgets.QLabel(
                formatted_traceback.replace("\n", "<br>"), self
            )
            tb_widget.setTextInteractionFlags(
                QtCore.Qt.TextBrowserInteraction
            )
            body_layout.addWidget(tb_widget)

        footer_widget = QtWidgets.QWidget(self)
        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        button_box = QtWidgets.QDialogButtonBox(QtCore.Qt.Vertical)
        button_box.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        button_box.accepted.connect(self._on_accept)
        footer_layout.addWidget(button_box, alignment=QtCore.Qt.AlignRight)
        body_layout.addWidget(footer_widget)

    def _on_accept(self):
        self.close()

    def _create_line(self):
        line = QtWidgets.QFrame(self)
        line.setFixedHeight(2)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line
