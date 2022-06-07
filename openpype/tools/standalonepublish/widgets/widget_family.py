import re

from Qt import QtWidgets, QtCore

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_subsets,
    get_last_version_by_subset_id,
)
from openpype.api import get_project_settings
from openpype.pipeline import LegacyCreator
from openpype.lib import TaskNotSetError
from openpype.pipeline.create import SUBSET_NAME_ALLOWED_SYMBOLS

from . import HelpRole, FamilyRole, ExistsRole, PluginRole, PluginKeyRole
from . import FamilyDescriptionWidget


class FamilyWidget(QtWidgets.QWidget):

    stateChanged = QtCore.Signal(bool)
    data = dict()
    _jobs = dict()
    Separator = "---separator---"
    NOT_SELECTED = '< Nothing is selected >'

    def __init__(self, dbcon, parent=None):
        super(FamilyWidget, self).__init__(parent=parent)
        # Store internal states in here
        self.state = {"valid": False}
        self.dbcon = dbcon
        self.asset_name = self.NOT_SELECTED

        body = QtWidgets.QWidget()
        lists = QtWidgets.QWidget()

        container = QtWidgets.QWidget()

        list_families = QtWidgets.QListWidget()

        input_subset = QtWidgets.QLineEdit()
        input_result = QtWidgets.QLineEdit()
        input_result.setEnabled(False)

        # region Menu for default subset names
        btn_subset = QtWidgets.QPushButton()
        btn_subset.setFixedWidth(18)
        menu_subset = QtWidgets.QMenu(btn_subset)
        btn_subset.setMenu(menu_subset)

        # endregion
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(input_subset, 1)
        name_layout.addWidget(btn_subset, 0)
        name_layout.setContentsMargins(0, 0, 0, 0)

        # version
        version_spinbox = QtWidgets.QSpinBox()
        version_spinbox.setButtonSymbols(QtWidgets.QSpinBox.NoButtons)
        version_spinbox.setMinimum(1)
        version_spinbox.setMaximum(9999)
        version_spinbox.setEnabled(False)

        version_checkbox = QtWidgets.QCheckBox("Next Available Version")
        version_checkbox.setCheckState(QtCore.Qt.CheckState(2))

        version_layout = QtWidgets.QHBoxLayout()
        version_layout.addWidget(version_spinbox)
        version_layout.addWidget(version_checkbox)

        layout = QtWidgets.QVBoxLayout(container)

        header = FamilyDescriptionWidget(parent=self)
        layout.addWidget(header)

        layout.addWidget(QtWidgets.QLabel("Family"))
        layout.addWidget(list_families)
        layout.addWidget(QtWidgets.QLabel("Subset"))
        layout.addLayout(name_layout)
        layout.addWidget(input_result)
        layout.addWidget(QtWidgets.QLabel("Version"))
        layout.addLayout(version_layout)
        layout.setContentsMargins(0, 0, 0, 0)

        options = QtWidgets.QWidget()

        layout = QtWidgets.QGridLayout(options)
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QHBoxLayout(lists)
        layout.addWidget(container)
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(body)

        layout.addWidget(lists)
        layout.addWidget(options, 0, QtCore.Qt.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)

        input_subset.textChanged.connect(self.on_data_changed)
        list_families.currentItemChanged.connect(self.on_selection_changed)
        list_families.currentItemChanged.connect(header.set_item)
        version_checkbox.stateChanged.connect(self.on_version_refresh)

        self.stateChanged.connect(self._on_state_changed)

        self.input_subset = input_subset
        self.menu_subset = menu_subset
        self.btn_subset = btn_subset
        self.list_families = list_families
        self.input_result = input_result
        self.version_checkbox = version_checkbox
        self.version_spinbox = version_spinbox

        self.refresh()

    def collect_data(self):
        plugin = self.list_families.currentItem().data(PluginRole)
        key = self.list_families.currentItem().data(PluginKeyRole)
        family = plugin.family.rsplit(".", 1)[-1]
        data = {
            'family_preset_key': key,
            'family': family,
            'subset': self.input_result.text(),
            'version': self.version_spinbox.value()
        }
        return data

    def on_task_change(self):
        self.on_data_changed()

    def change_asset(self, name):
        if name is None:
            name = self.NOT_SELECTED
        self.asset_name = name
        self.on_data_changed()

    def _on_state_changed(self, state):
        self.state['valid'] = state

    def _build_menu(self, default_names):
        """Create optional predefined subset names

        Args:
            default_names(list): all predefined names

        Returns:
             None
        """

        # Get and destroy the action group
        group = self.btn_subset.findChild(QtWidgets.QActionGroup)
        if group:
            group.deleteLater()

        state = any(default_names)
        self.btn_subset.setEnabled(state)
        if state is False:
            return

        # Build new action group
        group = QtWidgets.QActionGroup(self.btn_subset)
        for name in default_names:
            if name == self.Separator:
                self.menu_subset.addSeparator()
                continue
            action = group.addAction(name)
            self.menu_subset.addAction(action)

        group.triggered.connect(self._on_action_clicked)

    def _on_action_clicked(self, action):
        self.input_subset.setText(action.text())

    def _on_data_changed(self):
        asset_name = self.asset_name
        user_input_text = self.input_subset.text()
        item = self.list_families.currentItem()

        if item is None:
            return

        asset_doc = None
        if asset_name != self.NOT_SELECTED:
            # Get the assets from the database which match with the name
            project_name = self.dbcon.active_project()
            asset_doc = get_asset_by_name(
                project_name, asset_name, fields=["_id"]
            )

        # Get plugin and family
        plugin = item.data(PluginRole)

        # Early exit if no asset name
        if not asset_name.strip():
            self._build_menu([])
            item.setData(ExistsRole, False)
            print("Asset name is required ..")
            self.stateChanged.emit(False)
            return

        # Get the asset from the database which match with the name
        project_name = self.dbcon.active_project()
        asset_doc = get_asset_by_name(
            project_name, asset_name, fields=["_id"]
        )
        # Get plugin
        plugin = item.data(PluginRole)
        if asset_doc and plugin:
            asset_id = asset_doc["_id"]
            task_name = self.dbcon.Session["AVALON_TASK"]

            # Calculate subset name with Creator plugin
            try:
                subset_name = plugin.get_subset_name(
                    user_input_text, task_name, asset_id, project_name
                )
                # Force replacement of prohibited symbols
                # QUESTION should Creator care about this and here should be
                #   only validated with schema regex?
                subset_name = re.sub(
                    "[^{}]+".format(SUBSET_NAME_ALLOWED_SYMBOLS),
                    "",
                    subset_name
                )
                self.input_result.setText(subset_name)

            except TaskNotSetError:
                subset_name = ""
                self.input_result.setText("Select task please")

            # Get all subsets of the current asset
            subset_docs = get_subsets(
                project_name, asset_ids=[asset_id], fields=["name"]
            )

            existing_subset_names = {
                subset_doc["name"]
                for subset_doc in subset_docs
            }

            # Defaults to dropdown
            defaults = []
            # Check if Creator plugin has set defaults
            if (
                plugin.defaults
                and isinstance(plugin.defaults, (list, tuple, set))
            ):
                defaults = list(plugin.defaults)

            # Replace
            compare_regex = re.compile(re.sub(
                user_input_text, "(.+)", subset_name, flags=re.IGNORECASE
            ))
            subset_hints = set()
            if user_input_text:
                for _name in existing_subset_names:
                    _result = compare_regex.search(_name)
                    if _result:
                        subset_hints |= set(_result.groups())

            subset_hints = subset_hints - set(defaults)
            if subset_hints:
                if defaults:
                    defaults.append(self.Separator)
                defaults.extend(subset_hints)
            self._build_menu(defaults)

            item.setData(ExistsRole, True)

        else:
            subset_name = user_input_text
            self._build_menu([])
            item.setData(ExistsRole, False)

            if not plugin:
                print("No registered families ..")
            else:
                print("Asset '%s' not found .." % asset_name)

        self.on_version_refresh()

        # Update the valid state
        valid = (
            asset_name != self.NOT_SELECTED and
            subset_name.strip() != "" and
            item.data(QtCore.Qt.ItemIsEnabled) and
            item.data(ExistsRole)
        )
        self.stateChanged.emit(valid)

    def on_version_refresh(self):
        auto_version = self.version_checkbox.isChecked()
        self.version_spinbox.setEnabled(not auto_version)
        if not auto_version:
            return

        project_name = self.dbcon.active_project()
        asset_name = self.asset_name
        subset_name = self.input_result.text()
        version = 1

        asset_doc = None
        subset_doc = None
        if (
            asset_name != self.NOT_SELECTED and
            subset_name.strip() != ''
        ):
            asset_doc = get_asset_by_name(
                project_name, asset_name, fields=["_id"]
            )

        if asset_doc:
            subset_doc = get_subset_by_name(
                project_name,
                subset_name,
                asset_doc['_id'],
                fields=["_id"]
            )

        if subset_doc:
            last_version = get_last_version_by_subset_id(
                project_name,
                subset_doc["_id"],
                fields=["name"]
            )
            if last_version:
                version = last_version["name"] + 1

        self.version_spinbox.setValue(version)

    def on_data_changed(self, *args):

        # Set invalid state until it's reconfirmed to be valid by the
        # scheduled callback so any form of creation is held back until
        # valid again
        self.stateChanged.emit(False)
        self.schedule(self._on_data_changed, 500, channel="gui")

    def on_selection_changed(self, *args):
        item = self.list_families.currentItem()
        if not item:
            return
        plugin = item.data(PluginRole)
        if plugin is None:
            return

        if plugin.defaults and isinstance(plugin.defaults, list):
            default = plugin.defaults[0]
        else:
            default = "Default"

        self.input_subset.setText(default)

        self.on_data_changed()

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidentally perform Maya commands
        whilst trying to name an instance.

        """

    def refresh(self):
        self.list_families.clear()

        has_families = False
        project_name = self.dbcon.Session.get("AVALON_PROJECT")
        if not project_name:
            return

        settings = get_project_settings(project_name)
        sp_settings = settings.get('standalonepublisher', {})

        for key, creator_data in sp_settings.get("create", {}).items():
            creator = type(key, (LegacyCreator, ), creator_data)

            label = creator.label or creator.family
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, True)
            item.setData(HelpRole, creator.help or "")
            item.setData(FamilyRole, creator.family)
            item.setData(PluginRole, creator)
            item.setData(PluginKeyRole, key)
            item.setData(ExistsRole, False)
            self.list_families.addItem(item)

            has_families = True

        if not has_families:
            item = QtWidgets.QListWidgetItem("No registered families")
            item.setData(QtCore.Qt.ItemIsEnabled, False)
            self.list_families.addItem(item)

        self.list_families.setCurrentItem(self.list_families.item(0))

    def schedule(self, func, time, channel="default"):
        try:
            self._jobs[channel].stop()
        except (AttributeError, KeyError):
            pass

        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(func)
        timer.start(time)

        self._jobs[channel] = timer
