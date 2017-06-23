import sys
from maya import cmds
from avalon.vendor.Qt import QtWidgets, QtCore

self = sys.modules[__name__]
self._menu = "colorbleed"
self._parent = {
    widget.objectName(): widget
    for widget in QtWidgets.QApplication.topLevelWidgets()
}.get("MayaWindow")


def install():
    from . import interactive

    uninstall()

    def deferred():
        cmds.menu(self._menu,
                  label="Colorbleed",
                  tearOff=True,
                  parent="MayaWindow")

        # Modeling sub-menu
        cmds.menuItem("Modeling",
                      label="Modeling",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Combine", command=interactive.combine)

        # Rigging sub-menu
        cmds.menuItem("Rigging",
                      label="Rigging",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Auto Connect", command=interactive.auto_connect)
        cmds.menuItem("Clone (Local)", command=interactive.clone_localspace)
        cmds.menuItem("Clone (World)", command=interactive.clone_worldspace)
        cmds.menuItem("Clone (Special)", command=interactive.clone_special)
        cmds.menuItem("Create Follicle", command=interactive.follicle)

        # Animation sub-menu
        cmds.menuItem("Animation",
                      label="Animation",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Set Defaults", command=interactive.set_defaults)

        cmds.setParent("..", menu=True)

        cmds.menuItem(divider=True)

        cmds.menuItem("Auto Connect", command=interactive.auto_connect_assets)

    # Allow time for uninstallation to finish.
    QtCore.QTimer.singleShot(100, deferred)


def uninstall():
    app = QtWidgets.QApplication.instance()
    widgets = dict((w.objectName(), w) for w in app.allWidgets())
    menu = widgets.get(self._menu)

    if menu:
        menu.deleteLater()
        del(menu)
