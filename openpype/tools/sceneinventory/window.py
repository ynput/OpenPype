import os
import sys

from Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome
from avalon import io, api, style


from avalon.tools import lib as tools_lib
from avalon.tools.delegates import VersionDelegate

from .proxy import FilterProxyModel
from .model import InventoryModel
from .view import View


module = sys.modules[__name__]
module.window = None


class SceneInventoryWindow(QtWidgets.QDialog):
    """Scene Inventory window"""

    def __init__(self, parent=None):
        super(SceneInventoryWindow, self).__init__(parent)

        self.resize(1100, 480)
        self.setWindowTitle(
            "Scene Inventory 1.0 - {}".format(
                os.getenv("AVALON_PROJECT") or "<Project not set>"
            )
        )
        self.setObjectName("SceneInventory")
        self.setProperty("saveWindowPref", True)  # Maya only property!

        layout = QtWidgets.QVBoxLayout(self)

        # region control
        control_layout = QtWidgets.QHBoxLayout()
        filter_label = QtWidgets.QLabel("Search")
        text_filter = QtWidgets.QLineEdit()

        outdated_only = QtWidgets.QCheckBox("Filter to outdated")
        outdated_only.setToolTip("Show outdated files only")
        outdated_only.setChecked(False)

        icon = qtawesome.icon("fa.refresh", color="white")
        refresh_button = QtWidgets.QPushButton()
        refresh_button.setIcon(icon)

        control_layout.addWidget(filter_label)
        control_layout.addWidget(text_filter)
        control_layout.addWidget(outdated_only)
        control_layout.addWidget(refresh_button)

        # endregion control
        self.family_config_cache = tools_lib.global_family_cache()

        model = InventoryModel(self.family_config_cache)
        proxy = FilterProxyModel()
        view = View()
        view.setModel(proxy)

        # apply delegates
        version_delegate = VersionDelegate(io, self)
        column = model.Columns.index("version")
        view.setItemDelegateForColumn(column, version_delegate)

        layout.addLayout(control_layout)
        layout.addWidget(view)

        self.filter = text_filter
        self.outdated_only = outdated_only
        self.view = view
        self.refresh_button = refresh_button
        self.model = model
        self.proxy = proxy

        # signals
        text_filter.textChanged.connect(self.proxy.setFilterRegExp)
        outdated_only.stateChanged.connect(self.proxy.set_filter_outdated)
        refresh_button.clicked.connect(self.refresh)
        view.data_changed.connect(self.refresh)
        view.hierarchy_view.connect(self.model.set_hierarchy_view)
        view.hierarchy_view.connect(self.proxy.set_hierarchy_view)

        # proxy settings
        proxy.setSourceModel(self.model)
        proxy.setDynamicSortFilter(True)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.data = {
            "delegates": {
                "version": version_delegate
            }
        }

        # set some nice default widths for the view
        self.view.setColumnWidth(0, 250)  # name
        self.view.setColumnWidth(1, 55)  # version
        self.view.setColumnWidth(2, 55)  # count
        self.view.setColumnWidth(3, 150)  # family
        self.view.setColumnWidth(4, 100)  # namespace

        self.family_config_cache.refresh()

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidently perform Maya commands
        whilst trying to name an instance.

        """

    def refresh(self, items=None):
        with tools_lib.preserve_expanded_rows(tree_view=self.view,
                                              role=self.model.UniqueRole):
            with tools_lib.preserve_selection(tree_view=self.view,
                                              role=self.model.UniqueRole,
                                              current_index=False):
                if self.view._hierarchy_view:
                    self.model.refresh(selected=self.view._selected,
                                       items=items)
                else:
                    self.model.refresh(items=items)


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

    with tools_lib.application():
        window = SceneInventoryWindow(parent)
        window.setStyleSheet(style.load_stylesheet())
        window.show()
        window.refresh(items=items)

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
