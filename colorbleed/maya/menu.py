import sys

from avalon.vendor.Qt import QtWidgets, QtCore

self = sys.modules[__name__]
self._menu = "colorbleed"
self._parent = {widget.objectName(): widget for widget in
                QtWidgets.QApplication.topLevelWidgets()}.get("MayaWindow")


def install():
    # from . import interactive

    uninstall()

    def deferred():

        import site
        import os

        # todo: replace path with server / library path
        site.addsitedir("C:\Users\User\Documents\development\scriptsmenu\python")

        from scriptsmenu import launchformaya
        import scriptsmenu.scriptsmenu as menu

        # load configuration of custon menu
        config_path = os.path.join(os.path.dirname(__file__), "menu.json")
        config = menu.load_configuration(config_path)

        # create menu in appliction
        cb_menu = launchformaya.main(title=self._menu, parent=self._parent)

        # apply configuration
        menu.load_from_configuration(cb_menu, config)

        # cmds.menu(self._menu,
        #           label=self._menu.capitalize(),
        #           tearOff=True,
        #           parent="MayaWindow")
        #
        # # Modeling sub-menu
        # cmds.menuItem("Modeling",
        #               label="Modeling",
        #               tearOff=True,
        #               subMenu=True,
        #               parent=self._menu)
        #
        # cmds.menuItem("Combine", command=interactive.combine)
        #
        # # Rigging sub-menu
        # cmds.menuItem("Rigging",
        #               label="Rigging",
        #               tearOff=True,
        #               subMenu=True,
        #               parent=self._menu)
        #
        # cmds.menuItem("Auto Connect", command=interactive.auto_connect)
        # cmds.menuItem("Clone (Local)", command=interactive.clone_localspace)
        # cmds.menuItem("Clone (World)", command=interactive.clone_worldspace)
        # cmds.menuItem("Clone (Special)", command=interactive.clone_special)
        # cmds.menuItem("Create Follicle", command=interactive.follicle)
        #
        # # Animation sub-menu
        # cmds.menuItem("Animation",
        #               label="Animation",
        #               tearOff=True,
        #               subMenu=True,
        #               parent=self._menu)
        #
        # cmds.menuItem("Set Defaults", command=interactive.set_defaults)
        #
        # cmds.setParent("..", menu=True)
        #
        # cmds.menuItem(divider=True)
        #
        # cmds.menuItem("Auto Connect", command=interactive.auto_connect_assets)

    # Allow time for uninstallation to finish.
    QtCore.QTimer.singleShot(100, deferred)


def uninstall():
    app = QtWidgets.QApplication.instance()
    widgets = dict((w.objectName(), w) for w in app.allWidgets())
    menu = widgets.get(self._menu)

    if menu:
        menu.deleteLater()
        del(menu)
