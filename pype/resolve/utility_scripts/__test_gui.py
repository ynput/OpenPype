#! python3
# -*- coding: utf-8 -*-

# DaVinci Resolve scripting proof of concept. Resolve page external switcher.
# Local or TCP/IP control mode.
# Refer to Resolve V15 public beta 2 scripting API documentation for host setup.
# Copyright 2018 Igor Riđanović, www.hdhead.com
from Qt.QtGui import *
from Qt.QtWidgets import *
from Qt.QtCore import *

import sys

# If API module not found assume we"re working as a remote control
try:
    import DaVinciResolveScript
    # Instantiate Resolve object
    resolve = DaVinciResolveScript.scriptapp("Resolve")
    checkboxState = False
except ImportError:
    print("Resolve API not found.")
    checkboxState = True

try:
    _encoding = QApplication.UnicodeUTF8

    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(str("Resolve Page Switcher"))
        Form.resize(561, 88)
        Form.setStyleSheet(str((
            "background-color: #282828;"
            "border-color: #555555;"
            "color: #929292;"
            "font-size: 13px;"
        )))
        self.horizontalLayout = QHBoxLayout(Form)
        self.horizontalLayout.setObjectName(str("horizontalLayout"))
        self.mediaButton = QPushButton(Form)
        self.mediaButton.setObjectName(str("mediaButton"))
        self.horizontalLayout.addWidget(self.mediaButton)
        self.editButton = QPushButton(Form)
        self.editButton.setObjectName(str("editButton"))
        self.horizontalLayout.addWidget(self.editButton)
        self.fusionButton = QPushButton(Form)
        self.fusionButton.setObjectName(str("fusionButton"))
        self.horizontalLayout.addWidget(self.fusionButton)
        self.colorButton = QPushButton(Form)
        self.colorButton.setObjectName(str("colorButton"))
        self.horizontalLayout.addWidget(self.colorButton)
        self.fairlightButton = QPushButton(Form)
        self.fairlightButton.setObjectName(str("fairlightButton"))
        self.horizontalLayout.addWidget(self.fairlightButton)
        self.deliverButton = QPushButton(Form)
        self.deliverButton.setObjectName(str("deliverButton"))
        self.horizontalLayout.addWidget(self.deliverButton)

        self.mediaButton.clicked.connect(lambda: self.pageswitch("media"))
        self.editButton.clicked.connect(lambda: self.pageswitch("edit"))
        self.fusionButton.clicked.connect(lambda: self.pageswitch("fusion"))
        self.colorButton.clicked.connect(lambda: self.pageswitch("color"))
        self.fairlightButton.clicked.connect(
            lambda: self.pageswitch("fairlight"))
        self.deliverButton.clicked.connect(lambda: self.pageswitch("deliver"))

        self.mediaButton.setStyleSheet(str("background-color: #181818;"))
        self.editButton.setStyleSheet(str("background-color: #181818;"))
        self.fusionButton.setStyleSheet(
            str("background-color: #181818;"))
        self.colorButton.setStyleSheet(str("background-color: #181818;"))
        self.fairlightButton.setStyleSheet(
            str("background-color: #181818;"))
        self.deliverButton.setStyleSheet(
            str("background-color: #181818;"))

        self.retranslateUi(Form)
        QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Resolve Page Switcher",
                                       "Resolve Page Switcher", None))
        self.mediaButton.setText(_translate("Form", "Media", None))
        self.editButton.setText(_translate("Form", "Edit", None))
        self.fusionButton.setText(_translate("Form", "Fusion", None))
        self.colorButton.setText(_translate("Form", "Color", None))
        self.fairlightButton.setText(_translate("Form", "Fairlight", None))
        self.deliverButton.setText(_translate("Form", "Deliver", None))

    def pageswitch(self, page):
        # Send page name to server to switch remote Resolve"s page
        try:
            resolve.OpenPage(page)
            print(f"Switched to {page}")
        except NameError:
            print("Resolve API not found. Run in remote mode instead?")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    Form = QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())
