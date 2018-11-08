# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '..\CODE\github\pypeclub\pype-setup\temp\pype_project_settins_ui\login_dialogue.ui'
#
# Created by: PyQt5 UI code generator 5.7.1
#
# WARNING! All changes made in this file will be lost!

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from app import style
import credentials
import login_tools

class Login_Dialog_ui(QtWidgets.QWidget):

    SIZE_W = 300
    SIZE_H = 160

    def __init__(self):
        super().__init__()

        _translate = QtCore.QCoreApplication.translate

        self.resize(self.SIZE_W, self.SIZE_H)
        self.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.setStyleSheet(style.load_stylesheet())

        self.main = QtWidgets.QVBoxLayout()
        self.main.setObjectName("main")

        self.form = QtWidgets.QFormLayout()
        self.form.setContentsMargins(10, 15, 10, 5)
        self.form.setObjectName("form")

        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Condensed")
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(50)
        font.setKerning(True)

        self.ftsite_label = QtWidgets.QLabel("FTrack URL:")
        self.ftsite_label.setFont(font)
        self.ftsite_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.ftsite_label.setTextFormat(QtCore.Qt.RichText)
        self.ftsite_label.setObjectName("user_label")

        self.ftsite_input = QtWidgets.QLineEdit()
        self.ftsite_input.setEnabled(True)
        self.ftsite_input.setFrame(True)
        self.ftsite_input.setEnabled(False)
        self.ftsite_input.setReadOnly(True)
        self.ftsite_input.setObjectName("ftsite_input")

        self.user_label = QtWidgets.QLabel("Username:")
        self.user_label.setFont(font)
        self.user_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.user_label.setTextFormat(QtCore.Qt.RichText)
        self.user_label.setObjectName("user_label")

        self.user_input = QtWidgets.QLineEdit()
        self.user_input.setEnabled(True)
        self.user_input.setFrame(True)
        self.user_input.setObjectName("user_input")
        self.user_input.setPlaceholderText(_translate("main","user.name"))

        self.api_label = QtWidgets.QLabel("API Key:")
        self.api_label.setFont(font)
        self.api_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.api_label.setTextFormat(QtCore.Qt.RichText)
        self.api_label.setObjectName("api_label")

        self.api_input = QtWidgets.QLineEdit()
        self.api_input.setEnabled(True)
        self.api_input.setFrame(True)
        self.api_input.setObjectName("api_input")
        self.api_input.setPlaceholderText(_translate("main","e.g. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"))

        self.form.addRow(self.ftsite_label, self.ftsite_input)
        self.form.addRow(self.user_label, self.user_input)
        self.form.addRow(self.api_label,self.api_input)

        self.btnGroup = QtWidgets.QHBoxLayout()
        self.btnGroup.addStretch(1)
        self.btnGroup.setObjectName("btnGroup")

        self.btnEnter = QtWidgets.QPushButton("Login")
        self.btnEnter.setToolTip('Set Username and API Key with entered values')
        self.btnEnter.clicked.connect(self._enter_credentials)

        self.btnClose = QtWidgets.QPushButton("Close")
        self.btnClose.setToolTip('Close this window')
        self.btnClose.clicked.connect(self._close_widget)

        self.btnFtrack = QtWidgets.QPushButton("Ftrack")
        self.btnFtrack.setToolTip('Open browser for Login to Ftrack')
        self.btnFtrack.clicked.connect(self._open_ftrack)

        self.btnGroup.addWidget(self.btnFtrack)
        self.btnGroup.addWidget(self.btnEnter)
        self.btnGroup.addWidget(self.btnClose)

        self.main.addLayout(self.form)
        self.main.addLayout(self.btnGroup)

        self.setLayout(self.main)
        self.setWindowTitle('FTrack Login')
        self._set_site()
        self.show()

    def _set_site(self):
        try:
            txt = os.getenv('FTRACK_SERVER')
        except:
            txt = "FTrack site si is not set!"

        self.ftsite_input.setText(txt)

    def _enter_credentials(self):
        print("EnteredCredentials!")
        user = self.user_input.text()
        api = self.api_input.text()
        verification = credentials._check_credentials(user, api)

        if verification:
            print("SUCCESS")
            credentials._save_credentials(user, api)
            credentials._set_env(user, api)
            self._close_widget()

    def _open_ftrack(self):
        print("OpenWindow!")
        try:
            url = "pype.ftrackapp.com"
            self.loginSignal = QtCore.pyqtSignal(object, object, object)
            self._login_server_thread = login_tools.LoginServerThread()
            self._login_server_thread.loginSignal.connect(self.loginSignal)
            self._login_server_thread.start(url)
        except Exception as e:
            print(e)

    def _close_widget(self):
        sys.exit(app.exec_())


class Login_Dialog(Login_Dialog_ui):
    def __init__(self):
        super(Login_Dialog, self).__init__()

    def execute(self):
        self._check_credentials()


def getApp():
    return QtWidgets.QApplication(sys.argv)

def main():
    app = getApp()
    ui = Login_Dialog()
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

main()
