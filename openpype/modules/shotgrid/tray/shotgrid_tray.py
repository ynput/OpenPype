import os
import webbrowser

from qtpy import QtWidgets



class ShotgridTrayWrapper:
    module = None

    def __init__(self, module):
        self.module = module

    def show_batch_dialog(self):
        if self.module.leecher_manager_url:
            webbrowser.open(self.module.leecher_manager_url)

    def tray_menu(self, tray_menu):
        # Add login to user menu
        menu = QtWidgets.QMenu("Shotgrid", tray_menu)
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
