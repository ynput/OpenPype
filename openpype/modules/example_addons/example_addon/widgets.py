from Qt import QtWidgets


class MyExampleDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MyExampleDialog, self).__init__(parent)

        self.setWindowTitle("Connected modules")

        label_widget = QtWidgets.QLabel(self)

        ok_btn = QtWidgets.QPushButton("OK", self)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label_widget)
        layout.addLayout(btns_layout)

        self._label_widget = label_widget

    def set_connected_modules(self, connected_modules):
        if connected_modules:
            message = "\n".join(connected_modules)
        else:
            message = (
                "Other enabled modules/addons are not using my interface."
            )
        self._label_widget.setText(message)
