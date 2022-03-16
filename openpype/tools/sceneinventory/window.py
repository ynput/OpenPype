import os
import sys

from Qt import QtWidgets, QtCore
import qtawesome
from avalon import io, api

from openpype import style
from openpype.tools.utils.delegates import VersionDelegate
from openpype.tools.utils.lib import (
    qt_app_context,
    preserve_expanded_rows,
    preserve_selection,
    FamilyConfigCache
)

from .model import (
    InventoryModel,
    FilterProxyModel
)
from .view import SceneInventoryView


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

        project_name = os.getenv("AVALON_PROJECT") or "<Project not set>"
        self.setWindowTitle("Scene Inventory 1.0 - {}".format(project_name))
        self.setObjectName("SceneInventory")
        # Maya only property
        self.setProperty("saveWindowPref", True)

        self.resize(1100, 480)

        # region control
        filter_label = QtWidgets.QLabel("Search", self)
        text_filter = QtWidgets.QLineEdit(self)

        outdated_only_checkbox = QtWidgets.QCheckBox(
            "Filter to outdated", self
        )
        outdated_only_checkbox.setToolTip("Show outdated files only")
        outdated_only_checkbox.setChecked(False)

        icon = qtawesome.icon("fa.arrow-up", color="white")
        update_all_button = QtWidgets.QPushButton(self)
        update_all_button.setToolTip("Update all outdated to latest version")
        update_all_button.setIcon(icon)

        icon = qtawesome.icon("fa.refresh", color="white")
        refresh_button = QtWidgets.QPushButton(self)
        refresh_button.setToolTip("Refresh")
        refresh_button.setIcon(icon)

        control_layout = QtWidgets.QHBoxLayout()
        control_layout.addWidget(filter_label)
        control_layout.addWidget(text_filter)
        control_layout.addWidget(outdated_only_checkbox)
        control_layout.addWidget(update_all_button)
        control_layout.addWidget(refresh_button)

        # endregion control
        family_config_cache = FamilyConfigCache(io)

        model = InventoryModel(family_config_cache)
        proxy = FilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setDynamicSortFilter(True)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view = SceneInventoryView(self)
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
        text_filter.textChanged.connect(self._on_text_filter_change)
        outdated_only_checkbox.stateChanged.connect(
            self._on_outdated_state_change
        )
        view.hierarchy_view_changed.connect(
            self._on_hierarchy_view_change
        )
        view.data_changed.connect(self.refresh)
        refresh_button.clicked.connect(self.refresh)
        update_all_button.clicked.connect(self._on_update_all)

        self._update_all_button = update_all_button
        self._outdated_only_checkbox = outdated_only_checkbox
        self._view = view
        self._model = model
        self._proxy = proxy
        self._version_delegate = version_delegate
        self._family_config_cache = family_config_cache

        self._first_show = True

        family_config_cache.refresh()

    def showEvent(self, event):
        super(SceneInventoryWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidentally perform Maya commands
        whilst trying to name an instance.

        """

    def refresh(self, items=None):
        with preserve_expanded_rows(
            tree_view=self._view,
            role=self._model.UniqueRole
        ):
            with preserve_selection(
                tree_view=self._view,
                role=self._model.UniqueRole,
                current_index=False
            ):
                kwargs = {"items": items}
                # TODO do not touch view's inner attribute
                if self._view._hierarchy_view:
                    kwargs["selected"] = self._view._selected
                self._model.refresh(**kwargs)

    def _on_hierarchy_view_change(self, enabled):
        self._proxy.set_hierarchy_view(enabled)
        self._model.set_hierarchy_view(enabled)

    def _on_text_filter_change(self, text_filter):
        self._proxy.setFilterRegExp(text_filter)

    def _on_outdated_state_change(self):
        self._proxy.set_filter_outdated(
            self._outdated_only_checkbox.isChecked()
        )

    def _on_update_all(self):
        self._view.update_all()


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
