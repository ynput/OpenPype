import sys

from Qt import QtWidgets, QtCore
from avalon import api, io

from openpype import style
from openpype.lib import register_event_callback
from openpype.tools.utils import (
    lib,
    PlaceholderLineEdit
)
from openpype.tools.utils.assets_widget import MultiSelectAssetsWidget

from .widgets import (
    SubsetWidget,
    VersionWidget,
    FamilyListView,
    ThumbnailWidget,
    RepresentationWidget,
    OverlayFrame
)

from openpype.modules import ModulesManager

module = sys.modules[__name__]
module.window = None


class LoaderWindow(QtWidgets.QDialog):
    """Asset loader interface"""

    tool_name = "loader"
    message_timeout = 5000

    def __init__(self, parent=None):
        super(LoaderWindow, self).__init__(parent)
        title = "Asset Loader 2.1"
        project_name = api.Session.get("AVALON_PROJECT")
        if project_name:
            title += " - {}".format(project_name)
        self.setWindowTitle(title)

        # Groups config
        self.groups_config = lib.GroupsConfig(io)
        self.family_config_cache = lib.FamilyConfigCache(io)

        # Enable minimize and maximize for app
        window_flags = QtCore.Qt.Window
        if not parent:
            window_flags |= QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        main_splitter = QtWidgets.QSplitter(self)

        # --- Left part ---
        left_side_splitter = QtWidgets.QSplitter(main_splitter)
        left_side_splitter.setOrientation(QtCore.Qt.Vertical)

        # Assets widget
        assets_widget = MultiSelectAssetsWidget(
            io, parent=left_side_splitter
        )
        assets_widget.set_current_asset_btn_visibility(True)

        # Families widget
        families_filter_view = FamilyListView(
            io, self.family_config_cache, left_side_splitter
        )
        left_side_splitter.addWidget(assets_widget)
        left_side_splitter.addWidget(families_filter_view)
        left_side_splitter.setStretchFactor(0, 65)
        left_side_splitter.setStretchFactor(1, 35)

        # --- Middle part ---
        # Subsets widget
        subsets_widget = SubsetWidget(
            io,
            self.groups_config,
            self.family_config_cache,
            tool_name=self.tool_name,
            parent=main_splitter
        )

        # --- Right part ---
        thumb_ver_splitter = QtWidgets.QSplitter(main_splitter)
        thumb_ver_splitter.setOrientation(QtCore.Qt.Vertical)

        thumbnail_widget = ThumbnailWidget(io, parent=thumb_ver_splitter)
        version_info_widget = VersionWidget(io, parent=thumb_ver_splitter)

        thumb_ver_splitter.addWidget(thumbnail_widget)
        thumb_ver_splitter.addWidget(version_info_widget)

        thumb_ver_splitter.setStretchFactor(0, 30)
        thumb_ver_splitter.setStretchFactor(1, 35)

        manager = ModulesManager()
        sync_server = manager.modules_by_name.get("sync_server")
        sync_server_enabled = False
        if sync_server is not None:
            sync_server_enabled = sync_server.enabled

        repres_widget = None
        if sync_server_enabled:
            repres_widget = RepresentationWidget(
                io, self.tool_name, parent=thumb_ver_splitter
            )
            thumb_ver_splitter.addWidget(repres_widget)

        main_splitter.addWidget(left_side_splitter)
        main_splitter.addWidget(subsets_widget)
        main_splitter.addWidget(thumb_ver_splitter)

        if sync_server_enabled:
            main_splitter.setSizes([250, 1000, 550])
        else:
            main_splitter.setSizes([250, 850, 200])

        footer_widget = QtWidgets.QWidget(self)

        message_label = QtWidgets.QLabel(footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(message_label, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(main_splitter, 1)
        layout.addWidget(footer_widget, 0)

        self.data = {
            "state": {
                "assetIds": None
            }
        }

        overlay_frame = OverlayFrame("Loading...", self)
        overlay_frame.setVisible(False)

        message_timer = QtCore.QTimer()
        message_timer.setInterval(self.message_timeout)
        message_timer.setSingleShot(True)

        message_timer.timeout.connect(self._on_message_timeout)

        families_filter_view.active_changed.connect(
            self._on_family_filter_change
        )
        assets_widget.selection_changed.connect(self.on_assetschanged)
        assets_widget.refresh_triggered.connect(self.on_assetschanged)
        subsets_widget.active_changed.connect(self.on_subsetschanged)
        subsets_widget.version_changed.connect(self.on_versionschanged)
        subsets_widget.refreshed.connect(self._on_subset_refresh)

        subsets_widget.load_started.connect(self._on_load_start)
        subsets_widget.load_ended.connect(self._on_load_end)
        if repres_widget:
            repres_widget.load_started.connect(self._on_load_start)
            repres_widget.load_ended.connect(self._on_load_end)

        self._sync_server_enabled = sync_server_enabled

        self._assets_widget = assets_widget
        self._families_filter_view = families_filter_view

        self._subsets_widget = subsets_widget

        self._version_info_widget = version_info_widget
        self._thumbnail_widget = thumbnail_widget
        self._repres_widget = repres_widget

        self._message_label = message_label
        self._message_timer = message_timer

        # TODO add overlay using stack widget
        self._overlay_frame = overlay_frame

        self.family_config_cache.refresh()
        self.groups_config.refresh()

        self._refresh()
        self._assetschanged()

        self._first_show = True

        register_event_callback("taskChanged", self.on_context_task_change)

    def resizeEvent(self, event):
        super(LoaderWindow, self).resizeEvent(event)
        self._overlay_frame.resize(self.size())

    def moveEvent(self, event):
        super(LoaderWindow, self).moveEvent(event)
        self._overlay_frame.move(0, 0)

    def showEvent(self, event):
        super(LoaderWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.setStyleSheet(style.load_stylesheet())
            if self._sync_server_enabled:
                self.resize(1800, 900)
            else:
                self.resize(1300, 700)
            lib.center_window(self)

    # -------------------------------
    # Delay calling blocking methods
    # -------------------------------

    def refresh(self):
        self.echo("Fetching results..")
        lib.schedule(self._refresh, 50, channel="mongo")

    def on_assetschanged(self, *args):
        self.echo("Fetching asset..")
        lib.schedule(self._assetschanged, 50, channel="mongo")

    def on_subsetschanged(self, *args):
        self.echo("Fetching subset..")
        lib.schedule(self._subsetschanged, 50, channel="mongo")

    def on_versionschanged(self, *args):
        self.echo("Fetching version..")
        lib.schedule(self._versionschanged, 150, channel="mongo")

    def set_context(self, context, refresh=True):
        self.echo("Setting context: {}".format(context))
        lib.schedule(lambda: self._set_context(context, refresh=refresh),
                     50, channel="mongo")

    def _on_load_start(self):
        # Show overlay and process events so it's repainted
        self._overlay_frame.setVisible(True)
        QtWidgets.QApplication.processEvents()

    def _hide_overlay(self):
        self._overlay_frame.setVisible(False)

    def _on_subset_refresh(self, has_item):
        self._subsets_widget.set_loading_state(
            loading=False, empty=not has_item
        )
        families = self._subsets_widget.get_subsets_families()
        self._families_filter_view.set_enabled_families(families)

    def _on_load_end(self):
        # Delay hiding as click events happened during loading should be
        #   blocked
        QtCore.QTimer.singleShot(100, self._hide_overlay)

    # ------------------------------
    def _on_family_filter_change(self, families):
        self._subsets_widget.set_family_filters(families)

    def on_context_task_change(self, *args, **kwargs):
        # Refresh families config
        self._families_filter_view.refresh()
        # Change to context asset on context change
        self._assets_widget.select_asset_by_name(io.Session["AVALON_ASSET"])

    def _refresh(self):
        """Load assets from database"""

        # Ensure a project is loaded
        project = io.find_one({"type": "project"}, {"type": 1})
        assert project, "Project was not found! This is a bug"

        self._assets_widget.refresh()
        self._assets_widget.setFocus()

        self._families_filter_view.refresh()

    def clear_assets_underlines(self):
        """Clear colors from asset data to remove colored underlines
        When multiple assets are selected colored underlines mark which asset
        own selected subsets. These colors must be cleared from asset data
        on selection change so they match current selection.
        """
        # TODO do not touch inner attributes of asset widget
        self._assets_widget.clear_underlines()

    def _assetschanged(self):
        """Selected assets have changed"""
        subsets_widget = self._subsets_widget
        # TODO do not touch subset widget inner attributes
        subsets_model = subsets_widget.model

        subsets_model.clear()
        self.clear_assets_underlines()

        asset_ids = self._assets_widget.get_selected_asset_ids()
        # Start loading
        subsets_widget.set_loading_state(
            loading=bool(asset_ids),
            empty=True
        )

        subsets_model.set_assets(asset_ids)
        subsets_widget.view.setColumnHidden(
            subsets_model.Columns.index("asset"),
            len(asset_ids) < 2
        )

        # Clear the version information on asset change
        self._thumbnail_widget.set_thumbnail(asset_ids)
        self._version_info_widget.set_version(None)

        self.data["state"]["assetIds"] = asset_ids

        # reset repre list
        if self._repres_widget is not None:
            self._repres_widget.set_version_ids([])

    def _subsetschanged(self):
        asset_ids = self.data["state"]["assetIds"]
        # Skip setting colors if not asset multiselection
        if not asset_ids or len(asset_ids) < 2:
            self.clear_assets_underlines()
            self._versionschanged()
            return

        selected_subsets = self._subsets_widget.get_selected_merge_items()

        asset_colors = {}
        asset_ids = []
        for subset_node in selected_subsets:
            asset_ids.extend(subset_node.get("assetIds", []))
        asset_ids = set(asset_ids)

        for subset_node in selected_subsets:
            for asset_id in asset_ids:
                if asset_id not in asset_colors:
                    asset_colors[asset_id] = []

                color = None
                if asset_id in subset_node.get("assetIds", []):
                    color = subset_node["subsetColor"]

                asset_colors[asset_id].append(color)

        self._assets_widget.set_underline_colors(asset_colors)

        # Set version in Version Widget
        self._versionschanged()

    def _versionschanged(self):
        items = self._subsets_widget.get_selected_subsets()
        version_doc = None
        version_docs = []
        for item in items:
            doc = item["version_document"]
            version_docs.append(doc)
            if version_doc is None:
                version_doc = doc

        self._version_info_widget.set_version(version_doc)

        thumbnail_src_ids = [
            version_doc["_id"]
            for version_doc in version_docs
        ]
        if not thumbnail_src_ids:
            thumbnail_src_ids = self._assets_widget.get_selected_asset_ids()

        self._thumbnail_widget.set_thumbnail(thumbnail_src_ids)

        if self._repres_widget is not None:
            version_ids = [doc["_id"] for doc in version_docs]
            self._repres_widget.set_version_ids(version_ids)

            # self._repres_widget.change_visibility("subset", len(rows) > 1)
            # self._repres_widget.change_visibility(
            #     "asset", len(asset_docs) > 1
            # )

    def _set_context(self, context, refresh=True):
        """Set the selection in the interface using a context.

        The context must contain `asset` data by name.

        Args:
            context (dict): The context to apply.
            refrest (bool): Trigger refresh on context set.
        """

        asset = context.get("asset", None)
        if asset is None:
            return

        if refresh:
            self._refresh()

        self._assets_widget.select_asset_by_name(asset)

    def _on_message_timeout(self):
        self._message_label.setText("")

    def echo(self, message):
        self._message_label.setText(str(message))
        print(message)
        self._message_timer.start()

    def closeEvent(self, event):
        # Kill on holding SHIFT
        modifiers = QtWidgets.QApplication.queryKeyboardModifiers()
        shift_pressed = QtCore.Qt.ShiftModifier & modifiers

        if shift_pressed:
            print("Force quit..")
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        print("Good bye")
        return super(LoaderWindow, self).closeEvent(event)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        ctrl_pressed = QtCore.Qt.ControlModifier & modifiers

        # Grouping subsets on pressing Ctrl + G
        if (ctrl_pressed and event.key() == QtCore.Qt.Key_G and
                not event.isAutoRepeat()):
            self.show_grouping_dialog()
            return

        super(LoaderWindow, self).keyPressEvent(event)
        event.setAccepted(True)  # Avoid interfering other widgets

    def show_grouping_dialog(self):
        subsets = self._subsets_widget
        if not subsets.is_groupable():
            self.echo("Grouping not enabled.")
            return

        selected = self._subsets_widget.get_selected_subsets()
        if not selected:
            self.echo("No selected subset.")
            return

        dialog = SubsetGroupingDialog(
            items=selected, groups_config=self.groups_config, parent=self
        )
        dialog.grouped.connect(self._assetschanged)
        dialog.show()


class SubsetGroupingDialog(QtWidgets.QDialog):
    grouped = QtCore.Signal()

    def __init__(self, items, groups_config, parent=None):
        super(SubsetGroupingDialog, self).__init__(parent=parent)
        self.setWindowTitle("Grouping Subsets")
        self.setMinimumWidth(250)
        self.setModal(True)

        self.items = items
        self.groups_config = groups_config
        # TODO do not touch inner attributes
        self.subsets = parent._subsets_widget
        self.asset_ids = parent.data["state"]["assetIds"]

        name = PlaceholderLineEdit(self)
        name.setPlaceholderText("Remain blank to ungroup..")

        # Menu for pre-defined subset groups
        name_button = QtWidgets.QPushButton()
        name_button.setFixedWidth(18)
        name_button.setFixedHeight(20)
        name_menu = QtWidgets.QMenu(name_button)
        name_button.setMenu(name_menu)

        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(name)
        name_layout.addWidget(name_button)
        name_layout.setContentsMargins(0, 0, 0, 0)

        group_btn = QtWidgets.QPushButton("Apply")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Group Name"))
        layout.addLayout(name_layout)
        layout.addWidget(group_btn)

        group_btn.clicked.connect(self.on_group)
        group_btn.setAutoDefault(True)
        group_btn.setDefault(True)

        self.name = name
        self.name_menu = name_menu

        self._build_menu()

    def _build_menu(self):
        menu = self.name_menu
        button = menu.parent()
        # Get and destroy the action group
        group = button.findChild(QtWidgets.QActionGroup)
        if group:
            group.deleteLater()

        active_groups = self.groups_config.active_groups(self.asset_ids)

        # Build new action group
        group = QtWidgets.QActionGroup(button)
        group_names = list()
        for data in sorted(active_groups, key=lambda x: x["order"]):
            name = data["name"]
            if name in group_names:
                continue
            group_names.append(name)
            icon = data["icon"]

            action = group.addAction(name)
            action.setIcon(icon)
            menu.addAction(action)

        group.triggered.connect(self._on_action_clicked)
        button.setEnabled(not menu.isEmpty())

    def _on_action_clicked(self, action):
        self.name.setText(action.text())

    def on_group(self):
        name = self.name.text().strip()
        self.subsets.group_subsets(name, self.asset_ids, self.items)

        with lib.preserve_selection(tree_view=self.subsets.view,
                                    current_index=False):
            self.grouped.emit()
            self.close()


def show(debug=False, parent=None, use_context=False):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): The Qt object to parent to.
        use_context (bool): Whether to apply the current context upon launch

    """

    # Remember window
    if module.window is not None:
        try:
            module.window.show()

            # If the window is minimized then unminimize it.
            if module.window.windowState() & QtCore.Qt.WindowMinimized:
                module.window.setWindowState(QtCore.Qt.WindowActive)

            # Raise and activate the window
            module.window.raise_()             # for MacOS
            module.window.activateWindow()     # for Windows
            module.window.refresh()
            return
        except (AttributeError, RuntimeError):
            # Garbage collected
            module.window = None

    if debug:
        import traceback
        sys.excepthook = lambda typ, val, tb: traceback.print_last()

        io.install()

        any_project = next(
            project for project in io.projects()
            if project.get("active", True) is not False
        )

        api.Session["AVALON_PROJECT"] = any_project["name"]
        module.project = any_project["name"]

    with lib.qt_app_context():
        window = LoaderWindow(parent)
        window.show()

        if use_context:
            context = {"asset": api.Session["AVALON_ASSET"]}
            window.set_context(context, refresh=True)
        else:
            window.refresh()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()


def cli(args):

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("project")

    args = parser.parse_args(args)
    project = args.project

    print("Entering Project: %s" % project)

    io.install()

    # Store settings
    api.Session["AVALON_PROJECT"] = project

    from avalon import pipeline

    # Find the set config
    _config = pipeline.find_config()
    if hasattr(_config, "install"):
        _config.install()
    else:
        print("Config `%s` has no function `install`" %
              _config.__name__)

    show()
