# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '..\CODE\github\pypeclub\pype-setup\temp\pype_project_settins_ui\login_dialogue.ui'
#
# Created by: PyQt5 UI code generator 5.7.1
#
# WARNING! All changes made in this file will be lost!

import sys
from PyQt5 import QtCore, QtGui, QtWidgets

from app import style




class Login_Dialog_ui(object):

    SIZE_W = 250
    SIZE_H = 300

    def __init__(self):
        super(Login_Dialog_ui, self).__init__()
        self.Dialog = QtWidgets.QDialog()
        self.Dialog.setStyleSheet(style.load_stylesheet())
        self.Dialog.setObjectName("Dialog")
        self.Dialog.resize(self.SIZE_W, self.SIZE_H)
        self.Dialog.setMinimumSize(QtCore.QSize(self.SIZE_W, self.SIZE_H))
        self.verticalLayoutWidget = QtWidgets.QWidget(self.Dialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(0, 0, self.SIZE_W + 1, self.SIZE_H + 1))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(10, 5, 10, 5)
        self.verticalLayout.setObjectName("verticalLayout")

        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Condensed")
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(50)
        font.setKerning(True)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        if self.ftracksite:
            self.site_label = QtWidgets.QLabel(self.verticalLayoutWidget)
            sizePolicy.setHeightForWidth(self.site_label.sizePolicy().hasHeightForWidth())
            self.site_label.setSizePolicy(sizePolicy)
            self.site_label.setMinimumSize(QtCore.QSize(150, 28))
            self.site_label.setFont(font)
            self.site_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            self.site_label.setTextFormat(QtCore.Qt.RichText)
            # self.site_label.setAlignment(QtCore.Qt.AlignCenter)
            self.site_label.setObjectName("site_label")
            self.verticalLayout.addWidget(self.site_label)

            self.site_input = QtWidgets.QLineEdit(self.verticalLayoutWidget)
            self.site_input.setEnabled(True)
            self.site_input.setFrame(True)
            self.site_input.setFrame(True)
            self.site_input.setReadOnly(True)
            self.site_input.setObjectName("site_input")
            self.verticalLayout.addWidget(self.site_input)

        self.user_label = QtWidgets.QLabel(self.verticalLayoutWidget)
        sizePolicy.setHeightForWidth(self.user_label.sizePolicy().hasHeightForWidth())
        self.user_label.setSizePolicy(sizePolicy)
        self.user_label.setMinimumSize(QtCore.QSize(150, 28))
        self.user_label.setFont(font)
        self.user_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.user_label.setTextFormat(QtCore.Qt.RichText)
        # self.user_label.setAlignment(QtCore.Qt.AlignCenter)
        self.user_label.setObjectName("user_label")
        self.verticalLayout.addWidget(self.user_label)

        self.user_input = QtWidgets.QLineEdit(self.verticalLayoutWidget)
        self.user_input.setEnabled(True)
        self.user_input.setFrame(True)
        self.user_input.setObjectName("user_input")
        self.verticalLayout.addWidget(self.user_input)

        self.api_label = QtWidgets.QLabel(self.verticalLayoutWidget)
        sizePolicy.setHeightForWidth(self.api_label.sizePolicy().hasHeightForWidth())
        self.api_label.setSizePolicy(sizePolicy)
        self.api_label.setMinimumSize(QtCore.QSize(150, 28))
        self.api_label.setFont(font)
        self.api_label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.api_label.setTextFormat(QtCore.Qt.RichText)
        # self.api_label.setAlignment(QtCore.Qt.AlignCenter)
        self.api_label.setObjectName("api_label")
        self.verticalLayout.addWidget(self.api_label)

        self.api_input = QtWidgets.QLineEdit(self.verticalLayoutWidget)
        self.api_input.setEnabled(True)
        self.api_input.setFrame(True)
        self.api_input.setObjectName("api_input")
        self.verticalLayout.addWidget(self.api_input)

        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)


        # button.setToolTip('This is an example button')
        # button.move(100,70)
        self.btn_ftrack = QtWidgets.QPushButton("Login", self.verticalLayoutWidget)
        self.btn_ftrack.resize(10,10)
        # self.btn_ftrack.move(100,70)
        self.verticalLayout.addWidget(self.btn_ftrack)

        self.buttonBox = QtWidgets.QDialogButtonBox(self.verticalLayoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(self.Dialog)
        self.buttonBox.accepted.connect(self.execute)
        self.buttonBox.rejected.connect(self.Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(self.Dialog)
        self.Dialog.setTabOrder(self.user_input, self.api_input)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", self.ui_title))
        self.site_label.setText(_translate("Dialog", "FTrack URL:"))
        if self.ftracksite:
            self.site_input.setText(_translate("Dialog", self.ftracksite))
        self.user_label.setText(_translate("Dialog", "Username:"))
        self.user_input.setPlaceholderText(_translate("Dialog", "user.name"))
        self.api_label.setText(_translate("Dialog", "API Key:"))
        self.api_input.setPlaceholderText(_translate("Dialog", "eg.:"))

    def show(self):
        self.Dialog.show()


class Login_Dialog(Login_Dialog_ui):
    def __init__(self, ui_title="Dialog", ftracksite=None):
        self.ui_title = ui_title
        self.ftracksite = ftracksite
        super(Login_Dialog, self).__init__()
        self.user_input.textChanged.connect(self._user_changed)
        self.api_input.textChanged.connect(self._api_changed)

    def _user_changed(self):
        self.user_input.setStyleSheet("")

    def _api_changed(self):
        self.api_input.setStyleSheet("")
        # print(self.passw_input.text())

    def _invalid_input(self,entity):
        entity.setStyleSheet("border: 1px solid red;")

    def _check_credentials(self):
        logged = False

        user = self.user_input.text()
        api = self.api_input.text()

        if user == "":
            self._invalid_input(self.user_input)
        elif True:
            # IF user exist
            pass

        if api == "":
            self._invalid_input(self.api_input)
        elif True:
            # IF is api ok exist - Session creation
            pass

        if logged is True:
            self.close()

    def execute(self):
        self._check_credentials()


def getApp():
    return QtWidgets.QApplication(sys.argv)

def main():
    app = QtWidgets.QApplication(sys.argv)
    ui = Login_Dialog("Ftrack Login","pype")
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

main()
