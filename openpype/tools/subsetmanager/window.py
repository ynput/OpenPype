import os
import sys

from ... import api, style

from ...vendor import qtawesome
from ...vendor.Qt import QtWidgets, QtCore

from .. import lib as tools_lib
from ..models import RecursiveSortFilterProxyModel
from .model import (
    InstanceModel,
    InstanceRole,
    InstanceItemId
)
from .widgets import InstanceDetail


module = sys.modules[__name__]
module.window = None


class SubsetManagerWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SubsetManagerWindow, self).__init__(parent=parent)
        self.setWindowTitle("Subset Manager 0.1")
        self.setObjectName("SubsetManager")
        if not parent:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )

        self.resize(780, 430)

        # Trigger refresh on first called show
        self._first_show = True

        left_side_widget = QtWidgets.QWidget(self)

        # Header part
        header_widget = QtWidgets.QWidget(left_side_widget)

        # Filter input
        filter_input = QtWidgets.QLineEdit()
        filter_input.setPlaceholderText("Filter subsets..")

        # Refresh button
        icon = qtawesome.icon("fa.refresh", color="white")
        refresh_btn = QtWidgets.QPushButton()
        refresh_btn.setIcon(icon)

        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(filter_input)
        header_layout.addWidget(refresh_btn)

        # Instances view
        view = QtWidgets.QTreeView(left_side_widget)
        view.setIndentation(0)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        model = InstanceModel(view)
        proxy = RecursiveSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        view.setModel(proxy)

        left_side_layout = QtWidgets.QVBoxLayout(left_side_widget)
        left_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_layout.addWidget(header_widget)
        left_side_layout.addWidget(view)

        details_widget = InstanceDetail(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(left_side_widget, 0)
        layout.addWidget(details_widget, 1)

        filter_input.textChanged.connect(proxy.setFilterFixedString)
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        view.clicked.connect(self._on_activated)
        view.customContextMenuRequested.connect(self.on_context_menu)
        details_widget.save_triggered.connect(self._on_save)

        self.model = model
        self.proxy = proxy
        self.view = view
        self.details_widget = details_widget
        self.refresh_btn = refresh_btn

    def _on_refresh_clicked(self):
        self.refresh()

    def _on_activated(self, index):
        container = None
        item_id = None
        if index.isValid():
            container = index.data(InstanceRole)
            item_id = index.data(InstanceItemId)

        self.details_widget.set_details(container, item_id)

    def _on_save(self):
        host = api.registered_host()
        if not hasattr(host, "save_instances"):
            print("BUG: Host does not have \"save_instances\" method")
            return

        current_index = self.view.selectionModel().currentIndex()
        if not current_index.isValid():
            return

        item_id = current_index.data(InstanceItemId)
        if item_id != self.details_widget.item_id():
            return

        item_data = self.details_widget.instance_data_from_text()
        new_instances = []
        for index in tools_lib.iter_model_rows(self.model, 0):
            _item_id = index.data(InstanceItemId)
            if _item_id == item_id:
                instance_data = item_data
            else:
                instance_data = index.data(InstanceRole)
            new_instances.append(instance_data)

        host.save_instances(new_instances)

    def on_context_menu(self, point):
        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        # Prepare menu
        menu = QtWidgets.QMenu(self)
        actions = []
        host = api.registered_host()
        if hasattr(host, "remove_instance"):
            action = QtWidgets.QAction("Remove instance", menu)
            action.setData(host.remove_instance)
            actions.append(action)

        if hasattr(host, "select_instance"):
            action = QtWidgets.QAction("Select instance", menu)
            action.setData(host.select_instance)
            actions.append(action)

        if not actions:
            actions.append(QtWidgets.QAction("* Nothing to do", menu))

        for action in actions:
            menu.addAction(action)

        # Show menu under mouse
        global_point = self.view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action or not action.data():
            return

        # Process action
        # TODO catch exceptions
        function = action.data()
        function(point_index.data(InstanceRole))

        # Reset modified data
        self.refresh()

    def refresh(self):
        self.details_widget.set_details(None, None)
        self.model.refresh()

        host = api.registered_host()
        dev_mode = os.environ.get("AVALON_DEVELOP_MODE") or ""
        editable = False
        if dev_mode.lower() in ("1", "yes", "true", "on"):
            editable = hasattr(host, "save_instances")
        self.details_widget.set_editable(editable)

    def showEvent(self, *args, **kwargs):
        super(SubsetManagerWindow, self).showEvent(*args, **kwargs)
        if self._first_show:
            self._first_show = False
            self.refresh()


def show(root=None, debug=False, parent=None):
    """Display Scene Inventory GUI

    Arguments:
        debug (bool, optional): Run in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): When provided parent the interface
            to this QObject.

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    with tools_lib.application():
        window = Window(parent)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
