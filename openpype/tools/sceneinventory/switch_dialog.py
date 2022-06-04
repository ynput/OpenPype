import collections
import logging
from Qt import QtWidgets, QtCore
import qtawesome
from bson.objectid import ObjectId

from openpype.client import (
    get_asset,
    get_assets,
    get_subset,
    get_subsets,
    get_versions,
    get_hero_versions,
    get_last_versions,
    get_representations,
)
from openpype.pipeline import legacy_io
from openpype.pipeline.load import (
    discover_loader_plugins,
    switch_container,
    get_repres_contexts,
    loaders_from_repre_context,
)

from .widgets import (
    ButtonWithMenu,
    SearchComboBox
)

log = logging.getLogger("SwitchAssetDialog")


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

    switched = QtCore.Signal()

    def __init__(self, parent=None, items=None):
        super(SwitchAssetDialog, self).__init__(parent)

        self.setWindowTitle("Switch selected items ...")

        # Force and keep focus dialog
        self.setModal(True)

        assets_combox = SearchComboBox(self)
        subsets_combox = SearchComboBox(self)
        repres_combobox = SearchComboBox(self)

        assets_combox.set_placeholder("<asset>")
        subsets_combox.set_placeholder("<subset>")
        repres_combobox.set_placeholder("<representation>")

        asset_label = QtWidgets.QLabel(self)
        subset_label = QtWidgets.QLabel(self)
        repre_label = QtWidgets.QLabel(self)

        current_asset_btn = QtWidgets.QPushButton("Use current asset")

        accept_icon = qtawesome.icon("fa.check", color="white")
        accept_btn = ButtonWithMenu(self)
        accept_btn.setIcon(accept_icon)

        main_layout = QtWidgets.QGridLayout(self)
        # Asset column
        main_layout.addWidget(current_asset_btn, 0, 0)
        main_layout.addWidget(assets_combox, 1, 0)
        main_layout.addWidget(asset_label, 2, 0)
        # Subset column
        main_layout.addWidget(subsets_combox, 1, 1)
        main_layout.addWidget(subset_label, 2, 1)
        # Representation column
        main_layout.addWidget(repres_combobox, 1, 2)
        main_layout.addWidget(repre_label, 2, 2)
        # Btn column
        main_layout.addWidget(accept_btn, 1, 3)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)
        main_layout.setColumnStretch(2, 1)
        main_layout.setColumnStretch(3, 0)

        assets_combox.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        subsets_combox.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        repres_combobox.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        accept_btn.clicked.connect(self._on_accept)
        current_asset_btn.clicked.connect(self._on_current_asset)

        self._current_asset_btn = current_asset_btn

        self._assets_box = assets_combox
        self._subsets_box = subsets_combox
        self._representations_box = repres_combobox

        self._asset_label = asset_label
        self._subset_label = subset_label
        self._repre_label = repre_label

        self._accept_btn = accept_btn

        self.setMinimumWidth(self.MIN_WIDTH)

        # Set default focus to accept button so you don't directly type in
        # first asset field, this also allows to see the placeholder value.
        accept_btn.setFocus()

        self.content_loaders = set()
        self.content_assets = {}
        self.content_subsets = {}
        self.content_versions = {}
        self.content_repres = {}

        self.hero_version_ids = set()

        self.missing_assets = []
        self.missing_versions = []
        self.missing_subsets = []
        self.missing_repres = []
        self.missing_docs = False

        self.archived_assets = []
        self.archived_subsets = []
        self.archived_repres = []

        self._init_asset_name = None
        self._init_subset_name = None
        self._init_repre_name = None

        self._fill_check = False

        self._items = items
        self._prepare_content_data()
        self.refresh(True)

    def active_project(self):
        return legacy_io.active_project()

    def _prepare_content_data(self):
        repre_ids = set()
        content_loaders = set()
        for item in self._items:
            repre_ids.add(ObjectId(item["representation"]))
            content_loaders.add(item["loader"])

        project_name = self.active_project()
        repres = get_representations(
            project_name,
            representation_ids=repre_ids,
            archived=True
        )
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

        versions = get_versions(
            project_name,
            version_ids=set(version_ids),
            hero=True
        )
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

        subsets = get_subsets(
            project_name, subset_ids=subset_ids, archived=True
        )
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

        assets = get_assets(project_name, asset_ids=asset_ids, archived=True)
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

        self.content_loaders = content_loaders
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
        if not self._fill_check and not init_refresh:
            return

        self._fill_check = False

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

        self._build_loaders_menu()

        if init_refresh:  # pre select context if possible
            self._assets_box.set_valid_value(self._init_asset_name)
            self._subsets_box.set_valid_value(self._init_subset_name)
            self._representations_box.set_valid_value(self._init_repre_name)

        self._fill_check = True

    def _build_loaders_menu(self):
        repre_ids = self._get_current_output_repre_ids()
        loaders = self._get_loaders(repre_ids)
        # Get and destroy the action group
        self._accept_btn.clear_actions()

        if not loaders:
            return

        # Build new action group
        group = QtWidgets.QActionGroup(self._accept_btn)

        for loader in loaders:
            # Label
            label = getattr(loader, "label", None)
            if label is None:
                label = loader.__name__

            action = group.addAction(label)
            # action = QtWidgets.QAction(label)
            action.setData(loader)

            # Support font-awesome icons using the `.icon` and `.color`
            # attributes on plug-ins.
            icon = getattr(loader, "icon", None)
            if icon is not None:
                try:
                    key = "fa.{0}".format(icon)
                    color = getattr(loader, "color", "white")
                    action.setIcon(qtawesome.icon(key, color=color))

                except Exception as exc:
                    print("Unable to set icon for loader {}: {}".format(
                        loader, str(exc)
                    ))

            self._accept_btn.add_action(action)

        group.triggered.connect(self._on_action_clicked)

    def _on_action_clicked(self, action):
        loader_plugin = action.data()
        self._trigger_switch(loader_plugin)

    def _get_loaders(self, repre_ids):
        repre_contexts = None
        if repre_ids:
            repre_contexts = get_repres_contexts(repre_ids)

        if not repre_contexts:
            return list()

        available_loaders = []
        for loader_plugin in discover_loader_plugins():
            # Skip loaders without switch method
            if not hasattr(loader_plugin, "switch"):
                continue

            # Skip utility loaders
            if (
                hasattr(loader_plugin, "is_utility")
                and loader_plugin.is_utility
            ):
                continue
            available_loaders.append(loader_plugin)

        loaders = None
        for repre_context in repre_contexts.values():
            _loaders = set(loaders_from_repre_context(
                available_loaders, repre_context
            ))
            if loaders is None:
                loaders = _loaders
            else:
                loaders = _loaders.intersection(loaders)

            if not loaders:
                break

        if loaders is None:
            loaders = []
        else:
            loaders = list(loaders)

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

        asset_sheet = None
        subset_sheet = None
        repre_sheet = None
        accept_state = ""
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
            accept_state = "1"

        self._assets_box.setStyleSheet(asset_sheet or "")
        self._subsets_box.setStyleSheet(subset_sheet or "")
        self._representations_box.setStyleSheet(repre_sheet or "")

        self._accept_btn.setEnabled(validation_state.all_ok)
        self._set_style_property(self._accept_btn, "state", accept_state)

    def _set_style_property(self, widget, name, value):
        cur_value = widget.property(name)
        if cur_value == value:
            return
        widget.setProperty(name, value)
        widget.style().polish(widget)

    def _get_current_output_repre_ids(self):
        # NOTE hero versions are not used because it is expected that
        # hero version has same representations as latests
        selected_asset = self._assets_box.currentText()
        selected_subset = self._subsets_box.currentText()
        selected_repre = self._representations_box.currentText()

        # Nothing is selected
        # [ ] [ ] [ ]
        if not selected_asset and not selected_subset and not selected_repre:
            return list(self.content_repres.keys())

        # Prepare asset document if asset is selected
        asset_doc = None
        if selected_asset:
            asset_doc = get_asset(
                self.active_project(),
                asset_name=selected_asset,
                fields=["_id"]
            )
            if not asset_doc:
                return []

        # Everything is selected
        # [x] [x] [x]
        if selected_asset and selected_subset and selected_repre:
            return self._get_current_output_repre_ids_xxx(
                asset_doc, selected_subset, selected_repre
            )

        # [x] [x] [ ]
        # If asset and subset is selected
        if selected_asset and selected_subset:
            return self._get_current_output_repre_ids_xxo(
                asset_doc, selected_subset
            )

        # [x] [ ] [x]
        # If asset and repre is selected
        if selected_asset and selected_repre:
            return self._get_current_output_repre_ids_xox(
                asset_doc, selected_repre
            )

        # [x] [ ] [ ]
        # If asset and subset is selected
        if selected_asset:
            return self._get_current_output_repre_ids_xoo(asset_doc)

        # [ ] [x] [x]
        if selected_subset and selected_repre:
            return self._get_current_output_repre_ids_oxx(
                selected_subset, selected_repre
            )

        # [ ] [x] [ ]
        if selected_subset:
            return self._get_current_output_repre_ids_oxo(
                selected_subset
            )

        # [ ] [ ] [x]
        return self._get_current_output_repre_ids_oox(selected_repre)

    def _get_current_output_repre_ids_xxx(
        self, asset_doc, selected_subset, selected_repre
    ):
        project_name = self.active_project()
        subset_doc = get_subset(
            project_name,
            subset_name=selected_subset,
            asset_id=asset_doc["_id"],
            fields=["_id"]
        )

        subset_id = subset_doc["_id"]
        last_versions_by_subset_id = self.find_last_versions([subset_id])
        version_doc = last_versions_by_subset_id.get(subset_id)
        if not version_doc:
            return []

        repre_docs = get_representations(
            project_name,
            version_ids=[version_doc["_id"]],
            representation_names=[selected_repre],
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_xxo(self, asset_doc, selected_subset):
        project_name = self.active_project()
        subset_doc = get_subset(
            project_name,
            asset_id=asset_doc["_id"],
            subset_name=selected_subset,
            fields=["_id"]
        )
        if not subset_doc:
            return []

        repre_names = set()
        for repre_doc in self.content_repres.values():
            repre_names.add(repre_doc["name"])

        # TODO where to take version ids?
        version_ids = []
        repre_docs = get_representations(
            project_name,
            representation_names=repre_names,
            version_ids=version_ids,
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_xox(self, asset_doc, selected_repre):
        subset_names = set()
        for subset_doc in self.content_subsets.values():
            subset_names.add(subset_doc["name"])

        project_name = self.active_project()
        subset_docs = get_subsets(
            project_name,
            asset_ids=[asset_doc["_id"]],
            subset_names=subset_names,
            fields=["_id", "name"]
        )
        subset_name_by_id = {
            subset_doc["_id"]: subset_doc["name"]
            for subset_doc in subset_docs
        }
        subset_ids = list(subset_name_by_id.keys())
        last_versions_by_subset_id = self.find_last_versions(subset_ids)
        last_version_id_by_subset_name = {}
        for subset_id, last_version in last_versions_by_subset_id.items():
            subset_name = subset_name_by_id[subset_id]
            last_version_id_by_subset_name[subset_name] = (
                last_version["_id"]
            )

        repre_docs = get_representations(
            project_name,
            version_ids=last_version_id_by_subset_name.values(),
            representation_names=[selected_repre],
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_xoo(self, asset_doc):
        project_name = self.active_project()
        repres_by_subset_name = collections.defaultdict(set)
        for repre_doc in self.content_repres.values():
            repre_name = repre_doc["name"]
            version_doc = self.content_versions[repre_doc["parent"]]
            subset_doc = self.content_subsets[version_doc["parent"]]
            subset_name = subset_doc["name"]
            repres_by_subset_name[subset_name].add(repre_name)

        subset_docs = list(get_subsets(
            project_name,
            asset_ids=[asset_doc["_id"]],
            subset_names=repres_by_subset_name.keys(),
            fields=["_id", "name"]
        ))
        subset_name_by_id = {
            subset_doc["_id"]: subset_doc["name"]
            for subset_doc in subset_docs
        }
        subset_ids = list(subset_name_by_id.keys())
        last_versions_by_subset_id = self.find_last_versions(subset_ids)
        last_version_id_by_subset_name = {}
        for subset_id, last_version in last_versions_by_subset_id.items():
            subset_name = subset_name_by_id[subset_id]
            last_version_id_by_subset_name[subset_name] = (
                last_version["_id"]
            )

        repre_names_by_version_id = {}
        for subset_name, repre_names in repres_by_subset_name.items():
            version_id = last_version_id_by_subset_name.get(subset_name)
            # This should not happen but why to crash?
            if version_id is not None:
                repre_names_by_version_id[version_id] = list(repre_names)

        repre_docs = get_representations(
            project_name,
            names_by_version_ids=repre_names_by_version_id,
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_oxx(
        self, selected_subset, selected_repre
    ):
        project_name = self.active_project()
        subset_docs = get_subsets(
            project_name,
            asset_ids=self.content_assets.keys(),
            subset_names=[selected_subset],
            fields=["_id"]
        )
        subset_ids = [subset_doc["_id"] for subset_doc in subset_docs]
        last_versions_by_subset_id = self.find_last_versions(subset_ids)
        last_version_ids = [
            last_version["_id"]
            for last_version in last_versions_by_subset_id.values()
        ]
        repre_docs = get_representations(
            project_name,
            version_ids=last_version_ids,
            representation_names=[selected_repre],
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_oxo(self, selected_subset):
        project_name = self.active_project()
        subset_docs = get_subsets(
            project_name,
            asset_ids=self.content_assets.keys(),
            subset_names=[selected_subset],
            fields=["_id", "parent"]
        )
        subset_docs_by_id = {
            subset_doc["_id"]: subset_doc
            for subset_doc in subset_docs
        }
        if not subset_docs:
            return list()

        last_versions_by_subset_id = self.find_last_versions(
            subset_docs_by_id.keys()
        )

        subset_id_by_version_id = {}
        for subset_id, last_version in last_versions_by_subset_id.items():
            version_id = last_version["_id"]
            subset_id_by_version_id[version_id] = subset_id

        if not subset_id_by_version_id:
            return list()

        repre_names_by_asset_id = collections.defaultdict(set)
        for repre_doc in self.content_repres.values():
            version_doc = self.content_versions[repre_doc["parent"]]
            subset_doc = self.content_subsets[version_doc["parent"]]
            asset_doc = self.content_assets[subset_doc["parent"]]
            repre_name = repre_doc["name"]
            asset_id = asset_doc["_id"]
            repre_names_by_asset_id[asset_id].add(repre_name)

        repre_names_by_version_id = {}
        for last_version_id, subset_id in subset_id_by_version_id.items():
            subset_doc = subset_docs_by_id[subset_id]
            asset_id = subset_doc["parent"]
            repre_names = repre_names_by_asset_id.get(asset_id)
            if not repre_names:
                continue
            repre_names_by_version_id[last_version_id] = repre_names

        repre_docs = get_representations(
            project_name,
            names_by_version_ids=repre_names_by_version_id,
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_oox(self, selected_repre):
        project_name = self.active_project()
        repre_docs = get_representations(
            project_name,
            representation_names=[selected_repre],
            version_ids=self.content_versions.keys(),
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_asset_box_values(self):
        project_name = self.active_project()
        asset_docs = get_assets(project_name, fields=["_id", "name"])
        asset_names_by_id = {
            asset_doc["_id"]: asset_doc["name"]
            for asset_doc in asset_docs
        }
        subsets = get_subsets(
            project_name,
            asset_ids=asset_names_by_id.keys(),
            fields=["parent"]
        )
        filtered_assets = []
        for subset in subsets:
            asset_name = asset_names_by_id[subset["parent"]]
            if asset_name not in filtered_assets:
                filtered_assets.append(asset_name)
        return sorted(filtered_assets)

    def _get_subset_box_values(self):
        project_name = self.active_project()
        selected_asset = self._assets_box.get_valid_value()
        if selected_asset:
            asset_doc = get_asset(
                project_name, asset_name=selected_asset, fields=["_id"]
            )
            asset_ids = [asset_doc["_id"]]
        else:
            asset_ids = list(self.content_assets.keys())

        subsets = get_subsets(
            project_name,
            asset_ids=asset_ids,
            fields=["parent", "name"]
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
        project_name = self.active_project()
        selected_asset = self._assets_box.currentText()
        selected_subset = self._subsets_box.currentText()

        # If nothing is selected
        # [ ] [ ] [?]
        if not selected_asset and not selected_subset:
            # Find all representations of selection's subsets
            possible_repres = get_representations(
                project_name,
                version_ids=self.content_versions.keys(),
                fields=["parent", "name"]
            )

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
            asset_doc = get_asset(
                project_name, asset_name=selected_asset, fields=["_id"]
            )
            subset_doc = get_subset(
                project_name,
                asset_id=asset_doc["_id"],
                subset_name=selected_subset,
                fields=["_id"]
            )

            subset_id = subset_doc["_id"]
            last_versions_by_subset_id = self.find_last_versions([subset_id])
            version_doc = last_versions_by_subset_id.get(subset_id)
            repre_docs = get_representations(
                project_name,
                version_ids=[version_doc["_id"]],
                fields=["name"]
            )
            return [
                repre_doc["name"]
                for repre_doc in repre_docs
            ]

        # [x] [ ] [?]
        # If asset only is selected
        if selected_asset:
            asset_doc = get_asset(
                project_name, asset_name=selected_asset, fields=["_id"]
            )
            if not asset_doc:
                return list()

            # Filter subsets by subset names from content
            subset_names = set()
            for subset_doc in self.content_subsets.values():
                subset_names.add(subset_doc["name"])

            subset_docs = get_subsets(
                project_name,
                asset_ids=[asset_doc["_id"]],
                subset_names=subset_names,
                fields=["_id"]
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

            repre_docs = list(get_representations(
                project_name,
                version_ids=subset_id_by_version_id.keys(),
                fields=["name", "parent"]
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
        subset_docs = list(get_subsets(
            project_name,
            asset_ids=self.content_assets.keys(),
            subset_names=[selected_subset],
            fields=["_id", "parent"]
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

        repre_docs = list(
            get_representations(
                project_name,
                subset_ids=subset_id_by_version_id.keys(),
                fields=["name", "parent"]
            )
        )
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
        project_name = self.active_project()
        asset_doc = get_asset(
            project_name, asset_name=selected_asset, fields=["_id"]
        )
        subset_docs = get_subsets(
            project_name, asset_ids=[asset_doc["_id"]], fields=["name"]
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
        project_name = self.active_project()
        return get_last_versions(
            project_name,
            subset_ids=subset_ids,
            fields=["_id", "parent", "type"]
        )

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
        project_name = self.active_project()
        if selected_asset is not None and selected_subset is not None:
            asset_doc = get_asset(
                project_name, asset_name=selected_asset, fields=["_id"]
            )
            subset_doc = get_subset(
                project_name,
                asset_id=asset_doc["_id"],
                subset_name=selected_subset,
                fields=["_id"]
            )
            subset_id = subset_doc["_id"]
            last_versions_by_subset_id = self.find_last_versions([subset_id])
            last_version = last_versions_by_subset_id.get(subset_id)
            if not last_version:
                validation_state.repre_ok = False
                return

            repre_docs = get_representations(
                project_name,
                version_ids=[last_version["_id"]],
                fields=["name"]
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
            asset_doc = get_asset(
                project_name, asset_name=selected_asset, fields=["_id"]
            )
            subset_docs = list(get_subsets(
                project_name,
                asset_ids=[asset_doc["_id"]],
                fields=["_id", "name"]
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

            repre_docs = get_representations(
                project_name,
                subset_ids=subset_id_by_version_id.keys(),
                fields=["name", "parent"]
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
        subset_docs = get_subsets(
            project_name,
            asset_ids=self.content_assets.keys(),
            subset_names=[selected_subset],
            fields=["_id", "name", "parent"]
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

        repre_docs = get_representations(
            project_name,
            version_ids=subset_id_by_version_id.keys(),
            fields=["name", "parent"]
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
        asset_name = legacy_io.Session["AVALON_ASSET"]
        index = self._assets_box.findText(
            asset_name, QtCore.Qt.MatchFixedString
        )
        if index >= 0:
            print("Setting asset to {}".format(asset_name))
            self._assets_box.setCurrentIndex(index)

    def _on_accept(self):
        self._trigger_switch()

    def _trigger_switch(self, loader=None):
        # Use None when not a valid value or when placeholder value
        selected_asset = self._assets_box.get_valid_value()
        selected_subset = self._subsets_box.get_valid_value()
        selected_representation = self._representations_box.get_valid_value()

        project_name = self.active_project()
        if selected_asset:
            asset_doc = get_asset(project_name, asset_name=selected_asset)
            asset_docs_by_id = {asset_doc["_id"]: asset_doc}
        else:
            asset_docs_by_id = self.content_assets

        asset_docs_by_name = {
            asset_doc["name"]: asset_doc
            for asset_doc in asset_docs_by_id.values()
        }

        subset_names = None
        if selected_subset:
            subset_names = [selected_subset]

        subset_docs = list(get_subsets(
            project_name,
            subset_names=subset_names,
            asset_ids=asset_docs_by_id.keys()
        ))
        subset_ids = []
        subset_docs_by_parent_and_name = collections.defaultdict(dict)
        for subset in subset_docs:
            subset_ids.append(subset["_id"])
            parent_id = subset["parent"]
            name = subset["name"]
            subset_docs_by_parent_and_name[parent_id][name] = subset

        # versions
        _version_docs = get_versions(project_name, subset_ids=subset_ids)
        version_docs = list(reversed(
            sorted(_version_docs, key=lambda item: item["name"])
        ))

        hero_version_docs = list(get_hero_versions(
            project_name, subset_ids=subset_ids
        ))

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

        repre_docs = get_representations(project_name, version_ids=version_ids)
        repre_docs_by_parent_id_by_name = collections.defaultdict(dict)
        for repre_doc in repre_docs:
            parent_id = repre_doc["parent"]
            name = repre_doc["name"]
            repre_docs_by_parent_id_by_name[parent_id][name] = repre_doc

        for container in self._items:
            container_repre_id = ObjectId(container["representation"])
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
                switch_container(container, repre_doc, loader)
            except Exception:
                msg = (
                    "Couldn't switch asset."
                    "See traceback for more information."
                )
                log.warning(msg, exc_info=True)
                dialog = QtWidgets.QMessageBox(self)
                dialog.setWindowTitle("Switch asset failed")
                dialog.setText(
                    "Switch asset failed. Search console log for more details"
                )
                dialog.exec_()

        self.switched.emit()

        self.close()
