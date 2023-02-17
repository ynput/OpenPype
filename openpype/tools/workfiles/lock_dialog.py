from qtpy import QtWidgets, QtCore, QtGui
from openpype.style import load_stylesheet, get_app_icon_path

from openpype.pipeline.workfile.lock_workfile import get_workfile_lock_data


class WorkfileLockDialog(QtWidgets.QDialog):
    def __init__(self, workfile_path, parent=None):
        super(WorkfileLockDialog, self).__init__(parent)
        self.setWindowTitle("Warning")
        icon = QtGui.QIcon(get_app_icon_path())
        self.setWindowIcon(icon)

        data = get_workfile_lock_data(workfile_path)

        message = "{} on {} machine is working on the same workfile.".format(
            data["username"],
            data["hostname"]
        )

        msg_label = QtWidgets.QLabel(message, self)

        btns_widget = QtWidgets.QWidget(self)

        cancel_btn = QtWidgets.QPushButton("Cancel", btns_widget)
        ignore_btn = QtWidgets.QPushButton("Ignore lock", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.setSpacing(10)
        btns_layout.addStretch(1)
        btns_layout.addWidget(cancel_btn, 0)
        btns_layout.addWidget(ignore_btn, 0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.addWidget(msg_label, 1, QtCore.Qt.AlignCenter),
        main_layout.addSpacing(10)
        main_layout.addWidget(btns_widget, 0)

        cancel_btn.clicked.connect(self.reject)
        ignore_btn.clicked.connect(self.accept)

    def showEvent(self, event):
        super(WorkfileLockDialog, self).showEvent(event)

        self.setStyleSheet(load_stylesheet())
