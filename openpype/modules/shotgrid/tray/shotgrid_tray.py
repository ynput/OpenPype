import os
import webbrowser

from Qt import QtWidgets

from openpype.modules.shotgrid.lib import credentials
from openpype.modules.shotgrid.tray.credential_dialog import (
    CredentialsDialog,
)


class ShotgridTrayWrapper:
    module = None
    credentials_dialog = None
    logged_user_label = None

    def __init__(self, module):
        self.module = module
        self.credentials_dialog = CredentialsDialog(module)
        self.credentials_dialog.login_changed.connect(self.set_login_label)
        self.logged_user_label = QtWidgets.QAction("")
        self.logged_user_label.setDisabled(True)
        self.set_login_label()

    def show_batch_dialog(self):
        if self.module.leecher_manager_url:
            webbrowser.open(self.module.leecher_manager_url)

    def show_connect_dialog(self):
        self.show_credential_dialog()

    def show_credential_dialog(self):
        self.credentials_dialog.show()
        self.credentials_dialog.activateWindow()
        self.credentials_dialog.raise_()

    def set_login_label(self):
        login = credentials.get_local_login()
        if login:
            self.logged_user_label.setText("{}".format(login))
        else:
            self.logged_user_label.setText(
                "No User logged in {0}".format(login)
            )

    def tray_menu(self, tray_menu):
        # Add login to user menu
        menu = QtWidgets.QMenu("Shotgrid", tray_menu)
        show_connect_action = QtWidgets.QAction("Connect to Shotgrid", menu)
        show_connect_action.triggered.connect(self.show_connect_dialog)
        menu.addAction(self.logged_user_label)
        menu.addSeparator()
        menu.addAction(show_connect_action)
        tray_menu.addMenu(menu)

        # Add manager to Admin menu
        for m in tray_menu.findChildren(QtWidgets.QMenu):
            if m.title() == "Admin":
                shotgrid_manager_action = QtWidgets.QAction(
                    "Shotgrid manager", menu
                )
                shotgrid_manager_action.triggered.connect(
                    self.show_batch_dialog
                )
                m.addAction(shotgrid_manager_action)

    def validate(self):
        login = credentials.get_local_login()

        if not login:
            self.show_credential_dialog()
        else:
            os.environ["OPENPYPE_SG_USER"] = login

        return True
