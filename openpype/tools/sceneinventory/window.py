import os
import sys

from Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome
from avalon import io, api

from avalon.tools import lib as tools_lib
from avalon.tools.delegates import VersionDelegate

from openpype import style

from .proxy import FilterProxyModel
from .model import InventoryModel
from openpype.tools.utils.lib import (
    qt_app_context,
    preserve_expanded_rows,
    preserve_selection
)
from .view import SceneInvetoryView


module = sys.modules[__name__]
module.window = None


class SceneInventoryWindow(QtWidgets.QDialog):
    """Scene Inventory window"""

    def __init__(self, parent=None):
        super(SceneInventoryWindow, self).__init__(parent)

        if not parent:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )

        self.resize(1100, 480)
        self.setWindowTitle(
            "Scene Inventory 1.0 - {}".format(
                os.getenv("AVALON_PROJECT") or "<Project not set>"
            )
        )
        self.setObjectName("SceneInventory")
        self.setProperty("saveWindowPref", True)  # Maya only property!

        # region control
        filter_label = QtWidgets.QLabel("Search", self)
        text_filter = QtWidgets.QLineEdit(self)

        outdated_only_checkbox = QtWidgets.QCheckBox(
            "Filter to outdated", self
        )
        outdated_only_checkbox.setToolTip("Show outdated files only")
        outdated_only_checkbox.setChecked(False)

        icon = qtawesome.icon("fa.refresh", color="white")
        refresh_button = QtWidgets.QPushButton(self)
        refresh_button.setIcon(icon)

        control_layout = QtWidgets.QHBoxLayout()
        control_layout.addWidget(filter_label)
        control_layout.addWidget(text_filter)
        control_layout.addWidget(outdated_only_checkbox)
        control_layout.addWidget(refresh_button)

        # endregion control
        self.family_config_cache = tools_lib.global_family_cache()

        model = InventoryModel(self.family_config_cache)
        proxy = FilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setDynamicSortFilter(True)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view = SceneInvetoryView(self)
        view.setModel(proxy)

        # set some nice default widths for the view
        view.setColumnWidth(0, 250)  # name
        view.setColumnWidth(1, 55)   # version
        view.setColumnWidth(2, 55)   # count
        view.setColumnWidth(3, 150)  # family
        view.setColumnWidth(4, 100)  # namespace

        # apply delegates
        version_delegate = VersionDelegate(io, self)
        column = model.Columns.index("version")
        view.setItemDelegateForColumn(column, version_delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(control_layout)
        layout.addWidget(view)

        # signals
        text_filter.textChanged.connect(proxy.setFilterRegExp)
        outdated_only_checkbox.stateChanged.connect(proxy.set_filter_outdated)
        refresh_button.clicked.connect(self.refresh)
        view.data_changed.connect(self.refresh)
        view.hierarchy_view.connect(model.set_hierarchy_view)
        view.hierarchy_view.connect(proxy.set_hierarchy_view)

        self._view = view
        self.refresh_button = refresh_button
        self.model = model
        self.proxy = proxy
        self._version_delegate = version_delegate

        self.family_config_cache.refresh()

        self._first_show = True

    def showEvent(self, event):
        super(SceneInventoryWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidently perform Maya commands
        whilst trying to name an instance.

        """

    def refresh(self, items=None):
        with preserve_expanded_rows(
            tree_view=self._view,
            role=self.model.UniqueRole
        ):
            with preserve_selection(
                tree_view=self._view,
                role=self.model.UniqueRole,
                current_index=False
            ):
                kwargs = {"items": items}
                if self.view._hierarchy_view:
                    # TODO do not touch view's inner attribute
                    kwargs["selected"] = self.view._selected
                self.model.refresh(**kwargs)


def show(root=None, debug=False, parent=None, items=None):
    """Display Scene Inventory GUI

    Arguments:
        debug (bool, optional): Run in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): When provided parent the interface
            to this QObject.
        items (list) of dictionaries - for injection of items for standalone
                testing

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    if debug is True:
        io.install()

        if not os.environ.get("AVALON_PROJECT"):
            any_project = next(
                project for project in io.projects()
                if project.get("active", True) is not False
            )

            api.Session["AVALON_PROJECT"] = any_project["name"]
        else:
            api.Session["AVALON_PROJECT"] = os.environ.get("AVALON_PROJECT")

    with qt_app_context():
        window = SceneInventoryWindow(parent)
        window.show()
        window.refresh(items=items)

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
