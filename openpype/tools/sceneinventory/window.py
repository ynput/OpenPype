import os
import sys
import logging
import collections
from functools import partial

from ...vendor.Qt import QtWidgets, QtCore
from ...vendor import qtawesome
from ... import io, api, style
from ...lib import HeroVersionType

from .. import lib as tools_lib
from ..delegates import VersionDelegate

from .proxy import FilterProxyModel
from .model import InventoryModel

from openpype.modules import ModulesManager

DEFAULT_COLOR = "#fb9c15"

module = sys.modules[__name__]
module.window = None

log = logging.getLogger("SceneInventory")


class View(QtWidgets.QTreeView):
    data_changed = QtCore.Signal()
    hierarchy_view = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(View, self).__init__(parent=parent)

        if not parent:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )
        # view settings
        self.setIndentation(12)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_mouse_menu)
        self._hierarchy_view = False
        self._selected = None

        manager = ModulesManager()
        self.sync_server = manager.modules_by_name["sync_server"]
        self.sync_enabled = self.sync_server.enabled

    def enter_hierarchy(self, items):
        self._selected = set(i["objectName"] for i in items)
        self._hierarchy_view = True
        self.hierarchy_view.emit(True)
        self.data_changed.emit()
        self.expandToDepth(1)
        self.setStyleSheet("""
        QTreeView {
             border-color: #fb9c15;
        }
        """)

    def leave_hierarchy(self):
        self._hierarchy_view = False
        self.hierarchy_view.emit(False)
        self.data_changed.emit()
        self.setStyleSheet("QTreeView {}")

    def build_item_menu_for_selection(self, items, menu):
        if not items:
            return

        repre_ids = []
        for item in items:
            item_id = io.ObjectId(item["representation"])
            if item_id not in repre_ids:
                repre_ids.append(item_id)

        repre_docs = io.find(
            {
                "type": "representation",
                "_id": {"$in": repre_ids}
            },
            {"parent": 1}
        )

        version_ids = []
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            if version_id not in version_ids:
                version_ids.append(version_id)

        loaded_versions = io.find({
            "_id": {"$in": version_ids},
            "type": {"$in": ["version", "hero_version"]}
        })

        loaded_hero_versions = []
        versions_by_parent_id = collections.defaultdict(list)
        version_parents = []
        for version in loaded_versions:
            if version["type"] == "hero_version":
                loaded_hero_versions.append(version)
            else:
                parent_id = version["parent"]
                versions_by_parent_id[parent_id].append(version)
                if parent_id not in version_parents:
                    version_parents.append(parent_id)

        all_versions = io.find({
            "type": {"$in": ["hero_version", "version"]},
            "parent": {"$in": version_parents}
        })
        hero_versions = []
        versions = []
        for version in all_versions:
            if version["type"] == "hero_version":
                hero_versions.append(version)
            else:
                versions.append(version)

        has_loaded_hero_versions = len(loaded_hero_versions) > 0
        has_available_hero_version = len(hero_versions) > 0
        has_outdated = False

        for version in versions:
            parent_id = version["parent"]
            current_versions = versions_by_parent_id[parent_id]
            for current_version in current_versions:
                if current_version["name"] < version["name"]:
                    has_outdated = True
                    break

            if has_outdated:
                break

        switch_to_versioned = None
        if has_loaded_hero_versions:
            def _on_switch_to_versioned(items):
                repre_ids = []
                for item in items:
                    item_id = io.ObjectId(item["representation"])
                    if item_id not in repre_ids:
                        repre_ids.append(item_id)

                repre_docs = io.find(
                    {
                        "type": "representation",
                        "_id": {"$in": repre_ids}
                    },
                    {"parent": 1}
                )

                version_ids = []
                version_id_by_repre_id = {}
                for repre_doc in repre_docs:
                    version_id = repre_doc["parent"]
                    version_id_by_repre_id[repre_doc["_id"]] = version_id
                    if version_id not in version_ids:
                        version_ids.append(version_id)
                hero_versions = io.find(
                    {
                        "_id": {"$in": version_ids},
                        "type": "hero_version"
                    },
                    {"version_id": 1}
                )
                version_ids = set()
                for hero_version in hero_versions:
                    version_id = hero_version["version_id"]
                    version_ids.add(version_id)
                    hero_version_id = hero_version["_id"]
                    for _repre_id, current_version_id in (
                        version_id_by_repre_id.items()
                    ):
                        if current_version_id == hero_version_id:
                            version_id_by_repre_id[_repre_id] = version_id

                version_docs = io.find(
                    {
                        "_id": {"$in": list(version_ids)},
                        "type": "version"
                    },
                    {"name": 1}
                )
                version_name_by_id = {}
                for version_doc in version_docs:
                    version_name_by_id[version_doc["_id"]] = \
                        version_doc["name"]

                for item in items:
                    repre_id = io.ObjectId(item["representation"])
                    version_id = version_id_by_repre_id.get(repre_id)
                    version_name = version_name_by_id.get(version_id)
                    if version_name is not None:
                        try:
                            api.update(item, version_name)
                        except AssertionError:
                            self._show_version_error_dialog(version_name,
                                                            [item])
                            log.warning("Update failed", exc_info=True)

                self.data_changed.emit()

            update_icon = qtawesome.icon(
                "fa.asterisk",
                color=DEFAULT_COLOR
            )
            switch_to_versioned = QtWidgets.QAction(
                update_icon,
                "Switch to versioned",
                menu
            )
            switch_to_versioned.triggered.connect(
                lambda: _on_switch_to_versioned(items)
            )

        update_to_latest_action = None
        if has_outdated or has_loaded_hero_versions:
            # update to latest version
            def _on_update_to_latest(items):
                for item in items:
                    try:
                        api.update(item, -1)
                    except AssertionError:
                        self._show_version_error_dialog(None, [item])
                        log.warning("Update failed", exc_info=True)
                self.data_changed.emit()

            update_icon = qtawesome.icon(
                "fa.angle-double-up",
                color=DEFAULT_COLOR
            )
            update_to_latest_action = QtWidgets.QAction(
                update_icon,
                "Update to latest",
                menu
            )
            update_to_latest_action.triggered.connect(
                lambda: _on_update_to_latest(items)
            )

        change_to_hero = None
        if has_available_hero_version:
            # change to hero version
            def _on_update_to_hero(items):
                for item in items:
                    try:
                        api.update(item, HeroVersionType(-1))
                    except AssertionError:
                        self._show_version_error_dialog('hero', [item])
                        log.warning("Update failed", exc_info=True)
                self.data_changed.emit()

            # TODO change icon
            change_icon = qtawesome.icon(
                "fa.asterisk",
                color="#00b359"
            )
            change_to_hero = QtWidgets.QAction(
                change_icon,
                "Change to hero",
                menu
            )
            change_to_hero.triggered.connect(
                lambda: _on_update_to_hero(items)
            )

        # set version
        set_version_icon = qtawesome.icon("fa.hashtag", color=DEFAULT_COLOR)
        set_version_action = QtWidgets.QAction(
            set_version_icon,
            "Set version",
            menu
        )
        set_version_action.triggered.connect(
            lambda: self.show_version_dialog(items))

        # switch asset
        switch_asset_icon = qtawesome.icon("fa.sitemap", color=DEFAULT_COLOR)
        switch_asset_action = QtWidgets.QAction(
            switch_asset_icon,
            "Switch Asset",
            menu
        )
        switch_asset_action.triggered.connect(
            lambda: self.show_switch_dialog(items))

        # remove
        remove_icon = qtawesome.icon("fa.remove", color=DEFAULT_COLOR)
        remove_action = QtWidgets.QAction(remove_icon, "Remove items", menu)
        remove_action.triggered.connect(
            lambda: self.show_remove_warning_dialog(items))

        # add the actions
        if switch_to_versioned:
            menu.addAction(switch_to_versioned)

        if update_to_latest_action:
            menu.addAction(update_to_latest_action)

        if change_to_hero:
            menu.addAction(change_to_hero)

        menu.addAction(set_version_action)
        menu.addAction(switch_asset_action)

        menu.addSeparator()

        menu.addAction(remove_action)

        menu.addSeparator()

        if self.sync_enabled:
            menu = self.handle_sync_server(menu, repre_ids)

    def handle_sync_server(self, menu, repre_ids):
        """
            Adds actions for download/upload when SyncServer is enabled

            Args:
                menu (OptionMenu)
                repre_ids (list) of object_ids
            Returns:
                (OptionMenu)
        """
        download_icon = qtawesome.icon("fa.download", color=DEFAULT_COLOR)
        download_active_action = QtWidgets.QAction(
            download_icon,
            "Download",
            menu
        )
        download_active_action.triggered.connect(
            lambda: self._add_sites(repre_ids, 'active_site'))

        upload_icon = qtawesome.icon("fa.upload", color=DEFAULT_COLOR)
        upload_remote_action = QtWidgets.QAction(
            upload_icon,
            "Upload",
            menu
        )
        upload_remote_action.triggered.connect(
            lambda: self._add_sites(repre_ids, 'remote_site'))

        menu.addAction(download_active_action)
        menu.addAction(upload_remote_action)

        return menu

    def _add_sites(self, repre_ids, side):
        """
            (Re)sync all 'repre_ids' to specific site.

            It checks if opposite site has fully available content to limit
            accidents. (ReSync active when no remote >> losing active content)

            Args:
                repre_ids (list)
                side (str): 'active_site'|'remote_site'
        """
        project = io.Session["AVALON_PROJECT"]
        active_site = self.sync_server.get_active_site(project)
        remote_site = self.sync_server.get_remote_site(project)

        for repre_id in repre_ids:
            representation = io.find_one({"type": "representation",
                                          "_id": repre_id})
            if not representation:
                continue

            progress = tools_lib.get_progress_for_repre(representation,
                                                        active_site,
                                                        remote_site)
            if side == 'active_site':
                # check opposite from added site, must be 1 or unable to sync
                check_progress = progress[remote_site]
                site = active_site
            else:
                check_progress = progress[active_site]
                site = remote_site

            if check_progress == 1:
                self.sync_server.add_site(project, repre_id, site, force=True)

        self.data_changed.emit()

    def build_item_menu(self, items):
        """Create menu for the selected items"""

        menu = QtWidgets.QMenu(self)

        # add the actions
        self.build_item_menu_for_selection(items, menu)

        # These two actions should be able to work without selection
        # expand all items
        expandall_action = QtWidgets.QAction(menu, text="Expand all items")
        expandall_action.triggered.connect(self.expandAll)

        # collapse all items
        collapse_action = QtWidgets.QAction(menu, text="Collapse all items")
        collapse_action.triggered.connect(self.collapseAll)

        menu.addAction(expandall_action)
        menu.addAction(collapse_action)

        custom_actions = self.get_custom_actions(containers=items)
        if custom_actions:
            submenu = QtWidgets.QMenu("Actions", self)
            for action in custom_actions:

                color = action.color or DEFAULT_COLOR
                icon = qtawesome.icon("fa.%s" % action.icon, color=color)
                action_item = QtWidgets.QAction(icon, action.label, submenu)
                action_item.triggered.connect(
                    partial(self.process_custom_action, action, items))

                submenu.addAction(action_item)

            menu.addMenu(submenu)

        # go back to flat view
        if self._hierarchy_view:
            back_to_flat_icon = qtawesome.icon("fa.list", color=DEFAULT_COLOR)
            back_to_flat_action = QtWidgets.QAction(
                back_to_flat_icon,
                "Back to Full-View",
                menu
            )
            back_to_flat_action.triggered.connect(self.leave_hierarchy)

        # send items to hierarchy view
        enter_hierarchy_icon = qtawesome.icon("fa.indent", color="#d8d8d8")
        enter_hierarchy_action = QtWidgets.QAction(
            enter_hierarchy_icon,
            "Cherry-Pick (Hierarchy)",
            menu
        )
        enter_hierarchy_action.triggered.connect(
            lambda: self.enter_hierarchy(items))

        if items:
            menu.addAction(enter_hierarchy_action)

        if self._hierarchy_view:
            menu.addAction(back_to_flat_action)

        return menu

    def get_custom_actions(self, containers):
        """Get the registered Inventory Actions

        Args:
            containers(list): collection of containers

        Returns:
            list: collection of filter and initialized actions
        """

        def sorter(Plugin):
            """Sort based on order attribute of the plugin"""
            return Plugin.order

        # Fedd an empty dict if no selection, this will ensure the compat
        # lookup always work, so plugin can interact with Scene Inventory
        # reversely.
        containers = containers or [dict()]

        # Check which action will be available in the menu
        Plugins = api.discover(api.InventoryAction)
        compatible = [p() for p in Plugins if
                      any(p.is_compatible(c) for c in containers)]

        return sorted(compatible, key=sorter)

    def process_custom_action(self, action, containers):
        """Run action and if results are returned positive update the view

        If the result is list or dict, will select view items by the result.

        Args:
            action (InventoryAction): Inventory Action instance
            containers (list): Data of currently selected items

        Returns:
            None
        """

        result = action.process(containers)
        if result:
            self.data_changed.emit()

            if isinstance(result, (list, set)):
                self.select_items_by_action(result)

            if isinstance(result, dict):
                self.select_items_by_action(result["objectNames"],
                                            result["options"])

    def select_items_by_action(self, object_names, options=None):
        """Select view items by the result of action

        Args:
            object_names (list or set): A list/set of container object name
            options (dict): GUI operation options.

        Returns:
            None

        """
        options = options or dict()

        if options.get("clear", True):
            self.clearSelection()

        object_names = set(object_names)
        if (self._hierarchy_view and
                not self._selected.issuperset(object_names)):
            # If any container not in current cherry-picked view, update
            # view before selecting them.
            self._selected.update(object_names)
            self.data_changed.emit()

        model = self.model()
        selection_model = self.selectionModel()

        select_mode = {
            "select": selection_model.Select,
            "deselect": selection_model.Deselect,
            "toggle": selection_model.Toggle,
        }[options.get("mode", "select")]

        for item in tools_lib.iter_model_rows(model, 0):
            item = item.data(InventoryModel.ItemRole)
            if item.get("isGroupNode"):
                continue

            name = item.get("objectName")
            if name in object_names:
                self.scrollTo(item)  # Ensure item is visible
                flags = select_mode | selection_model.Rows
                selection_model.select(item, flags)

                object_names.remove(name)

            if len(object_names) == 0:
                break

    def show_right_mouse_menu(self, pos):
        """Display the menu when at the position of the item clicked"""

        globalpos = self.viewport().mapToGlobal(pos)

        if not self.selectionModel().hasSelection():
            print("No selection")
            # Build menu without selection, feed an empty list
            menu = self.build_item_menu([])
            menu.exec_(globalpos)
            return

        active = self.currentIndex()  # index under mouse
        active = active.sibling(active.row(), 0)  # get first column

        # move index under mouse
        indices = self.get_indices()
        if active in indices:
            indices.remove(active)

        indices.append(active)

        # Extend to the sub-items
        all_indices = self.extend_to_children(indices)
        items = [dict(i.data(InventoryModel.ItemRole)) for i in all_indices
                 if i.parent().isValid()]

        if self._hierarchy_view:
            # Ensure no group item
            items = [n for n in items if not n.get("isGroupNode")]

        menu = self.build_item_menu(items)
        menu.exec_(globalpos)

    def get_indices(self):
        """Get the selected rows"""
        selection_model = self.selectionModel()
        return selection_model.selectedRows()

    def extend_to_children(self, indices):
        """Extend the indices to the children indices.

        Top-level indices are extended to its children indices. Sub-items
        are kept as is.

        Args:
            indices (list): The indices to extend.

        Returns:
            list: The children indices

        """
        def get_children(i):
            model = i.model()
            rows = model.rowCount(parent=i)
            for row in range(rows):
                child = model.index(row, 0, parent=i)
                yield child

        subitems = set()
        for i in indices:
            valid_parent = i.parent().isValid()
            if valid_parent and i not in subitems:
                subitems.add(i)

                if self._hierarchy_view:
                    # Assume this is a group item
                    for child in get_children(i):
                        subitems.add(child)
            else:
                # is top level item
                for child in get_children(i):
                    subitems.add(child)

        return list(subitems)

    def show_version_dialog(self, items):
        """Create a dialog with the available versions for the selected file

        Args:
            items (list): list of items to run the "set_version" for

        Returns:
            None
        """

        active = items[-1]

        # Get available versions for active representation
        representation_id = io.ObjectId(active["representation"])
        representation = io.find_one({"_id": representation_id})
        version = io.find_one({
            "_id": representation["parent"]
        })

        versions = list(io.find(
            {
                "parent": version["parent"],
                "type": "version"
            },
            sort=[("name", 1)]
        ))

        hero_version = io.find_one({
            "parent": version["parent"],
            "type": "hero_version"
        })
        if hero_version:
            _version_id = hero_version["version_id"]
            for _version in versions:
                if _version["_id"] != _version_id:
                    continue

                hero_version["name"] = HeroVersionType(
                    _version["name"]
                )
                hero_version["data"] = _version["data"]
                break

        # Get index among the listed versions
        current_item = None
        current_version = active["version"]
        if isinstance(current_version, HeroVersionType):
            current_item = hero_version
        else:
            for version in versions:
                if version["name"] == current_version:
                    current_item = version
                    break

        all_versions = []
        if hero_version:
            all_versions.append(hero_version)
        all_versions.extend(reversed(versions))

        if current_item:
            index = all_versions.index(current_item)
        else:
            index = 0

        versions_by_label = dict()
        labels = []
        for version in all_versions:
            is_hero = version["type"] == "hero_version"
            label = tools_lib.format_version(version["name"], is_hero)
            labels.append(label)
            versions_by_label[label] = version["name"]

        label, state = QtWidgets.QInputDialog.getItem(
            self,
            "Set version..",
            "Set version number to",
            labels,
            current=index,
            editable=False
        )
        if not state:
            return

        if label:
            version = versions_by_label[label]
            for item in items:
                try:
                    api.update(item, version)
                except AssertionError:
                    self._show_version_error_dialog(version, [item])
                    log.warning("Update failed", exc_info=True)
            # refresh model when done
            self.data_changed.emit()

    def show_switch_dialog(self, items):
        """Display Switch dialog"""
        dialog = SwitchAssetDialog(self, items)
        dialog.switched.connect(self.data_changed.emit)
        dialog.show()

    def show_remove_warning_dialog(self, items):
        """Prompt a dialog to inform the user the action will remove items"""

        accept = QtWidgets.QMessageBox.Ok
        buttons = accept | QtWidgets.QMessageBox.Cancel

        message = ("Are you sure you want to remove "
                   "{} item(s)".format(len(items)))
        state = QtWidgets.QMessageBox.question(self, "Are you sure?",
                                               message,
                                               buttons=buttons,
                                               defaultButton=accept)

        if state != accept:
            return

        for item in items:
            api.remove(item)
        self.data_changed.emit()

    def _show_version_error_dialog(self, version, items):
        """Shows QMessageBox when version switch doesn't work

            Args:
                version: str or int or None
        """
        if not version:
            version_str = "latest"
        elif version == "hero":
            version_str = "hero"
        elif isinstance(version, int):
            version_str = "v{:03d}".format(version)
        else:
            version_str = version

        dialog = QtWidgets.QMessageBox()
        dialog.setIcon(QtWidgets.QMessageBox.Warning)
        dialog.setStyleSheet(style.load_stylesheet())
        dialog.setWindowTitle("Update failed")

        switch_btn = dialog.addButton("Switch Asset",
                                      QtWidgets.QMessageBox.ActionRole)
        switch_btn.clicked.connect(lambda: self.show_switch_dialog(items))

        dialog.addButton(QtWidgets.QMessageBox.Cancel)

        msg = "Version update to '{}' ".format(version_str) + \
              "failed as representation doesn't exist.\n\n" \
              "Please update to version with a valid " \
              "representation OR \n use 'Switch Asset' button " \
              "to change asset."
        dialog.setText(msg)
        dialog.exec_()


class SearchComboBox(QtWidgets.QComboBox):
    """Searchable ComboBox with empty placeholder value as first value"""

    def __init__(self, parent=None, placeholder=""):
        super(SearchComboBox, self).__init__(parent)

        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)
        self.lineEdit().setPlaceholderText(placeholder)

        # Apply completer settings
        completer = self.completer()
        completer.setCompletionMode(completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

        # Force style sheet on popup menu
        # It won't take the parent stylesheet for some reason
        # todo: better fix for completer popup stylesheet
        if module.window:
            popup = completer.popup()
            popup.setStyleSheet(module.window.styleSheet())

    def populate(self, items):
        self.clear()
        self.addItems([""])     # ensure first item is placeholder
        self.addItems(items)

    def get_valid_value(self):
        """Return the current text if it's a valid value else None

        Note: The empty placeholder value is valid and returns as ""

        """

        text = self.currentText()
        lookup = set(self.itemText(i) for i in range(self.count()))
        if text not in lookup:
            return None

        return text or None

    def set_valid_value(self, value):
        """Try to locate 'value' and pre-select it in dropdown."""
        index = self.findText(value)
        if index > -1:
            self.setCurrentIndex(index)


class ValidationState:
    def __init__(self):
        self.asset_ok = True
        self.subset_ok = True
        self.repre_ok = True

    @property
    def all_ok(self):
        return (
            self.asset_ok
            and self.subset_ok
            and self.repre_ok
        )


class SwitchAssetDialog(QtWidgets.QDialog):
    """Widget to support asset switching"""

    MIN_WIDTH = 550

    fill_check = False
    switched = QtCore.Signal()

    def __init__(self, parent=None, items=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle("Switch selected items ...")

        # Force and keep focus dialog
        self.setModal(True)

        self._assets_box = SearchComboBox(placeholder="<asset>")
        self._subsets_box = SearchComboBox(placeholder="<subset>")
        self._representations_box = SearchComboBox(
            placeholder="<representation>"
        )

        self._asset_label = QtWidgets.QLabel("")
        self._subset_label = QtWidgets.QLabel("")
        self._repre_label = QtWidgets.QLabel("")

        self.current_asset_btn = QtWidgets.QPushButton("Use current asset")

        main_layout = QtWidgets.QGridLayout(self)

        accept_icon = qtawesome.icon("fa.check", color="white")
        accept_btn = QtWidgets.QPushButton()
        accept_btn.setIcon(accept_icon)
        accept_btn.setFixedWidth(24)
        accept_btn.setFixedHeight(24)

        # Asset column
        main_layout.addWidget(self.current_asset_btn, 0, 0)
        main_layout.addWidget(self._assets_box, 1, 0)
        main_layout.addWidget(self._asset_label, 2, 0)
        # Subset column
        main_layout.addWidget(self._subsets_box, 1, 1)
        main_layout.addWidget(self._subset_label, 2, 1)
        # Representation column
        main_layout.addWidget(self._representations_box, 1, 2)
        main_layout.addWidget(self._repre_label, 2, 2)
        # Btn column
        main_layout.addWidget(accept_btn, 1, 3)

        self._accept_btn = accept_btn

        self._assets_box.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        self._subsets_box.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        self._representations_box.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        self._accept_btn.clicked.connect(self._on_accept)
        self.current_asset_btn.clicked.connect(self._on_current_asset)

        self._init_asset_name = None
        self._init_subset_name = None
        self._init_repre_name = None

        self._items = items
        self._prepare_content_data()
        self.refresh(True)

        self.setMinimumWidth(self.MIN_WIDTH)

        # Set default focus to accept button so you don't directly type in
        # first asset field, this also allows to see the placeholder value.
        accept_btn.setFocus()

    def _prepare_content_data(self):
        repre_ids = [
            io.ObjectId(item["representation"])
            for item in self._items
        ]
        repres = list(io.find({
            "type": {"$in": ["representation", "archived_representation"]},
            "_id": {"$in": repre_ids}
        }))
        repres_by_id = {repre["_id"]: repre for repre in repres}

        # stash context values, works only for single representation
        if len(repres) == 1:
            self._init_asset_name = repres[0]["context"]["asset"]
            self._init_subset_name = repres[0]["context"]["subset"]
            self._init_repre_name = repres[0]["context"]["representation"]

        content_repres = {}
        archived_repres = []
        missing_repres = []
        version_ids = []
        for repre_id in repre_ids:
            if repre_id not in repres_by_id:
                missing_repres.append(repre_id)
            elif repres_by_id[repre_id]["type"] == "archived_representation":
                repre = repres_by_id[repre_id]
                archived_repres.append(repre)
                version_ids.append(repre["parent"])
            else:
                repre = repres_by_id[repre_id]
                content_repres[repre_id] = repres_by_id[repre_id]
                version_ids.append(repre["parent"])

        versions = io.find({
            "type": {"$in": ["version", "hero_version"]},
            "_id": {"$in": list(set(version_ids))}
        })
        content_versions = {}
        hero_version_ids = set()
        for version in versions:
            content_versions[version["_id"]] = version
            if version["type"] == "hero_version":
                hero_version_ids.add(version["_id"])

        missing_versions = []
        subset_ids = []
        for version_id in version_ids:
            if version_id not in content_versions:
                missing_versions.append(version_id)
            else:
                subset_ids.append(content_versions[version_id]["parent"])

        subsets = io.find({
            "type": {"$in": ["subset", "archived_subset"]},
            "_id": {"$in": subset_ids}
        })
        subsets_by_id = {sub["_id"]: sub for sub in subsets}

        asset_ids = []
        archived_subsets = []
        missing_subsets = []
        content_subsets = {}
        for subset_id in subset_ids:
            if subset_id not in subsets_by_id:
                missing_subsets.append(subset_id)
            elif subsets_by_id[subset_id]["type"] == "archived_subset":
                subset = subsets_by_id[subset_id]
                asset_ids.append(subset["parent"])
                archived_subsets.append(subset)
            else:
                subset = subsets_by_id[subset_id]
                asset_ids.append(subset["parent"])
                content_subsets[subset_id] = subset

        assets = io.find({
            "type": {"$in": ["asset", "archived_asset"]},
            "_id": {"$in": list(asset_ids)}
        })
        assets_by_id = {asset["_id"]: asset for asset in assets}

        missing_assets = []
        archived_assets = []
        content_assets = {}
        for asset_id in asset_ids:
            if asset_id not in assets_by_id:
                missing_assets.append(asset_id)
            elif assets_by_id[asset_id]["type"] == "archived_asset":
                archived_assets.append(assets_by_id[asset_id])
            else:
                content_assets[asset_id] = assets_by_id[asset_id]

        self.content_assets = content_assets
        self.content_subsets = content_subsets
        self.content_versions = content_versions
        self.content_repres = content_repres

        self.hero_version_ids = hero_version_ids

        self.missing_assets = missing_assets
        self.missing_versions = missing_versions
        self.missing_subsets = missing_subsets
        self.missing_repres = missing_repres
        self.missing_docs = (
            bool(missing_assets)
            or bool(missing_versions)
            or bool(missing_subsets)
            or bool(missing_repres)
        )

        self.archived_assets = archived_assets
        self.archived_subsets = archived_subsets
        self.archived_repres = archived_repres

    def _combobox_value_changed(self, *args, **kwargs):
        self.refresh()

    def refresh(self, init_refresh=False):
        """Build the need comboboxes with content"""
        if not self.fill_check and not init_refresh:
            return

        self.fill_check = False

        if init_refresh:
            asset_values = self._get_asset_box_values()
            self._fill_combobox(asset_values, "asset")

        validation_state = ValidationState()

        # Set other comboboxes to empty if any document is missing or any asset
        # of loaded representations is archived.
        self._is_asset_ok(validation_state)
        if validation_state.asset_ok:
            subset_values = self._get_subset_box_values()
            self._fill_combobox(subset_values, "subset")
            self._is_subset_ok(validation_state)

        if validation_state.asset_ok and validation_state.subset_ok:
            repre_values = sorted(self._representations_box_values())
            self._fill_combobox(repre_values, "repre")
            self._is_repre_ok(validation_state)

        # Fill comboboxes with values
        self.set_labels()
        self.apply_validations(validation_state)

        if init_refresh:  # pre select context if possible
            self._assets_box.set_valid_value(self._init_asset_name)
            self._subsets_box.set_valid_value(self._init_subset_name)
            self._representations_box.set_valid_value(self._init_repre_name)

        self.fill_check = True

    def _get_loaders(self, representations):
        if not representations:
            return list()

        available_loaders = filter(
            lambda l: not (hasattr(l, "is_utility") and l.is_utility),
            api.discover(api.Loader)
        )

        loaders = set()

        for representation in representations:
            for loader in api.loaders_from_representation(
                available_loaders,
                representation
            ):
                loaders.add(loader)

        return loaders

    def _fill_combobox(self, values, combobox_type):
        if combobox_type == "asset":
            combobox_widget = self._assets_box
        elif combobox_type == "subset":
            combobox_widget = self._subsets_box
        elif combobox_type == "repre":
            combobox_widget = self._representations_box
        else:
            return
        selected_value = combobox_widget.get_valid_value()

        # Fill combobox
        if values is not None:
            combobox_widget.populate(list(sorted(values)))
            if selected_value and selected_value in values:
                index = None
                for idx in range(combobox_widget.count()):
                    if selected_value == str(combobox_widget.itemText(idx)):
                        index = idx
                        break
                if index is not None:
                    combobox_widget.setCurrentIndex(index)

    def set_labels(self):
        asset_label = self._assets_box.get_valid_value()
        subset_label = self._subsets_box.get_valid_value()
        repre_label = self._representations_box.get_valid_value()

        default = "*No changes"
        self._asset_label.setText(asset_label or default)
        self._subset_label.setText(subset_label or default)
        self._repre_label.setText(repre_label or default)

    def apply_validations(self, validation_state):
        error_msg = "*Please select"
        error_sheet = "border: 1px solid red;"
        success_sheet = "border: 1px solid green;"

        asset_sheet = None
        subset_sheet = None
        repre_sheet = None
        accept_sheet = None
        if validation_state.asset_ok is False:
            asset_sheet = error_sheet
            self._asset_label.setText(error_msg)
        elif validation_state.subset_ok is False:
            subset_sheet = error_sheet
            self._subset_label.setText(error_msg)
        elif validation_state.repre_ok is False:
            repre_sheet = error_sheet
            self._repre_label.setText(error_msg)

        if validation_state.all_ok:
            accept_sheet = success_sheet

        self._assets_box.setStyleSheet(asset_sheet or "")
        self._subsets_box.setStyleSheet(subset_sheet or "")
        self._representations_box.setStyleSheet(repre_sheet or "")

        self._accept_btn.setEnabled(validation_state.all_ok)
        self._accept_btn.setStyleSheet(accept_sheet or "")

    def _get_asset_box_values(self):
        asset_docs = io.find(
            {"type": "asset"},
            {"_id": 1, "name": 1}
        )
        asset_names_by_id = {
            asset_doc["_id"]: asset_doc["name"]
            for asset_doc in asset_docs
        }
        subsets = io.find(
            {
                "type": "subset",
                "parent": {"$in": list(asset_names_by_id.keys())}
            },
            {
                "parent": 1
            }
        )

        filtered_assets = []
        for subset in subsets:
            asset_name = asset_names_by_id[subset["parent"]]
            if asset_name not in filtered_assets:
                filtered_assets.append(asset_name)
        return sorted(filtered_assets)

    def _get_subset_box_values(self):
        selected_asset = self._assets_box.get_valid_value()
        if selected_asset:
            asset_doc = io.find_one({"type": "asset", "name": selected_asset})
            asset_ids = [asset_doc["_id"]]
        else:
            asset_ids = list(self.content_assets.keys())

        subsets = io.find(
            {
                "type": "subset",
                "parent": {"$in": asset_ids}
            },
            {
                "parent": 1,
                "name": 1
            }
        )

        subset_names_by_parent_id = collections.defaultdict(set)
        for subset in subsets:
            subset_names_by_parent_id[subset["parent"]].add(subset["name"])

        possible_subsets = None
        for subset_names in subset_names_by_parent_id.values():
            if possible_subsets is None:
                possible_subsets = subset_names
            else:
                possible_subsets = (possible_subsets & subset_names)

            if not possible_subsets:
                break

        return list(possible_subsets or list())

    def _representations_box_values(self):
        # NOTE hero versions are not used because it is expected that
        # hero version has same representations as latests
        selected_asset = self._assets_box.currentText()
        selected_subset = self._subsets_box.currentText()

        # If nothing is selected
        # [ ] [ ] [?]
        if not selected_asset and not selected_subset:
            # Find all representations of selection's subsets
            possible_repres = list(io.find(
                {
                    "type": "representation",
                    "parent": {"$in": list(self.content_versions.keys())}
                },
                {
                    "parent": 1,
                    "name": 1
                }
            ))

            possible_repres_by_parent = collections.defaultdict(set)
            for repre in possible_repres:
                possible_repres_by_parent[repre["parent"]].add(repre["name"])

            output_repres = None
            for repre_names in possible_repres_by_parent.values():
                if output_repres is None:
                    output_repres = repre_names
                else:
                    output_repres = (output_repres & repre_names)

                if not output_repres:
                    break

            return list(output_repres or list())

        # [x] [x] [?]
        if selected_asset and selected_subset:
            asset_doc = io.find_one(
                {"type": "asset", "name": selected_asset},
                {"_id": 1}
            )
            subset_doc = io.find_one(
                {
                    "type": "subset",
                    "name": selected_subset,
                    "parent": asset_doc["_id"]
                },
                {"_id": 1}
            )
            subset_id = subset_doc["_id"]
            last_versions_by_subset_id = self.find_last_versions([subset_id])
            version_doc = last_versions_by_subset_id.get(subset_id)
            repre_docs = io.find(
                {
                    "type": "representation",
                    "parent": version_doc["_id"]
                },
                {
                    "name": 1
                }
            )
            return [
                repre_doc["name"]
                for repre_doc in repre_docs
            ]

        # [x] [ ] [?]
        # If asset only is selected
        if selected_asset:
            asset_doc = io.find_one(
                {"type": "asset", "name": selected_asset},
                {"_id": 1}
            )
            if not asset_doc:
                return list()

            # Filter subsets by subset names from content
            subset_names = set()
            for subset_doc in self.content_subsets.values():
                subset_names.add(subset_doc["name"])
            subset_docs = io.find(
                {
                    "type": "subset",
                    "parent": asset_doc["_id"],
                    "name": {"$in": list(subset_names)}
                },
                {"_id": 1}
            )
            subset_ids = [
                subset_doc["_id"]
                for subset_doc in subset_docs
            ]
            if not subset_ids:
                return list()

            last_versions_by_subset_id = self.find_last_versions(subset_ids)
            subset_id_by_version_id = {}
            for subset_id, last_version in last_versions_by_subset_id.items():
                version_id = last_version["_id"]
                subset_id_by_version_id[version_id] = subset_id

            if not subset_id_by_version_id:
                return list()

            repre_docs = list(io.find(
                {
                    "type": "representation",
                    "parent": {"$in": list(subset_id_by_version_id.keys())}
                },
                {
                    "name": 1,
                    "parent": 1
                }
            ))
            if not repre_docs:
                return list()

            repre_names_by_parent = collections.defaultdict(set)
            for repre_doc in repre_docs:
                repre_names_by_parent[repre_doc["parent"]].add(
                    repre_doc["name"]
                )

            available_repres = None
            for repre_names in repre_names_by_parent.values():
                if available_repres is None:
                    available_repres = repre_names
                    continue

                available_repres = available_repres.intersection(repre_names)

            return list(available_repres)

        # [ ] [x] [?]
        subset_docs = list(io.find(
            {
                "type": "subset",
                "parent": {"$in": list(self.content_assets.keys())},
                "name": selected_subset
            },
            {"_id": 1, "parent": 1}
        ))
        if not subset_docs:
            return list()

        subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in subset_docs
        }
        last_versions_by_subset_id = self.find_last_versions(
            subset_docs_by_id.keys()
        )

        subset_id_by_version_id = {}
        for subset_id, last_version in last_versions_by_subset_id.items():
            version_id = last_version["_id"]
            subset_id_by_version_id[version_id] = subset_id

        if not subset_id_by_version_id:
            return list()

        repre_docs = list(io.find(
            {
                "type": "representation",
                "parent": {"$in": list(subset_id_by_version_id.keys())}
            },
            {
                "name": 1,
                "parent": 1
            }
        ))
        if not repre_docs:
            return list()

        repre_names_by_asset_id = {}
        for repre_doc in repre_docs:
            subset_id = subset_id_by_version_id[repre_doc["parent"]]
            asset_id = subset_docs_by_id[subset_id]["parent"]
            if asset_id not in repre_names_by_asset_id:
                repre_names_by_asset_id[asset_id] = set()
            repre_names_by_asset_id[asset_id].add(repre_doc["name"])

        available_repres = None
        for repre_names in repre_names_by_asset_id.values():
            if available_repres is None:
                available_repres = repre_names
                continue

            available_repres = available_repres.intersection(repre_names)

        return list(available_repres)

    def _is_asset_ok(self, validation_state):
        selected_asset = self._assets_box.get_valid_value()
        if (
            selected_asset is None
            and (self.missing_docs or self.archived_assets)
        ):
            validation_state.asset_ok = False

    def _is_subset_ok(self, validation_state):
        selected_asset = self._assets_box.get_valid_value()
        selected_subset = self._subsets_box.get_valid_value()

        # [?] [x] [?]
        # If subset is selected then must be ok
        if selected_subset is not None:
            return

        # [ ] [ ] [?]
        if selected_asset is None:
            # If there were archived subsets and asset is not selected
            if self.archived_subsets:
                validation_state.subset_ok = False
            return

        # [x] [ ] [?]
        asset_doc = io.find_one(
            {"type": "asset", "name": selected_asset},
            {"_id": 1}
        )
        subset_docs = io.find(
            {"type": "subset", "parent": asset_doc["_id"]},
            {"name": 1}
        )
        subset_names = set(
            subset_doc["name"]
            for subset_doc in subset_docs
        )

        for subset_doc in self.content_subsets.values():
            if subset_doc["name"] not in subset_names:
                validation_state.subset_ok = False
                break

    def find_last_versions(self, subset_ids):
        _pipeline = [
            # Find all versions of those subsets
            {"$match": {
                "type": "version",
                "parent": {"$in": list(subset_ids)}
            }},
            # Sorting versions all together
            {"$sort": {"name": 1}},
            # Group them by "parent", but only take the last
            {"$group": {
                "_id": "$parent",
                "_version_id": {"$last": "$_id"},
                "type": {"$last": "$type"}
            }}
        ]
        last_versions_by_subset_id = dict()
        for doc in io.aggregate(_pipeline):
            doc["parent"] = doc["_id"]
            doc["_id"] = doc.pop("_version_id")
            last_versions_by_subset_id[doc["parent"]] = doc
        return last_versions_by_subset_id

    def _is_repre_ok(self, validation_state):
        selected_asset = self._assets_box.get_valid_value()
        selected_subset = self._subsets_box.get_valid_value()
        selected_repre = self._representations_box.get_valid_value()

        # [?] [?] [x]
        # If subset is selected then must be ok
        if selected_repre is not None:
            return

        # [ ] [ ] [ ]
        if selected_asset is None and selected_subset is None:
            if (
                self.archived_repres
                or self.missing_versions
                or self.missing_repres
            ):
                validation_state.repre_ok = False
            return

        # [x] [x] [ ]
        if selected_asset is not None and selected_subset is not None:
            asset_doc = io.find_one(
                {"type": "asset", "name": selected_asset},
                {"_id": 1}
            )
            subset_doc = io.find_one(
                {
                    "type": "subset",
                    "parent": asset_doc["_id"],
                    "name": selected_subset
                },
                {"_id": 1}
            )
            last_versions_by_subset_id = self.find_last_versions(
                [subset_doc["_id"]]
            )
            last_version = last_versions_by_subset_id.get(subset_doc["_id"])
            if not last_version:
                validation_state.repre_ok = False
                return

            repre_docs = io.find(
                {
                    "type": "representation",
                    "parent": last_version["_id"]
                },
                {"name": 1}
            )

            repre_names = set(
                repre_doc["name"]
                for repre_doc in repre_docs
            )
            for repre_doc in self.content_repres.values():
                if repre_doc["name"] not in repre_names:
                    validation_state.repre_ok = False
                    break
            return

        # [x] [ ] [ ]
        if selected_asset is not None:
            asset_doc = io.find_one(
                {"type": "asset", "name": selected_asset},
                {"_id": 1}
            )
            subset_docs = list(io.find(
                {
                    "type": "subset",
                    "parent": asset_doc["_id"]
                },
                {"_id": 1, "name": 1}
            ))

            subset_name_by_id = {}
            subset_ids = set()
            for subset_doc in subset_docs:
                subset_id = subset_doc["_id"]
                subset_ids.add(subset_id)
                subset_name_by_id[subset_id] = subset_doc["name"]

            last_versions_by_subset_id = self.find_last_versions(subset_ids)

            subset_id_by_version_id = {}
            for subset_id, last_version in last_versions_by_subset_id.items():
                version_id = last_version["_id"]
                subset_id_by_version_id[version_id] = subset_id

            repre_docs = io.find(
                {
                    "type": "representation",
                    "parent": {"$in": list(subset_id_by_version_id.keys())}
                },
                {
                    "name": 1,
                    "parent": 1
                }
            )
            repres_by_subset_name = {}
            for repre_doc in repre_docs:
                subset_id = subset_id_by_version_id[repre_doc["parent"]]
                subset_name = subset_name_by_id[subset_id]
                if subset_name not in repres_by_subset_name:
                    repres_by_subset_name[subset_name] = set()
                repres_by_subset_name[subset_name].add(repre_doc["name"])

            for repre_doc in self.content_repres.values():
                version_doc = self.content_versions[repre_doc["parent"]]
                subset_doc = self.content_subsets[version_doc["parent"]]
                repre_names = (
                    repres_by_subset_name.get(subset_doc["name"]) or []
                )
                if repre_doc["name"] not in repre_names:
                    validation_state.repre_ok = False
                    break
            return

        # [ ] [x] [ ]
        # Subset documents
        subset_docs = io.find(
            {
                "type": "subset",
                "parent": {"$in": list(self.content_assets.keys())},
                "name": selected_subset
            },
            {"_id": 1, "name": 1, "parent": 1}
        )

        subset_docs_by_id = {}
        for subset_doc in subset_docs:
            subset_docs_by_id[subset_doc["_id"]] = subset_doc

        last_versions_by_subset_id = self.find_last_versions(
            subset_docs_by_id.keys()
        )
        subset_id_by_version_id = {}
        for subset_id, last_version in last_versions_by_subset_id.items():
            version_id = last_version["_id"]
            subset_id_by_version_id[version_id] = subset_id

        repre_docs = io.find(
            {
                "type": "representation",
                "parent": {"$in": list(subset_id_by_version_id.keys())}
            },
            {
                "name": 1,
                "parent": 1
            }
        )
        repres_by_asset_id = {}
        for repre_doc in repre_docs:
            subset_id = subset_id_by_version_id[repre_doc["parent"]]
            asset_id = subset_docs_by_id[subset_id]["parent"]
            if asset_id not in repres_by_asset_id:
                repres_by_asset_id[asset_id] = set()
            repres_by_asset_id[asset_id].add(repre_doc["name"])

        for repre_doc in self.content_repres.values():
            version_doc = self.content_versions[repre_doc["parent"]]
            subset_doc = self.content_subsets[version_doc["parent"]]
            asset_id = subset_doc["parent"]
            repre_names = (
                repres_by_asset_id.get(asset_id) or []
            )
            if repre_doc["name"] not in repre_names:
                validation_state.repre_ok = False
                break

    def _on_current_asset(self):
        # Set initial asset as current.
        asset_name = api.Session["AVALON_ASSET"]
        index = self._assets_box.findText(
            asset_name, QtCore.Qt.MatchFixedString
        )
        if index >= 0:
            print("Setting asset to {}".format(asset_name))
            self._assets_box.setCurrentIndex(index)

    def _on_accept(self):
        # Use None when not a valid value or when placeholder value
        selected_asset = self._assets_box.get_valid_value()
        selected_subset = self._subsets_box.get_valid_value()
        selected_representation = self._representations_box.get_valid_value()

        if selected_asset:
            asset_doc = io.find_one({"type": "asset", "name": selected_asset})
            asset_docs_by_id = {asset_doc["_id"]: asset_doc}
        else:
            asset_docs_by_id = self.content_assets

        asset_docs_by_name = {
            asset_doc["name"]: asset_doc
            for asset_doc in asset_docs_by_id.values()
        }

        asset_ids = list(asset_docs_by_id.keys())

        subset_query = {
            "type": "subset",
            "parent": {"$in": asset_ids}
        }
        if selected_subset:
            subset_query["name"] = selected_subset

        subset_docs = list(io.find(subset_query))
        subset_ids = []
        subset_docs_by_parent_and_name = collections.defaultdict(dict)
        for subset in subset_docs:
            subset_ids.append(subset["_id"])
            parent_id = subset["parent"]
            name = subset["name"]
            subset_docs_by_parent_and_name[parent_id][name] = subset

        # versions
        version_docs = list(io.find({
            "type": "version",
            "parent": {"$in": subset_ids}
        }, sort=[("name", -1)]))

        hero_version_docs = list(io.find({
            "type": "hero_version",
            "parent": {"$in": subset_ids}
        }))

        version_ids = list()

        version_docs_by_parent_id = {}
        for version_doc in version_docs:
            parent_id = version_doc["parent"]
            if parent_id not in version_docs_by_parent_id:
                version_ids.append(version_doc["_id"])
                version_docs_by_parent_id[parent_id] = version_doc

        hero_version_docs_by_parent_id = {}
        for hero_version_doc in hero_version_docs:
            version_ids.append(hero_version_doc["_id"])
            parent_id = hero_version_doc["parent"]
            hero_version_docs_by_parent_id[parent_id] = hero_version_doc

        repre_docs = io.find({
            "type": "representation",
            "parent": {"$in": version_ids}
        })
        repre_docs_by_parent_id_by_name = collections.defaultdict(dict)
        for repre_doc in repre_docs:
            parent_id = repre_doc["parent"]
            name = repre_doc["name"]
            repre_docs_by_parent_id_by_name[parent_id][name] = repre_doc

        for container in self._items:
            container_repre_id = io.ObjectId(container["representation"])
            container_repre = self.content_repres[container_repre_id]
            container_repre_name = container_repre["name"]

            container_version_id = container_repre["parent"]
            container_version = self.content_versions[container_version_id]

            container_subset_id = container_version["parent"]
            container_subset = self.content_subsets[container_subset_id]
            container_subset_name = container_subset["name"]

            container_asset_id = container_subset["parent"]
            container_asset = self.content_assets[container_asset_id]
            container_asset_name = container_asset["name"]

            if selected_asset:
                asset_doc = asset_docs_by_name[selected_asset]
            else:
                asset_doc = asset_docs_by_name[container_asset_name]

            subsets_by_name = subset_docs_by_parent_and_name[asset_doc["_id"]]
            if selected_subset:
                subset_doc = subsets_by_name[selected_subset]
            else:
                subset_doc = subsets_by_name[container_subset_name]

            repre_doc = None
            subset_id = subset_doc["_id"]
            if container_version["type"] == "hero_version":
                hero_version = hero_version_docs_by_parent_id.get(
                    subset_id
                )
                if hero_version:
                    _repres = repre_docs_by_parent_id_by_name.get(
                        hero_version["_id"]
                    )
                    if selected_representation:
                        repre_doc = _repres.get(selected_representation)
                    else:
                        repre_doc = _repres.get(container_repre_name)

            if not repre_doc:
                version_doc = version_docs_by_parent_id[subset_id]
                version_id = version_doc["_id"]
                repres_by_name = repre_docs_by_parent_id_by_name[version_id]
                if selected_representation:
                    repre_doc = repres_by_name[selected_representation]
                else:
                    repre_doc = repres_by_name[container_repre_name]

            try:
                api.switch(container, repre_doc)
            except Exception:
                log.warning(
                    (
                        "Couldn't switch asset."
                        "See traceback for more information."
                    ),
                    exc_info=True
                )
                dialog = QtWidgets.QMessageBox()
                dialog.setStyleSheet(style.load_stylesheet())
                dialog.setWindowTitle("Switch asset failed")
                msg = "Switch asset failed. "\
                      "Search console log for more details"
                dialog.setText(msg)
                dialog.exec_()

        self.switched.emit()

        self.close()


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
