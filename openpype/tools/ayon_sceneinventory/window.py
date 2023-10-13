from qtpy import QtWidgets, QtCore, QtGui
import qtawesome

from openpype import style, resources
from openpype.tools.utils.delegates import VersionDelegate
from openpype.tools.utils.lib import (
    preserve_expanded_rows,
    preserve_selection,
)
from openpype.tools.ayon_sceneinventory import SceneInventoryController

from .model import (
    InventoryModel,
    FilterProxyModel
)
from .view import SceneInventoryView


class ControllerVersionDelegate(VersionDelegate):
    """Version delegate that uses controller to get project.

    Original VersionDelegate is using 'AvalonMongoDB' object instead. Don't
    worry about the variable name, object is stored to '_dbcon' attribute.
    """

    def get_project_name(self):
        self._dbcon.get_current_project_name()


class SceneInventoryWindow(QtWidgets.QDialog):
    """Scene Inventory window"""

    def __init__(self, controller=None, parent=None):
        super(SceneInventoryWindow, self).__init__(parent)

        if controller is None:
            controller = SceneInventoryController()

        project_name = controller.get_current_project_name()
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Scene Inventory - {}".format(project_name))
        self.setObjectName("SceneInventory")

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

        model = InventoryModel(controller)
        proxy = FilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setDynamicSortFilter(True)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view = SceneInventoryView(controller, self)
        view.setModel(proxy)

        sync_enabled = controller.is_sync_server_enabled()
        view.setColumnHidden(model.active_site_col, not sync_enabled)
        view.setColumnHidden(model.remote_site_col, not sync_enabled)

        # set some nice default widths for the view
        view.setColumnWidth(0, 250)  # name
        view.setColumnWidth(1, 55)   # version
        view.setColumnWidth(2, 55)   # count
        view.setColumnWidth(3, 150)  # family
        view.setColumnWidth(4, 120)  # group
        view.setColumnWidth(5, 150)  # loader

        # apply delegates
        version_delegate = ControllerVersionDelegate(controller, self)
        column = model.Columns.index("version")
        view.setItemDelegateForColumn(column, version_delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(control_layout)
        layout.addWidget(view)

        show_timer = QtCore.QTimer()
        show_timer.setInterval(0)
        show_timer.setSingleShot(False)

        # signals
        show_timer.timeout.connect(self._on_show_timer)
        text_filter.textChanged.connect(self._on_text_filter_change)
        outdated_only_checkbox.stateChanged.connect(
            self._on_outdated_state_change
        )
        view.hierarchy_view_changed.connect(
            self._on_hierarchy_view_change
        )
        view.data_changed.connect(self._on_refresh_request)
        refresh_button.clicked.connect(self._on_refresh_request)
        update_all_button.clicked.connect(self._on_update_all)

        self._show_timer = show_timer
        self._show_counter = 0
        self._controller = controller
        self._update_all_button = update_all_button
        self._outdated_only_checkbox = outdated_only_checkbox
        self._view = view
        self._model = model
        self._proxy = proxy
        self._version_delegate = version_delegate

        self._first_show = True
        self._first_refresh = True

    def showEvent(self, event):
        super(SceneInventoryWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())

        self._show_counter = 0
        self._show_timer.start()

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidentally perform Maya commands
        whilst trying to name an instance.

        """

    def _on_refresh_request(self):
        """Signal callback to trigger 'refresh' without any arguments."""

        self.refresh()

    def refresh(self, containers=None):
        self._first_refresh = False
        self._controller.reset()
        with preserve_expanded_rows(
            tree_view=self._view,
            role=self._model.UniqueRole
        ):
            with preserve_selection(
                tree_view=self._view,
                role=self._model.UniqueRole,
                current_index=False
            ):
                kwargs = {"containers": containers}
                # TODO do not touch view's inner attribute
                if self._view._hierarchy_view:
                    kwargs["selected"] = self._view._selected
                self._model.refresh(**kwargs)

    def _on_show_timer(self):
        if self._show_counter < 3:
            self._show_counter += 1
            return
        self._show_timer.stop()
        self.refresh()

    def _on_hierarchy_view_change(self, enabled):
        self._proxy.set_hierarchy_view(enabled)
        self._model.set_hierarchy_view(enabled)

    def _on_text_filter_change(self, text_filter):
        if hasattr(self._proxy, "setFilterRegExp"):
            self._proxy.setFilterRegExp(text_filter)
        else:
            self._proxy.setFilterRegularExpression(text_filter)

    def _on_outdated_state_change(self):
        self._proxy.set_filter_outdated(
            self._outdated_only_checkbox.isChecked()
        )

    def _on_update_all(self):
        self._view.update_all()
