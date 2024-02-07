import collections
import logging

from qtpy import QtWidgets, QtCore
import qtawesome

from openpype.client import (
    get_assets,
    get_subset_by_name,
    get_subsets,
    get_versions,
    get_hero_versions,
    get_last_versions,
    get_representations,
)
from openpype.pipeline.load import (
    discover_loader_plugins,
    switch_container,
    get_repres_contexts,
    loaders_from_repre_context,
    LoaderSwitchNotImplementedError,
    IncompatibleLoaderError,
    LoaderNotFoundError
)

from .widgets import (
    ButtonWithMenu,
    SearchComboBox
)
from .folders_input import FoldersField

log = logging.getLogger("SwitchAssetDialog")


class ValidationState:
    def __init__(self):
        self.folder_ok = True
        self.product_ok = True
        self.repre_ok = True

    @property
    def all_ok(self):
        return (
            self.folder_ok
            and self.product_ok
            and self.repre_ok
        )


class SwitchAssetDialog(QtWidgets.QDialog):
    """Widget to support asset switching"""

    MIN_WIDTH = 550

    switched = QtCore.Signal()

    def __init__(self, controller, parent=None, items=None):
        super(SwitchAssetDialog, self).__init__(parent)

        self.setWindowTitle("Switch selected items ...")

        # Force and keep focus dialog
        self.setModal(True)

        folders_field = FoldersField(controller, self)
        products_combox = SearchComboBox(self)
        repres_combobox = SearchComboBox(self)

        products_combox.set_placeholder("<product>")
        repres_combobox.set_placeholder("<representation>")

        folder_label = QtWidgets.QLabel(self)
        product_label = QtWidgets.QLabel(self)
        repre_label = QtWidgets.QLabel(self)

        current_folder_btn = QtWidgets.QPushButton("Use current folder", self)

        accept_icon = qtawesome.icon("fa.check", color="white")
        accept_btn = ButtonWithMenu(self)
        accept_btn.setIcon(accept_icon)

        main_layout = QtWidgets.QGridLayout(self)
        # Folder column
        main_layout.addWidget(current_folder_btn, 0, 0)
        main_layout.addWidget(folders_field, 1, 0)
        main_layout.addWidget(folder_label, 2, 0)
        # Product column
        main_layout.addWidget(products_combox, 1, 1)
        main_layout.addWidget(product_label, 2, 1)
        # Representation column
        main_layout.addWidget(repres_combobox, 1, 2)
        main_layout.addWidget(repre_label, 2, 2)
        # Btn column
        main_layout.addWidget(accept_btn, 1, 3)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)
        main_layout.setColumnStretch(2, 1)
        main_layout.setColumnStretch(3, 0)

        show_timer = QtCore.QTimer()
        show_timer.setInterval(0)
        show_timer.setSingleShot(False)

        show_timer.timeout.connect(self._on_show_timer)
        folders_field.value_changed.connect(
            self._combobox_value_changed
        )
        products_combox.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        repres_combobox.currentIndexChanged.connect(
            self._combobox_value_changed
        )
        accept_btn.clicked.connect(self._on_accept)
        current_folder_btn.clicked.connect(self._on_current_folder)

        self._show_timer = show_timer
        self._show_counter = 0

        self._current_folder_btn = current_folder_btn

        self._folders_field = folders_field
        self._products_combox = products_combox
        self._representations_box = repres_combobox

        self._folder_label = folder_label
        self._product_label = product_label
        self._repre_label = repre_label

        self._accept_btn = accept_btn

        self.setMinimumWidth(self.MIN_WIDTH)

        # Set default focus to accept button so you don't directly type in
        # first asset field, this also allows to see the placeholder value.
        accept_btn.setFocus()

        self._folder_docs_by_id = {}
        self._product_docs_by_id = {}
        self._version_docs_by_id = {}
        self._repre_docs_by_id = {}

        self._missing_folder_ids = set()
        self._missing_product_ids = set()
        self._missing_version_ids = set()
        self._missing_repre_ids = set()
        self._missing_docs = False

        self._inactive_folder_ids = set()
        self._inactive_product_ids = set()
        self._inactive_repre_ids = set()

        self._init_folder_id = None
        self._init_product_name = None
        self._init_repre_name = None

        self._fill_check = False

        self._project_name = controller.get_current_project_name()
        self._folder_id = controller.get_current_folder_id()

        self._current_folder_btn.setEnabled(self._folder_id is not None)

        self._controller = controller

        self._items = items
        self._prepare_content_data()

    def showEvent(self, event):
        super(SwitchAssetDialog, self).showEvent(event)
        self._show_timer.start()

    def refresh(self, init_refresh=False):
        """Build the need comboboxes with content"""
        if not self._fill_check and not init_refresh:
            return

        self._fill_check = False

        validation_state = ValidationState()
        self._folders_field.refresh()
        # Set other comboboxes to empty if any document is missing or
        #   any folder of loaded representations is archived.
        self._is_folder_ok(validation_state)
        if validation_state.folder_ok:
            product_values = self._get_product_box_values()
            self._fill_combobox(product_values, "product")
            self._is_product_ok(validation_state)

        if validation_state.folder_ok and validation_state.product_ok:
            repre_values = sorted(self._representations_box_values())
            self._fill_combobox(repre_values, "repre")
            self._is_repre_ok(validation_state)

        # Fill comboboxes with values
        self.set_labels()

        self.apply_validations(validation_state)

        self._build_loaders_menu()

        if init_refresh:
            # pre select context if possible
            self._folders_field.set_selected_item(self._init_folder_id)
            self._products_combox.set_valid_value(self._init_product_name)
            self._representations_box.set_valid_value(self._init_repre_name)

        self._fill_check = True

    def set_labels(self):
        folder_label = self._folders_field.get_selected_folder_label()
        product_label = self._products_combox.get_valid_value()
        repre_label = self._representations_box.get_valid_value()

        default = "*No changes"
        self._folder_label.setText(folder_label or default)
        self._product_label.setText(product_label or default)
        self._repre_label.setText(repre_label or default)

    def apply_validations(self, validation_state):
        error_msg = "*Please select"
        error_sheet = "border: 1px solid red;"

        product_sheet = None
        repre_sheet = None
        accept_state = ""
        if validation_state.folder_ok is False:
            self._folder_label.setText(error_msg)
        elif validation_state.product_ok is False:
            product_sheet = error_sheet
            self._product_label.setText(error_msg)
        elif validation_state.repre_ok is False:
            repre_sheet = error_sheet
            self._repre_label.setText(error_msg)

        if validation_state.all_ok:
            accept_state = "1"

        self._folders_field.set_valid(validation_state.folder_ok)
        self._products_combox.setStyleSheet(product_sheet or "")
        self._representations_box.setStyleSheet(repre_sheet or "")

        self._accept_btn.setEnabled(validation_state.all_ok)
        self._set_style_property(self._accept_btn, "state", accept_state)

    def find_last_versions(self, product_ids):
        project_name = self._project_name
        return get_last_versions(
            project_name,
            subset_ids=product_ids,
            fields=["_id", "parent", "type"]
        )

    def _on_show_timer(self):
        if self._show_counter == 2:
            self._show_timer.stop()
            self.refresh(True)
        else:
            self._show_counter += 1

    def _prepare_content_data(self):
        repre_ids = {
            item["representation"]
            for item in self._items
        }

        project_name = self._project_name
        repres = list(get_representations(
            project_name,
            representation_ids=repre_ids,
            archived=True,
        ))
        repres_by_id = {str(repre["_id"]): repre for repre in repres}

        content_repre_docs_by_id = {}
        inactive_repre_ids = set()
        missing_repre_ids = set()
        version_ids = set()
        for repre_id in repre_ids:
            repre_doc = repres_by_id.get(repre_id)
            if repre_doc is None:
                missing_repre_ids.add(repre_id)
            elif repres_by_id[repre_id]["type"] == "archived_representation":
                inactive_repre_ids.add(repre_id)
                version_ids.add(repre_doc["parent"])
            else:
                content_repre_docs_by_id[repre_id] = repre_doc
                version_ids.add(repre_doc["parent"])

        version_docs = get_versions(
            project_name,
            version_ids=version_ids,
            hero=True
        )
        content_version_docs_by_id = {}
        for version_doc in version_docs:
            version_id = version_doc["_id"]
            content_version_docs_by_id[version_id] = version_doc

        missing_version_ids = set()
        product_ids = set()
        for version_id in version_ids:
            version_doc = content_version_docs_by_id.get(version_id)
            if version_doc is None:
                missing_version_ids.add(version_id)
            else:
                product_ids.add(version_doc["parent"])

        product_docs = get_subsets(
            project_name, subset_ids=product_ids, archived=True
        )
        product_docs_by_id = {sub["_id"]: sub for sub in product_docs}

        folder_ids = set()
        inactive_product_ids = set()
        missing_product_ids = set()
        content_product_docs_by_id = {}
        for product_id in product_ids:
            product_doc = product_docs_by_id.get(product_id)
            if product_doc is None:
                missing_product_ids.add(product_id)
            elif product_doc["type"] == "archived_subset":
                folder_ids.add(product_doc["parent"])
                inactive_product_ids.add(product_id)
            else:
                folder_ids.add(product_doc["parent"])
                content_product_docs_by_id[product_id] = product_doc

        folder_docs = get_assets(
            project_name, asset_ids=folder_ids, archived=True
        )
        folder_docs_by_id = {
            folder_doc["_id"]: folder_doc
            for folder_doc in folder_docs
        }

        missing_folder_ids = set()
        inactive_folder_ids = set()
        content_folder_docs_by_id = {}
        for folder_id in folder_ids:
            folder_doc = folder_docs_by_id.get(folder_id)
            if folder_doc is None:
                missing_folder_ids.add(folder_id)
            elif folder_doc["type"] == "archived_asset":
                inactive_folder_ids.add(folder_id)
            else:
                content_folder_docs_by_id[folder_id] = folder_doc

        # stash context values, works only for single representation
        init_folder_id = None
        init_product_name = None
        init_repre_name = None
        if len(repres) == 1:
            init_repre_doc = repres[0]
            init_version_doc = content_version_docs_by_id.get(
                init_repre_doc["parent"])
            init_product_doc = None
            init_folder_doc = None
            if init_version_doc:
                init_product_doc = content_product_docs_by_id.get(
                    init_version_doc["parent"]
                )
            if init_product_doc:
                init_folder_doc = content_folder_docs_by_id.get(
                    init_product_doc["parent"]
                )
            if init_folder_doc:
                init_repre_name = init_repre_doc["name"]
                init_product_name = init_product_doc["name"]
                init_folder_id = init_folder_doc["_id"]

        self._init_folder_id = init_folder_id
        self._init_product_name = init_product_name
        self._init_repre_name = init_repre_name

        self._folder_docs_by_id = content_folder_docs_by_id
        self._product_docs_by_id = content_product_docs_by_id
        self._version_docs_by_id = content_version_docs_by_id
        self._repre_docs_by_id = content_repre_docs_by_id

        self._missing_folder_ids = missing_folder_ids
        self._missing_product_ids = missing_product_ids
        self._missing_version_ids = missing_version_ids
        self._missing_repre_ids = missing_repre_ids
        self._missing_docs = (
            bool(missing_folder_ids)
            or bool(missing_version_ids)
            or bool(missing_product_ids)
            or bool(missing_repre_ids)
        )

        self._inactive_folder_ids = inactive_folder_ids
        self._inactive_product_ids = inactive_product_ids
        self._inactive_repre_ids = inactive_repre_ids

    def _combobox_value_changed(self, *args, **kwargs):
        self.refresh()

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
        if combobox_type == "product":
            combobox_widget = self._products_combox
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

    def _set_style_property(self, widget, name, value):
        cur_value = widget.property(name)
        if cur_value == value:
            return
        widget.setProperty(name, value)
        widget.style().polish(widget)

    def _get_current_output_repre_ids(self):
        # NOTE hero versions are not used because it is expected that
        # hero version has same representations as latests
        selected_folder_id = self._folders_field.get_selected_folder_id()
        selected_product_name = self._products_combox.currentText()
        selected_repre = self._representations_box.currentText()

        # Nothing is selected
        # [ ] [ ] [ ]
        if (
            not selected_folder_id
            and not selected_product_name
            and not selected_repre
        ):
            return list(self._repre_docs_by_id.keys())

        # Everything is selected
        # [x] [x] [x]
        if selected_folder_id and selected_product_name and selected_repre:
            return self._get_current_output_repre_ids_xxx(
                selected_folder_id, selected_product_name, selected_repre
            )

        # [x] [x] [ ]
        # If folder and product is selected
        if selected_folder_id and selected_product_name:
            return self._get_current_output_repre_ids_xxo(
                selected_folder_id, selected_product_name
            )

        # [x] [ ] [x]
        # If folder and repre is selected
        if selected_folder_id and selected_repre:
            return self._get_current_output_repre_ids_xox(
                selected_folder_id, selected_repre
            )

        # [x] [ ] [ ]
        # If folder and product is selected
        if selected_folder_id:
            return self._get_current_output_repre_ids_xoo(selected_folder_id)

        # [ ] [x] [x]
        if selected_product_name and selected_repre:
            return self._get_current_output_repre_ids_oxx(
                selected_product_name, selected_repre
            )

        # [ ] [x] [ ]
        if selected_product_name:
            return self._get_current_output_repre_ids_oxo(
                selected_product_name
            )

        # [ ] [ ] [x]
        return self._get_current_output_repre_ids_oox(selected_repre)

    def _get_current_output_repre_ids_xxx(
        self, folder_id, selected_product_name, selected_repre
    ):
        project_name = self._project_name
        product_doc = get_subset_by_name(
            project_name,
            selected_product_name,
            folder_id,
            fields=["_id"]
        )

        product_id = product_doc["_id"]
        last_versions_by_product_id = self.find_last_versions([product_id])
        version_doc = last_versions_by_product_id.get(product_id)
        if not version_doc:
            return []

        repre_docs = get_representations(
            project_name,
            version_ids=[version_doc["_id"]],
            representation_names=[selected_repre],
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_xxo(self, folder_id, product_name):
        project_name = self._project_name
        product_doc = get_subset_by_name(
            project_name,
            product_name,
            folder_id,
            fields=["_id"]
        )
        if not product_doc:
            return []

        repre_names = set()
        for repre_doc in self._repre_docs_by_id.values():
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

    def _get_current_output_repre_ids_xox(self, folder_id, selected_repre):
        product_names = {
            product_doc["name"]
            for product_doc in self._product_docs_by_id.values()
        }

        project_name = self._project_name
        product_docs = get_subsets(
            project_name,
            asset_ids=[folder_id],
            subset_names=product_names,
            fields=["_id", "name"]
        )
        product_name_by_id = {
            product_doc["_id"]: product_doc["name"]
            for product_doc in product_docs
        }
        product_ids = list(product_name_by_id.keys())
        last_versions_by_product_id = self.find_last_versions(product_ids)
        last_version_id_by_product_name = {}
        for product_id, last_version in last_versions_by_product_id.items():
            product_name = product_name_by_id[product_id]
            last_version_id_by_product_name[product_name] = (
                last_version["_id"]
            )

        repre_docs = get_representations(
            project_name,
            version_ids=last_version_id_by_product_name.values(),
            representation_names=[selected_repre],
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_xoo(self, folder_id):
        project_name = self._project_name
        repres_by_product_name = collections.defaultdict(set)
        for repre_doc in self._repre_docs_by_id.values():
            version_doc = self._version_docs_by_id[repre_doc["parent"]]
            product_doc = self._product_docs_by_id[version_doc["parent"]]
            product_name = product_doc["name"]
            repres_by_product_name[product_name].add(repre_doc["name"])

        product_docs = list(get_subsets(
            project_name,
            asset_ids=[folder_id],
            subset_names=repres_by_product_name.keys(),
            fields=["_id", "name"]
        ))
        product_name_by_id = {
            product_doc["_id"]: product_doc["name"]
            for product_doc in product_docs
        }
        product_ids = list(product_name_by_id.keys())
        last_versions_by_product_id = self.find_last_versions(product_ids)
        last_version_id_by_product_name = {}
        for product_id, last_version in last_versions_by_product_id.items():
            product_name = product_name_by_id[product_id]
            last_version_id_by_product_name[product_name] = (
                last_version["_id"]
            )

        repre_names_by_version_id = {}
        for product_name, repre_names in repres_by_product_name.items():
            version_id = last_version_id_by_product_name.get(product_name)
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
        self, product_name, selected_repre
    ):
        project_name = self._project_name
        product_docs = get_subsets(
            project_name,
            asset_ids=self._folder_docs_by_id.keys(),
            subset_names=[product_name],
            fields=["_id"]
        )
        product_ids = [product_doc["_id"] for product_doc in product_docs]
        last_versions_by_product_id = self.find_last_versions(product_ids)
        last_version_ids = [
            last_version["_id"]
            for last_version in last_versions_by_product_id.values()
        ]
        repre_docs = get_representations(
            project_name,
            version_ids=last_version_ids,
            representation_names=[selected_repre],
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_current_output_repre_ids_oxo(self, product_name):
        project_name = self._project_name
        product_docs = get_subsets(
            project_name,
            asset_ids=self._folder_docs_by_id.keys(),
            subset_names=[product_name],
            fields=["_id", "parent"]
        )
        product_docs_by_id = {
            product_doc["_id"]: product_doc
            for product_doc in product_docs
        }
        if not product_docs:
            return list()

        last_versions_by_product_id = self.find_last_versions(
            product_docs_by_id.keys()
        )

        product_id_by_version_id = {}
        for product_id, last_version in last_versions_by_product_id.items():
            version_id = last_version["_id"]
            product_id_by_version_id[version_id] = product_id

        if not product_id_by_version_id:
            return list()

        repre_names_by_folder_id = collections.defaultdict(set)
        for repre_doc in self._repre_docs_by_id.values():
            version_doc = self._version_docs_by_id[repre_doc["parent"]]
            product_doc = self._product_docs_by_id[version_doc["parent"]]
            folder_doc = self._folder_docs_by_id[product_doc["parent"]]
            folder_id = folder_doc["_id"]
            repre_names_by_folder_id[folder_id].add(repre_doc["name"])

        repre_names_by_version_id = {}
        for last_version_id, product_id in product_id_by_version_id.items():
            product_doc = product_docs_by_id[product_id]
            folder_id = product_doc["parent"]
            repre_names = repre_names_by_folder_id.get(folder_id)
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
        project_name = self._project_name
        repre_docs = get_representations(
            project_name,
            representation_names=[selected_repre],
            version_ids=self._version_docs_by_id.keys(),
            fields=["_id"]
        )
        return [repre_doc["_id"] for repre_doc in repre_docs]

    def _get_product_box_values(self):
        project_name = self._project_name
        selected_folder_id = self._folders_field.get_selected_folder_id()
        if selected_folder_id:
            folder_ids = [selected_folder_id]
        else:
            folder_ids = list(self._folder_docs_by_id.keys())

        product_docs = get_subsets(
            project_name,
            asset_ids=folder_ids,
            fields=["parent", "name"]
        )

        product_names_by_parent_id = collections.defaultdict(set)
        for product_doc in product_docs:
            product_names_by_parent_id[product_doc["parent"]].add(
                product_doc["name"]
            )

        possible_product_names = None
        for product_names in product_names_by_parent_id.values():
            if possible_product_names is None:
                possible_product_names = product_names
            else:
                possible_product_names = possible_product_names.intersection(
                    product_names)

            if not possible_product_names:
                break

        if not possible_product_names:
            return []
        return list(possible_product_names)

    def _representations_box_values(self):
        # NOTE hero versions are not used because it is expected that
        # hero version has same representations as latests
        project_name = self._project_name
        selected_folder_id = self._folders_field.get_selected_folder_id()
        selected_product_name = self._products_combox.currentText()

        # If nothing is selected
        # [ ] [ ] [?]
        if not selected_folder_id and not selected_product_name:
            # Find all representations of selection's products
            possible_repres = get_representations(
                project_name,
                version_ids=self._version_docs_by_id.keys(),
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
        if selected_folder_id and selected_product_name:
            product_doc = get_subset_by_name(
                project_name,
                selected_product_name,
                selected_folder_id,
                fields=["_id"]
            )

            product_id = product_doc["_id"]
            last_versions_by_product_id = self.find_last_versions([product_id])
            version_doc = last_versions_by_product_id.get(product_id)
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
        # If only folder is selected
        if selected_folder_id:
            # Filter products by names from content
            product_names = {
                product_doc["name"]
                for product_doc in self._product_docs_by_id.values()
            }

            product_docs = get_subsets(
                project_name,
                asset_ids=[selected_folder_id],
                subset_names=product_names,
                fields=["_id"]
            )
            product_ids = {
                product_doc["_id"]
                for product_doc in product_docs
            }
            if not product_ids:
                return list()

            last_versions_by_product_id = self.find_last_versions(product_ids)
            product_id_by_version_id = {}
            for product_id, last_version in (
                last_versions_by_product_id.items()
            ):
                version_id = last_version["_id"]
                product_id_by_version_id[version_id] = product_id

            if not product_id_by_version_id:
                return list()

            repre_docs = list(get_representations(
                project_name,
                version_ids=product_id_by_version_id.keys(),
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
        product_docs = list(get_subsets(
            project_name,
            asset_ids=self._folder_docs_by_id.keys(),
            subset_names=[selected_product_name],
            fields=["_id", "parent"]
        ))
        if not product_docs:
            return list()

        product_docs_by_id = {
            product_doc["_id"]: product_doc
            for product_doc in product_docs
        }
        last_versions_by_product_id = self.find_last_versions(
            product_docs_by_id.keys()
        )

        product_id_by_version_id = {}
        for product_id, last_version in last_versions_by_product_id.items():
            version_id = last_version["_id"]
            product_id_by_version_id[version_id] = product_id

        if not product_id_by_version_id:
            return list()

        repre_docs = list(
            get_representations(
                project_name,
                version_ids=product_id_by_version_id.keys(),
                fields=["name", "parent"]
            )
        )
        if not repre_docs:
            return list()

        repre_names_by_folder_id = collections.defaultdict(set)
        for repre_doc in repre_docs:
            product_id = product_id_by_version_id[repre_doc["parent"]]
            folder_id = product_docs_by_id[product_id]["parent"]
            repre_names_by_folder_id[folder_id].add(repre_doc["name"])

        available_repres = None
        for repre_names in repre_names_by_folder_id.values():
            if available_repres is None:
                available_repres = repre_names
                continue

            available_repres = available_repres.intersection(repre_names)

        return list(available_repres)

    def _is_folder_ok(self, validation_state):
        selected_folder_id = self._folders_field.get_selected_folder_id()
        if (
            selected_folder_id is None
            and (self._missing_docs or self._inactive_folder_ids)
        ):
            validation_state.folder_ok = False

    def _is_product_ok(self, validation_state):
        selected_folder_id = self._folders_field.get_selected_folder_id()
        selected_product_name = self._products_combox.get_valid_value()

        # [?] [x] [?]
        # If product is selected then must be ok
        if selected_product_name is not None:
            return

        # [ ] [ ] [?]
        if selected_folder_id is None:
            # If there were archived products and folder is not selected
            if self._inactive_product_ids:
                validation_state.product_ok = False
            return

        # [x] [ ] [?]
        project_name = self._project_name
        product_docs = get_subsets(
            project_name, asset_ids=[selected_folder_id], fields=["name"]
        )

        product_names = set(
            product_doc["name"]
            for product_doc in product_docs
        )

        for product_doc in self._product_docs_by_id.values():
            if product_doc["name"] not in product_names:
                validation_state.product_ok = False
                break

    def _is_repre_ok(self, validation_state):
        selected_folder_id = self._folders_field.get_selected_folder_id()
        selected_product_name = self._products_combox.get_valid_value()
        selected_repre = self._representations_box.get_valid_value()

        # [?] [?] [x]
        # If product is selected then must be ok
        if selected_repre is not None:
            return

        # [ ] [ ] [ ]
        if selected_folder_id is None and selected_product_name is None:
            if (
                self._inactive_repre_ids
                or self._missing_version_ids
                or self._missing_repre_ids
            ):
                validation_state.repre_ok = False
            return

        # [x] [x] [ ]
        project_name = self._project_name
        if (
            selected_folder_id is not None
            and selected_product_name is not None
        ):
            product_doc = get_subset_by_name(
                project_name,
                selected_product_name,
                selected_folder_id,
                fields=["_id"]
            )
            product_id = product_doc["_id"]
            last_versions_by_product_id = self.find_last_versions([product_id])
            last_version = last_versions_by_product_id.get(product_id)
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
            for repre_doc in self._repre_docs_by_id.values():
                if repre_doc["name"] not in repre_names:
                    validation_state.repre_ok = False
                    break
            return

        # [x] [ ] [ ]
        if selected_folder_id is not None:
            product_docs = list(get_subsets(
                project_name,
                asset_ids=[selected_folder_id],
                fields=["_id", "name"]
            ))

            product_name_by_id = {}
            product_ids = set()
            for product_doc in product_docs:
                product_id = product_doc["_id"]
                product_ids.add(product_id)
                product_name_by_id[product_id] = product_doc["name"]

            last_versions_by_product_id = self.find_last_versions(product_ids)

            product_id_by_version_id = {}
            for product_id, last_version in (
                last_versions_by_product_id.items()
            ):
                version_id = last_version["_id"]
                product_id_by_version_id[version_id] = product_id

            repre_docs = get_representations(
                project_name,
                version_ids=product_id_by_version_id.keys(),
                fields=["name", "parent"]
            )
            repres_by_product_name = collections.defaultdict(set)
            for repre_doc in repre_docs:
                product_id = product_id_by_version_id[repre_doc["parent"]]
                product_name = product_name_by_id[product_id]
                repres_by_product_name[product_name].add(repre_doc["name"])

            for repre_doc in self._repre_docs_by_id.values():
                version_doc = self._version_docs_by_id[repre_doc["parent"]]
                product_doc = self._product_docs_by_id[version_doc["parent"]]
                repre_names = repres_by_product_name[product_doc["name"]]
                if repre_doc["name"] not in repre_names:
                    validation_state.repre_ok = False
                    break
            return

        # [ ] [x] [ ]
        # Product documents
        product_docs = get_subsets(
            project_name,
            asset_ids=self._folder_docs_by_id.keys(),
            subset_names=[selected_product_name],
            fields=["_id", "name", "parent"]
        )
        product_docs_by_id = {}
        for product_doc in product_docs:
            product_docs_by_id[product_doc["_id"]] = product_doc

        last_versions_by_product_id = self.find_last_versions(
            product_docs_by_id.keys()
        )
        product_id_by_version_id = {}
        for product_id, last_version in last_versions_by_product_id.items():
            version_id = last_version["_id"]
            product_id_by_version_id[version_id] = product_id

        repre_docs = get_representations(
            project_name,
            version_ids=product_id_by_version_id.keys(),
            fields=["name", "parent"]
        )
        repres_by_folder_id = collections.defaultdict(set)
        for repre_doc in repre_docs:
            product_id = product_id_by_version_id[repre_doc["parent"]]
            folder_id = product_docs_by_id[product_id]["parent"]
            repres_by_folder_id[folder_id].add(repre_doc["name"])

        for repre_doc in self._repre_docs_by_id.values():
            version_doc = self._version_docs_by_id[repre_doc["parent"]]
            product_doc = self._product_docs_by_id[version_doc["parent"]]
            folder_id = product_doc["parent"]
            repre_names = repres_by_folder_id[folder_id]
            if repre_doc["name"] not in repre_names:
                validation_state.repre_ok = False
                break

    def _on_current_folder(self):
        # Set initial folder as current.
        folder_id = self._controller.get_current_folder_id()
        if not folder_id:
            return

        selected_folder_id = self._folders_field.get_selected_folder_id()
        if folder_id == selected_folder_id:
            return

        self._folders_field.set_selected_item(folder_id)
        self._combobox_value_changed()

    def _on_accept(self):
        self._trigger_switch()

    def _trigger_switch(self, loader=None):
        # Use None when not a valid value or when placeholder value
        selected_folder_id = self._folders_field.get_selected_folder_id()
        selected_product_name = self._products_combox.get_valid_value()
        selected_representation = self._representations_box.get_valid_value()

        project_name = self._project_name
        if selected_folder_id:
            folder_ids = {selected_folder_id}
        else:
            folder_ids = set(self._folder_docs_by_id.keys())

        product_names = None
        if selected_product_name:
            product_names = [selected_product_name]

        product_docs = list(get_subsets(
            project_name,
            subset_names=product_names,
            asset_ids=folder_ids
        ))
        product_ids = set()
        product_docs_by_parent_and_name = collections.defaultdict(dict)
        for product_doc in product_docs:
            product_ids.add(product_doc["_id"])
            folder_id = product_doc["parent"]
            name = product_doc["name"]
            product_docs_by_parent_and_name[folder_id][name] = product_doc

        # versions
        _version_docs = get_versions(project_name, subset_ids=product_ids)
        version_docs = list(reversed(
            sorted(_version_docs, key=lambda item: item["name"])
        ))

        hero_version_docs = list(get_hero_versions(
            project_name, subset_ids=product_ids
        ))

        version_ids = set()
        version_docs_by_parent_id_and_name = collections.defaultdict(dict)
        for version_doc in version_docs:
            version_ids.add(version_doc["_id"])
            product_id = version_doc["parent"]
            name = version_doc["name"]
            version_docs_by_parent_id_and_name[product_id][name] = version_doc

        hero_version_docs_by_parent_id = {}
        for hero_version_doc in hero_version_docs:
            version_ids.add(hero_version_doc["_id"])
            parent_id = hero_version_doc["parent"]
            hero_version_docs_by_parent_id[parent_id] = hero_version_doc

        repre_docs = get_representations(
            project_name, version_ids=version_ids
        )
        repre_docs_by_parent_id_by_name = collections.defaultdict(dict)
        for repre_doc in repre_docs:
            parent_id = repre_doc["parent"]
            name = repre_doc["name"]
            repre_docs_by_parent_id_by_name[parent_id][name] = repre_doc

        for container in self._items:
            self._switch_container(
                container,
                loader,
                selected_folder_id,
                selected_product_name,
                selected_representation,
                product_docs_by_parent_and_name,
                version_docs_by_parent_id_and_name,
                hero_version_docs_by_parent_id,
                repre_docs_by_parent_id_by_name,
            )

        self.switched.emit()

        self.close()

    def _switch_container(
        self,
        container,
        loader,
        selected_folder_id,
        selected_product_name,
        selected_representation,
        product_docs_by_parent_and_name,
        version_docs_by_parent_id_and_name,
        hero_version_docs_by_parent_id,
        repre_docs_by_parent_id_by_name,
    ):
        container_repre_id = container["representation"]
        container_repre = self._repre_docs_by_id[container_repre_id]
        container_repre_name = container_repre["name"]
        container_version_id = container_repre["parent"]

        container_version = self._version_docs_by_id[container_version_id]

        container_product_id = container_version["parent"]
        container_product = self._product_docs_by_id[container_product_id]
        container_product_name = container_product["name"]

        container_folder_id = container_product["parent"]

        if selected_folder_id:
            folder_id = selected_folder_id
        else:
            folder_id = container_folder_id

        products_by_name = product_docs_by_parent_and_name[folder_id]
        if selected_product_name:
            product_doc = products_by_name[selected_product_name]
        else:
            product_doc = products_by_name[container_product["name"]]

        repre_doc = None
        product_id = product_doc["_id"]
        if container_version["type"] == "hero_version":
            hero_version = hero_version_docs_by_parent_id.get(
                product_id
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
            version_docs_by_name = (
                version_docs_by_parent_id_and_name[product_id]
            )
            # If asset or subset are selected for switching, we use latest
            # version else we try to keep the current container version.
            version_name = None
            if (
                selected_folder_id in (None, container_folder_id)
                and selected_product_name in (None, container_product_name)
            ):
                version_name = container_version.get("name")

            version_doc = None
            if version_name is not None:
                version_doc = version_docs_by_name.get(version_name)

            if version_doc is None:
                version_name = max(version_docs_by_name)
                version_doc = version_docs_by_name[version_name]

            version_id = version_doc["_id"]
            repres_by_name = repre_docs_by_parent_id_by_name[version_id]
            if selected_representation:
                repre_doc = repres_by_name[selected_representation]
            else:
                repre_doc = repres_by_name[container_repre_name]

        error = None
        try:
            switch_container(container, repre_doc, loader)
        except (
            LoaderSwitchNotImplementedError,
            IncompatibleLoaderError,
            LoaderNotFoundError,
        ) as exc:
            error = str(exc)
        except Exception:
            error = (
                "Switch asset failed. "
                "Search console log for more details."
            )
        if error is not None:
            log.warning((
                "Couldn't switch asset."
                "See traceback for more information."
            ), exc_info=True)
            dialog = QtWidgets.QMessageBox(self)
            dialog.setWindowTitle("Switch asset failed")
            dialog.setText(error)
            dialog.exec_()
