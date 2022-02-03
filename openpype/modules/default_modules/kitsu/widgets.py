from Qt import QtWidgets

from openpype.style import load_stylesheet


class MyExampleDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MyExampleDialog, self).__init__(parent)

        self.setWindowTitle("Connected modules")

        msg = "This is example dialog of Kitsu."
        label_widget = QtWidgets.QLabel(msg, self)

        ok_btn = QtWidgets.QPushButton("OK", self)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label_widget)
        layout.addLayout(btns_layout)

        ok_btn.clicked.connect(self._on_ok_clicked)

        self._label_widget = label_widget

        self.setStyleSheet(load_stylesheet())

    def _on_ok_clicked(self):
        self.done(1)
