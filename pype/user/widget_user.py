import os
from Qt import QtCore, QtGui, QtWidgets
from pypeapp import style


class UserWidget(QtWidgets.QWidget):

    # loginSignal = QtCore.Signal(object, object, object)
    WIDTH = 300
    def __init__(self, module):

        super(UserWidget, self).__init__()

        self.module = module

        # Icon
        try:
            icon = module.icon
        except AttributeError:
            try:
                icon = module.parent.icon
            except AttributeError:
                pype_setup = os.getenv('PYPE_ROOT')
                fname = os.path.sep.join(
                    [pype_setup, "app", "resources", "icon.png"]
                )
                icon = QtGui.QIcon(fname)

        self.setWindowIcon(icon)

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        # Size setting
        self.setMinimumWidth(self.WIDTH)
        self.setStyleSheet(style.load_stylesheet())

        self.setLayout(self._main())
        self.setWindowTitle('Username Settings')

    def show(self, *args, **kwargs):
        super().show(*args, **kwargs)
        # Move widget to center of active screen
        screen = QtWidgets.QApplication.desktop().screen()
        screen_center = lambda self: (
            screen.rect().center() - self.rect().center()
        )
        self.move(screen_center(self))

    def _main(self):
        main_layout = QtWidgets.QVBoxLayout()

        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(10, 15, 10, 5)

        label_username = QtWidgets.QLabel("Username:")
        label_username.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        label_username.setTextFormat(QtCore.Qt.RichText)

        input_username = QtWidgets.QLineEdit()
        input_username.setPlaceholderText(
            QtCore.QCoreApplication.translate("main", "e.g. John Smith")
        )

        form_layout.addRow(label_username, input_username)

        btn_save = QtWidgets.QPushButton("Save")
        btn_save.clicked.connect(self.click_save)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.close)

        btn_group = QtWidgets.QHBoxLayout()
        btn_group.addStretch(1)
        btn_group.addWidget(btn_save)
        btn_group.addWidget(btn_cancel)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_group)

        self.input_username = input_username

        return main_layout

    def set_user(self, username):
        self.input_username.setText(username)

    def click_save(self):
        # all what should happen - validations and saving into appsdir
        username = self.input_username.text()
        self.module.save_credentials(username)
        self._close_widget()

    def closeEvent(self, event):
        event.ignore()
        self._close_widget()

    def _close_widget(self):
        self.hide()
