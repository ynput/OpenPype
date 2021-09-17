import sys

from Qt import QtWidgets, QtCore, QtGui

from avalon import style
from avalon.api import AvalonMongoDB
from openpype.tools.utils import lib as tools_lib
from openpype.tools.loader.widgets import (
    ThumbnailWidget,
    VersionWidget,
    FamilyListView,
    RepresentationWidget
)
from openpype.tools.utils.widgets import AssetWidget

from openpype.modules import ModulesManager

from . import lib
from .widgets import LibrarySubsetWidget

module = sys.modules[__name__]
module.window = None


class LibraryLoaderWindow(QtWidgets.QDialog):
    """Asset library loader interface"""

    tool_title = "Library Loader 0.5"
    tool_name = "library_loader"

    def __init__(
        self, parent=None, icon=None, show_projects=False, show_libraries=True
    ):
        super(LibraryLoaderWindow, self).__init__(parent)

        self._initial_refresh = False
        self._ignore_project_change = False

        # Enable minimize and maximize for app
        self.setWindowTitle(self.tool_title)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        if icon is not None:
            self.setWindowIcon(icon)
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        body = QtWidgets.QWidget()
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(20)

        container = QtWidgets.QWidget()

        self.dbcon = AvalonMongoDB()
        self.dbcon.install()
        self.dbcon.Session["AVALON_PROJECT"] = None

        self.show_projects = show_projects
        self.show_libraries = show_libraries

        # Groups config
        self.groups_config = tools_lib.GroupsConfig(self.dbcon)
        self.family_config_cache = tools_lib.FamilyConfigCache(self.dbcon)

        assets = AssetWidget(
            self.dbcon, multiselection=True, parent=self
        )
        families = FamilyListView(
            self.dbcon, self.family_config_cache, parent=self
        )
        subsets = LibrarySubsetWidget(
            self.dbcon,
            self.groups_config,
            self.family_config_cache,
            tool_name=self.tool_name,
            parent=self
        )

        version = VersionWidget(self.dbcon)
        thumbnail = ThumbnailWidget(self.dbcon)

        # Project
        self.combo_projects = QtWidgets.QComboBox()

        # Create splitter to show / hide family filters
        asset_filter_splitter = QtWidgets.QSplitter()
        asset_filter_splitter.setOrientation(QtCore.Qt.Vertical)
        asset_filter_splitter.addWidget(self.combo_projects)
        asset_filter_splitter.addWidget(assets)
        asset_filter_splitter.addWidget(families)
        asset_filter_splitter.setStretchFactor(1, 65)
        asset_filter_splitter.setStretchFactor(2, 35)

        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]

        representations = RepresentationWidget(self.dbcon)
        thumb_ver_splitter = QtWidgets.QSplitter()
        thumb_ver_splitter.setOrientation(QtCore.Qt.Vertical)
        thumb_ver_splitter.addWidget(thumbnail)
        thumb_ver_splitter.addWidget(version)
        if sync_server.enabled:
            thumb_ver_splitter.addWidget(representations)
        thumb_ver_splitter.setStretchFactor(0, 30)
        thumb_ver_splitter.setStretchFactor(1, 35)

        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        split = QtWidgets.QSplitter()
        split.addWidget(asset_filter_splitter)
        split.addWidget(subsets)
        split.addWidget(thumb_ver_splitter)
        split.setSizes([180, 950, 200])
        container_layout.addWidget(split)

        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.addWidget(container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        message = QtWidgets.QLabel()
        message.hide()

        footer_layout = QtWidgets.QVBoxLayout(footer)
        footer_layout.addWidget(message)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(footer)

        self.data = {
            "widgets": {
                "families": families,
                "assets": assets,
                "subsets": subsets,
                "version": version,
                "thumbnail": thumbnail,
                "representations": representations
            },
            "label": {
                "message": message,
            },
            "state": {
                "assetIds": None
            }
        }

        families.active_changed.connect(subsets.set_family_filters)
        assets.selection_changed.connect(self.on_assetschanged)
        assets.refresh_triggered.connect(self.on_assetschanged)
        assets.view.clicked.connect(self.on_assetview_click)
        subsets.active_changed.connect(self.on_subsetschanged)
        subsets.version_changed.connect(self.on_versionschanged)
        subsets.refreshed.connect(self._on_subset_refresh)
        self.combo_projects.currentTextChanged.connect(self.on_project_change)

        self.sync_server = sync_server

        # Set default thumbnail on start
        thumbnail.set_thumbnail(None)

        # Defaults
        if sync_server.enabled:
            split.setSizes([250, 1000, 550])
            self.resize(1800, 900)
        else:
            split.setSizes([250, 850, 200])
            self.resize(1300, 700)

    def showEvent(self, event):
        super(LibraryLoaderWindow, self).showEvent(event)
        if not self._initial_refresh:
            self.refresh()

    def on_assetview_click(self, *args):
        subsets_widget = self.data["widgets"]["subsets"]
        selection_model = subsets_widget.view.selectionModel()
        if selection_model.selectedIndexes():
            selection_model.clearSelection()

    def _set_projects(self):
        # Store current project
        old_project_name = self.current_project

        self._ignore_project_change = True

        # Cleanup
        self.combo_projects.clear()

        # Fill combobox with projects
        select_project_item = QtGui.QStandardItem("< Select project >")
        select_project_item.setData(None, QtCore.Qt.UserRole + 1)

        combobox_items = [select_project_item]

        project_names = self.get_filtered_projects()

        for project_name in sorted(project_names):
            item = QtGui.QStandardItem(project_name)
            item.setData(project_name, QtCore.Qt.UserRole + 1)
            combobox_items.append(item)

        root_item = self.combo_projects.model().invisibleRootItem()
        root_item.appendRows(combobox_items)

        index = 0
        self._ignore_project_change = False

        if old_project_name:
            index = self.combo_projects.findText(
                old_project_name, QtCore.Qt.MatchFixedString
            )

        self.combo_projects.setCurrentIndex(index)

    def get_filtered_projects(self):
        projects = list()
        for project in self.dbcon.projects():
            is_library = project.get("data", {}).get("library_project", False)
            if (
                (is_library and self.show_libraries) or
                (not is_library and self.show_projects)
            ):
                projects.append(project["name"])

        return projects

    def on_project_change(self):
        if self._ignore_project_change:
            return

        row = self.combo_projects.currentIndex()
        index = self.combo_projects.model().index(row, 0)
        project_name = index.data(QtCore.Qt.UserRole + 1)

        self.dbcon.Session["AVALON_PROJECT"] = project_name

        _config = lib.find_config()
        if hasattr(_config, "install"):
            _config.install()
        else:
            print(
                "Config `%s` has no function `install`" % _config.__name__
            )

        subsets = self.data["widgets"]["subsets"]
        representations = self.data["widgets"]["representations"]

        subsets.on_project_change(self.dbcon.Session["AVALON_PROJECT"])
        representations.on_project_change(self.dbcon.Session["AVALON_PROJECT"])

        self.family_config_cache.refresh()
        self.groups_config.refresh()

        self._refresh_assets()
        self._assetschanged()

        project_name = self.dbcon.active_project() or "No project selected"
        title = "{} - {}".format(self.tool_title, project_name)
        self.setWindowTitle(title)

    @property
    def current_project(self):
        if (
            not self.dbcon.active_project() or
            self.dbcon.active_project() == ""
        ):
            return None

        return self.dbcon.active_project()

    # -------------------------------
    # Delay calling blocking methods
    # -------------------------------

    def refresh(self):
        self.echo("Fetching results..")
        tools_lib.schedule(self._refresh, 50, channel="mongo")

    def on_assetschanged(self, *args):
        self.echo("Fetching asset..")
        tools_lib.schedule(self._assetschanged, 50, channel="mongo")

    def on_subsetschanged(self, *args):
        self.echo("Fetching subset..")
        tools_lib.schedule(self._subsetschanged, 50, channel="mongo")

    def on_versionschanged(self, *args):
        self.echo("Fetching version..")
        tools_lib.schedule(self._versionschanged, 150, channel="mongo")

    def _on_subset_refresh(self, has_item):
        subsets_widget = self.data["widgets"]["subsets"]
        families_view = self.data["widgets"]["families"]

        subsets_widget.set_loading_state(loading=False, empty=not has_item)
        families = subsets_widget.get_subsets_families()
        families_view.set_enabled_families(families)

    def set_context(self, context, refresh=True):
        self.echo("Setting context: {}".format(context))
        lib.schedule(
            lambda: self._set_context(context, refresh=refresh),
            50, channel="mongo"
        )

    # ------------------------------
    def _refresh(self):
        if not self._initial_refresh:
            self._initial_refresh = True
        self._set_projects()

    def _refresh_assets(self):
        """Load assets from database"""
        if self.current_project is not None:
            # Ensure a project is loaded
            project_doc = self.dbcon.find_one(
                {"type": "project"},
                {"type": 1}
            )
            assert project_doc, "This is a bug"

        assets_widget = self.data["widgets"]["assets"]
        families_view = self.data["widgets"]["families"]
        families_view.set_enabled_families(set())
        families_view.refresh()

        assets_widget.model.stop_fetch_thread()
        assets_widget.refresh()
        assets_widget.setFocus()

    def clear_assets_underlines(self):
        last_asset_ids = self.data["state"]["assetIds"]
        if not last_asset_ids:
            return

        assets_widget = self.data["widgets"]["assets"]
        id_role = assets_widget.model.ObjectIdRole

        for index in tools_lib.iter_model_rows(assets_widget.model, 0):
            if index.data(id_role) not in last_asset_ids:
                continue

            assets_widget.model.setData(
                index, [], assets_widget.model.subsetColorsRole
            )

    def _assetschanged(self):
        """Selected assets have changed"""
        assets_widget = self.data["widgets"]["assets"]
        subsets_widget = self.data["widgets"]["subsets"]
        subsets_model = subsets_widget.model

        subsets_model.clear()
        self.clear_assets_underlines()

        if not self.dbcon.Session.get("AVALON_PROJECT"):
            subsets_widget.set_loading_state(
                loading=False,
                empty=True
            )
            return

        # filter None docs they are silo
        asset_docs = assets_widget.get_selected_assets()
        if len(asset_docs) == 0:
            return

        asset_ids = [asset_doc["_id"] for asset_doc in asset_docs]
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
        self.data["widgets"]["version"].set_version(None)
        self.data["widgets"]["thumbnail"].set_thumbnail(asset_docs)

        self.data["state"]["assetIds"] = asset_ids

        representations = self.data["widgets"]["representations"]
        # reset repre list
        representations.set_version_ids([])

    def _subsetschanged(self):
        asset_ids = self.data["state"]["assetIds"]
        # Skip setting colors if not asset multiselection
        if not asset_ids or len(asset_ids) < 2:
            self._versionschanged()
            return

        subsets = self.data["widgets"]["subsets"]
        selected_subsets = subsets.selected_subsets(_merged=True, _other=False)

        asset_models = {}
        asset_ids = []
        for subset_node in selected_subsets:
            asset_ids.extend(subset_node.get("assetIds", []))
        asset_ids = set(asset_ids)

        for subset_node in selected_subsets:
            for asset_id in asset_ids:
                if asset_id not in asset_models:
                    asset_models[asset_id] = []

                color = None
                if asset_id in subset_node.get("assetIds", []):
                    color = subset_node["subsetColor"]

                asset_models[asset_id].append(color)

        self.clear_assets_underlines()

        assets_widget = self.data["widgets"]["assets"]
        indexes = assets_widget.view.selectionModel().selectedRows()

        for index in indexes:
            id = index.data(assets_widget.model.ObjectIdRole)
            if id not in asset_models:
                continue

            assets_widget.model.setData(
                index, asset_models[id], assets_widget.model.subsetColorsRole
            )
        # Trigger repaint
        assets_widget.view.updateGeometries()
        # Set version in Version Widget
        self._versionschanged()

    def _versionschanged(self):

        subsets = self.data["widgets"]["subsets"]
        selection = subsets.view.selectionModel()

        # Active must be in the selected rows otherwise we
        # assume it's not actually an "active" current index.
        version_docs = None
        version_doc = None
        active = selection.currentIndex()
        rows = selection.selectedRows(column=active.column())
        if active and active in rows:
            item = active.data(subsets.model.ItemRole)
            if (
                item is not None
                and not (item.get("isGroup") or item.get("isMerged"))
            ):
                version_doc = item["version_document"]

        if rows:
            version_docs = []
            for index in rows:
                if not index or not index.isValid():
                    continue
                item = index.data(subsets.model.ItemRole)
                if (
                    item is None
                    or item.get("isGroup")
                    or item.get("isMerged")
                ):
                    continue
                version_docs.append(item["version_document"])

        self.data["widgets"]["version"].set_version(version_doc)

        thumbnail_docs = version_docs
        if not thumbnail_docs:
            assets_widget = self.data["widgets"]["assets"]
            asset_docs = assets_widget.get_selected_assets()
            if len(asset_docs) > 0:
                thumbnail_docs = asset_docs

        self.data["widgets"]["thumbnail"].set_thumbnail(thumbnail_docs)

        representations = self.data["widgets"]["representations"]
        version_ids = [doc["_id"] for doc in version_docs or []]
        representations.set_version_ids(version_ids)

    def _set_context(self, context, refresh=True):
        """Set the selection in the interface using a context.
        The context must contain `asset` data by name.
        Note: Prior to setting context ensure `refresh` is triggered so that
              the "silos" are listed correctly, aside from that setting the
              context will force a refresh further down because it changes
              the active silo and asset.
        Args:
            context (dict): The context to apply.
        Returns:
            None
        """

        asset = context.get("asset", None)
        if asset is None:
            return

        if refresh:
            # Workaround:
            # Force a direct (non-scheduled) refresh prior to setting the
            # asset widget's silo and asset selection to ensure it's correctly
            # displaying the silo tabs. Calling `window.refresh()` and directly
            # `window.set_context()` the `set_context()` seems to override the
            # scheduled refresh and the silo tabs are not shown.
            self._refresh_assets()

        asset_widget = self.data["widgets"]["assets"]
        asset_widget.select_assets(asset)

    def echo(self, message):
        widget = self.data["label"]["message"]
        widget.setText(str(message))
        widget.show()
        print(message)

        tools_lib.schedule(widget.hide, 5000, channel="message")

    def closeEvent(self, event):
        # Kill on holding SHIFT
        modifiers = QtWidgets.QApplication.queryKeyboardModifiers()
        shift_pressed = QtCore.Qt.ShiftModifier & modifiers

        if shift_pressed:
            print("Force quitted..")
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        print("Good bye")
        return super(LibraryLoaderWindow, self).closeEvent(event)


def show(
    debug=False, parent=None, icon=None,
    show_projects=False, show_libraries=True
):
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
        except RuntimeError as e:
            if not e.message.rstrip().endswith("already deleted."):
                raise

            # Garbage collected
            module.window = None

    if debug:
        import traceback
        sys.excepthook = lambda typ, val, tb: traceback.print_last()

    with tools_lib.application():
        window = LibraryLoaderWindow(
            parent, icon, show_projects, show_libraries
        )
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window


def cli(args):

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("project")

    show(show_projects=True, show_libraries=True)
