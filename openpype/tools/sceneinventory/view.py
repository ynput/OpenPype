import collections
import logging
from functools import partial

from Qt import QtWidgets, QtCore
import qtawesome
from bson.objectid import ObjectId

from openpype.client import (
    get_version_by_id,
    get_versions,
    get_hero_versions,
    get_representation_by_id,
    get_representations,
)
from openpype import style
from openpype.pipeline import (
    legacy_io,
    HeroVersionType,
    update_container,
    remove_container,
    discover_inventory_actions,
)
from openpype.modules import ModulesManager
from openpype.tools.utils.lib import (
    get_progress_for_repre,
    iter_model_rows,
    format_version
)

from .switch_dialog import SwitchAssetDialog
from .model import InventoryModel


DEFAULT_COLOR = "#fb9c15"

log = logging.getLogger("SceneInventory")


class SceneInventoryView(QtWidgets.QTreeView):
    data_changed = QtCore.Signal()
    hierarchy_view_changed = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(SceneInventoryView, self).__init__(parent=parent)

        # view settings
        self.setIndentation(12)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_right_mouse_menu)
        self._hierarchy_view = False
        self._selected = None

        manager = ModulesManager()
        self.sync_server = manager.modules_by_name["sync_server"]
        self.sync_enabled = self.sync_server.enabled

    def _set_hierarchy_view(self, enabled):
        if enabled == self._hierarchy_view:
            return
        self._hierarchy_view = enabled
        self.hierarchy_view_changed.emit(enabled)

    def _enter_hierarchy(self, items):
        self._selected = set(i["objectName"] for i in items)
        self._set_hierarchy_view(True)
        self.data_changed.emit()
        self.expandToDepth(1)
        self.setStyleSheet("""
        QTreeView {
             border-color: #fb9c15;
        }
        """)

    def _leave_hierarchy(self):
        self._set_hierarchy_view(False)
        self.data_changed.emit()
        self.setStyleSheet("QTreeView {}")

    def _build_item_menu_for_selection(self, items, menu):
        if not items:
            return

        repre_ids = []
        for item in items:
            item_id = ObjectId(item["representation"])
            if item_id not in repre_ids:
                repre_ids.append(item_id)

        project_name = legacy_io.active_project()
        repre_docs = get_representations(
            project_name, representaion_ids=repre_ids, fields=["parent"]
        )

        version_ids = []
        for repre_doc in repre_docs:
            version_id = repre_doc["parent"]
            if version_id not in version_ids:
                version_ids.append(version_id)

        loaded_versions = get_versions(
            project_name, version_ids=version_ids, hero=True
        )

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

        all_versions = get_versions(
            project_name, subset_ids=version_parents, hero=True
        )
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
                    item_id = ObjectId(item["representation"])
                    if item_id not in repre_ids:
                        repre_ids.append(item_id)

                repre_docs = get_representations(
                    project_name,
                    representation_ids=repre_ids,
                    fields=["parent"]
                )

                version_ids = []
                version_id_by_repre_id = {}
                for repre_doc in repre_docs:
                    version_id = repre_doc["parent"]
                    version_id_by_repre_id[repre_doc["_id"]] = version_id
                    if version_id not in version_ids:
                        version_ids.append(version_id)

                hero_versions = get_hero_versions(
                    project_name,
                    version_ids=version_ids,
                    fields=["version_id"]
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

                version_docs = get_versions(
                    project_name,
                    version_ids=version_ids,
                    fields=["name"]
                )
                version_name_by_id = {}
                for version_doc in version_docs:
                    version_name_by_id[version_doc["_id"]] = \
                        version_doc["name"]

                for item in items:
                    repre_id = ObjectId(item["representation"])
                    version_id = version_id_by_repre_id.get(repre_id)
                    version_name = version_name_by_id.get(version_id)
                    if version_name is not None:
                        try:
                            update_container(item, version_name)
                        except AssertionError:
                            self._show_version_error_dialog(
                                version_name, [item]
                            )
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
                        update_container(item, -1)
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
                        update_container(item, HeroVersionType(-1))
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
            lambda: self._show_version_dialog(items))

        # switch asset
        switch_asset_icon = qtawesome.icon("fa.sitemap", color=DEFAULT_COLOR)
        switch_asset_action = QtWidgets.QAction(
            switch_asset_icon,
            "Switch Asset",
            menu
        )
        switch_asset_action.triggered.connect(
            lambda: self._show_switch_dialog(items))

        # remove
        remove_icon = qtawesome.icon("fa.remove", color=DEFAULT_COLOR)
        remove_action = QtWidgets.QAction(remove_icon, "Remove items", menu)
        remove_action.triggered.connect(
            lambda: self._show_remove_warning_dialog(items))

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

        self._handle_sync_server(menu, repre_ids)

    def _handle_sync_server(self, menu, repre_ids):
        """
            Adds actions for download/upload when SyncServer is enabled

            Args:
                menu (OptionMenu)
                repre_ids (list) of object_ids
            Returns:
                (OptionMenu)
        """
        if not self.sync_enabled:
            return

        menu.addSeparator()

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

    def _add_sites(self, repre_ids, side):
        """
            (Re)sync all 'repre_ids' to specific site.

            It checks if opposite site has fully available content to limit
            accidents. (ReSync active when no remote >> losing active content)

            Args:
                repre_ids (list)
                side (str): 'active_site'|'remote_site'
        """
        project_name = legacy_io.Session["AVALON_PROJECT"]
        active_site = self.sync_server.get_active_site(project_name)
        remote_site = self.sync_server.get_remote_site(project_name)

        repre_docs = get_representations(
            project_name, representation_ids=repre_ids
        )
        repre_docs_by_id = {
            repre_doc["_id"]: repre_doc
            for repre_doc in repre_docs
        }
        for repre_id in repre_ids:
            repre_doc = repre_docs_by_id.get(repre_id)
            if not repre_doc:
                continue

            progress = get_progress_for_repre(
                repre_doc,
                active_site,
                remote_site
            )
            if side == "active_site":
                # check opposite from added site, must be 1 or unable to sync
                check_progress = progress[remote_site]
                site = active_site
            else:
                check_progress = progress[active_site]
                site = remote_site

            if check_progress == 1:
                self.sync_server.add_site(
                    project_name, repre_id, site, force=True
                )

        self.data_changed.emit()

    def _build_item_menu(self, items=None):
        """Create menu for the selected items"""

        if not items:
            items = []

        menu = QtWidgets.QMenu(self)

        # add the actions
        self._build_item_menu_for_selection(items, menu)

        # These two actions should be able to work without selection
        # expand all items
        expandall_action = QtWidgets.QAction(menu, text="Expand all items")
        expandall_action.triggered.connect(self.expandAll)

        # collapse all items
        collapse_action = QtWidgets.QAction(menu, text="Collapse all items")
        collapse_action.triggered.connect(self.collapseAll)

        menu.addAction(expandall_action)
        menu.addAction(collapse_action)

        custom_actions = self._get_custom_actions(containers=items)
        if custom_actions:
            submenu = QtWidgets.QMenu("Actions", self)
            for action in custom_actions:
                color = action.color or DEFAULT_COLOR
                icon = qtawesome.icon("fa.%s" % action.icon, color=color)
                action_item = QtWidgets.QAction(icon, action.label, submenu)
                action_item.triggered.connect(
                    partial(self._process_custom_action, action, items))

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
            back_to_flat_action.triggered.connect(self._leave_hierarchy)

        # send items to hierarchy view
        enter_hierarchy_icon = qtawesome.icon("fa.indent", color="#d8d8d8")
        enter_hierarchy_action = QtWidgets.QAction(
            enter_hierarchy_icon,
            "Cherry-Pick (Hierarchy)",
            menu
        )
        enter_hierarchy_action.triggered.connect(
            lambda: self._enter_hierarchy(items))

        if items:
            menu.addAction(enter_hierarchy_action)

        if self._hierarchy_view:
            menu.addAction(back_to_flat_action)

        return menu

    def _get_custom_actions(self, containers):
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
        Plugins = discover_inventory_actions()
        compatible = [p() for p in Plugins if
                      any(p.is_compatible(c) for c in containers)]

        return sorted(compatible, key=sorter)

    def _process_custom_action(self, action, containers):
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
                self._select_items_by_action(result)

            if isinstance(result, dict):
                self._select_items_by_action(
                    result["objectNames"], result["options"]
                )

    def _select_items_by_action(self, object_names, options=None):
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
        if (
            self._hierarchy_view
            and not self._selected.issuperset(object_names)
        ):
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

        for item in iter_model_rows(model, 0):
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

    def _show_right_mouse_menu(self, pos):
        """Display the menu when at the position of the item clicked"""

        globalpos = self.viewport().mapToGlobal(pos)

        if not self.selectionModel().hasSelection():
            print("No selection")
            # Build menu without selection, feed an empty list
            menu = self._build_item_menu()
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
        all_indices = self._extend_to_children(indices)
        items = [dict(i.data(InventoryModel.ItemRole)) for i in all_indices
                 if i.parent().isValid()]

        if self._hierarchy_view:
            # Ensure no group item
            items = [n for n in items if not n.get("isGroupNode")]

        menu = self._build_item_menu(items)
        menu.exec_(globalpos)

    def get_indices(self):
        """Get the selected rows"""
        selection_model = self.selectionModel()
        return selection_model.selectedRows()

    def _extend_to_children(self, indices):
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

    def _show_version_dialog(self, items):
        """Create a dialog with the available versions for the selected file

        Args:
            items (list): list of items to run the "set_version" for

        Returns:
            None
        """

        active = items[-1]

        project_name = legacy_io.active_project()
        # Get available versions for active representation
        repre_doc = get_representation_by_id(
            project_name,
            active["representation"],
            fields=["parent"]
        )

        repre_version_doc = get_version_by_id(
            project_name,
            repre_doc["parent"],
            fields=["parent"]
        )

        version_docs = list(get_versions(
            project_name,
            subset_ids=[repre_version_doc["parent"]],
            hero=True
        ))
        hero_version = None
        standard_versions = []
        for version_doc in version_docs:
            if version_doc["type"] == "hero_version":
                hero_version = version_doc
            else:
                standard_versions.append(version_doc)
        versions = list(reversed(
            sorted(standard_versions, key=lambda item: item["name"])
        ))
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
        all_versions.extend(versions)

        if current_item:
            index = all_versions.index(current_item)
        else:
            index = 0

        versions_by_label = dict()
        labels = []
        for version in all_versions:
            is_hero = version["type"] == "hero_version"
            label = format_version(version["name"], is_hero)
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
                    update_container(item, version)
                except AssertionError:
                    self._show_version_error_dialog(version, [item])
                    log.warning("Update failed", exc_info=True)
            # refresh model when done
            self.data_changed.emit()

    def _show_switch_dialog(self, items):
        """Display Switch dialog"""
        dialog = SwitchAssetDialog(self, items)
        dialog.switched.connect(self.data_changed.emit)
        dialog.show()

    def _show_remove_warning_dialog(self, items):
        """Prompt a dialog to inform the user the action will remove items"""

        accept = QtWidgets.QMessageBox.Ok
        buttons = accept | QtWidgets.QMessageBox.Cancel

        state = QtWidgets.QMessageBox.question(
            self,
            "Are you sure?",
            "Are you sure you want to remove {} item(s)".format(len(items)),
            buttons=buttons,
            defaultButton=accept
        )

        if state != accept:
            return

        for item in items:
            remove_container(item)
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

        switch_btn = dialog.addButton(
            "Switch Asset",
            QtWidgets.QMessageBox.ActionRole
        )
        switch_btn.clicked.connect(lambda: self._show_switch_dialog(items))

        dialog.addButton(QtWidgets.QMessageBox.Cancel)

        msg = (
            "Version update to '{}' failed as representation doesn't exist."
            "\n\nPlease update to version with a valid representation"
            " OR \n use 'Switch Asset' button to change asset."
        ).format(version_str)
        dialog.setText(msg)
        dialog.exec_()

    def update_all(self):
        """Update all items that are currently 'outdated' in the view"""
        # Get the source model through the proxy model
        model = self.model().sourceModel()

        # Get all items from outdated groups
        outdated_items = []
        for index in iter_model_rows(model,
                                     column=0,
                                     include_root=False):
            item = index.data(model.ItemRole)

            if not item.get("isGroupNode"):
                continue

            # Only the group nodes contain the "highest_version" data and as
            # such we find only the groups and take its children.
            if not model.outdated(item):
                continue

            # Collect all children which we want to update
            children = item.children()
            outdated_items.extend(children)

        if not outdated_items:
            log.info("Nothing to update.")
            return

        # Trigger update to latest
        for item in outdated_items:
            try:
                update_container(item, -1)
            except AssertionError:
                self._show_version_error_dialog(None, [item])
                log.warning("Update failed", exc_info=True)
        self.data_changed.emit()
