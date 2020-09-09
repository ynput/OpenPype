from collections import namedtuple

from Qt import QtWidgets, QtCore
from . import HelpRole, FamilyRole, ExistsRole, PluginRole, PluginKeyRole
from . import FamilyDescriptionWidget

from pype.api import config


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
        input_result.setStyleSheet("color: #BBBBBB;")
        input_result.setEnabled(False)

        # region Menu for default subset names
        btn_subset = QtWidgets.QPushButton()
        btn_subset.setFixedWidth(18)
        btn_subset.setFixedHeight(20)
        menu_subset = QtWidgets.QMenu(btn_subset)
        btn_subset.setMenu(menu_subset)

        # endregion
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(input_subset)
        name_layout.addWidget(btn_subset)
        name_layout.setContentsMargins(0, 0, 0, 0)

        # version
        version_spinbox = QtWidgets.QSpinBox()
        version_spinbox.setMinimum(1)
        version_spinbox.setMaximum(9999)
        version_spinbox.setEnabled(False)
        version_spinbox.setStyleSheet("color: #BBBBBB;")

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
        subset_name = self.input_subset.text()
        item = self.list_families.currentItem()

        if item is None:
            return

        assets = None
        if asset_name != self.NOT_SELECTED:
            # Get the assets from the database which match with the name
            assets_db = self.dbcon.find(
                filter={"type": "asset"},
                projection={"name": 1}
            )
            assets = [
                asset for asset in assets_db if asset_name in asset["name"]
            ]

        # Get plugin and family
        plugin = item.data(PluginRole)
        if plugin is None:
            return

        family = plugin.family.rsplit(".", 1)[-1]

        # Update the result
        if subset_name:
            subset_name = subset_name[0].upper() + subset_name[1:]
        self.input_result.setText("{}{}".format(family, subset_name))

        if assets:
            # Get all subsets of the current asset
            asset_ids = [asset["_id"] for asset in assets]
            subsets = self.dbcon.find(filter={"type": "subset",
                                      "name": {"$regex": "{}*".format(family),
                                               "$options": "i"},
                                      "parent": {"$in": asset_ids}}) or []

            # Get all subsets' their subset name, "Default", "High", "Low"
            existed_subsets = [sub["name"].split(family)[-1]
                               for sub in subsets]

            if plugin.defaults and isinstance(plugin.defaults, list):
                defaults = plugin.defaults[:] + [self.Separator]
                lowered = [d.lower() for d in plugin.defaults]
                for sub in [s for s in existed_subsets
                            if s.lower() not in lowered]:
                    defaults.append(sub)
            else:
                defaults = existed_subsets

            self._build_menu(defaults)

            item.setData(ExistsRole, True)
        else:
            self._build_menu([])
            item.setData(ExistsRole, False)
            if asset_name != self.NOT_SELECTED:
                # TODO add logging into standalone_publish
                print("'%s' not found .." % asset_name)

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

        asset_name = self.asset_name
        subset_name = self.input_result.text()
        version = 1

        if (
            asset_name != self.NOT_SELECTED and
            subset_name.strip() != ''
        ):
            asset = self.dbcon.find_one({
                'type': 'asset',
                'name': asset_name
            })
            subset = self.dbcon.find_one({
                'type': 'subset',
                'parent': asset['_id'],
                'name': subset_name
            })
            if subset:
                versions = self.dbcon.find({
                    'type': 'version',
                    'parent': subset['_id']
                })
                if versions:
                    versions = sorted(
                        [v for v in versions],
                        key=lambda ver: ver['name']
                    )
                    version = int(versions[-1]['name']) + 1

        self.version_spinbox.setValue(version)

    def on_data_changed(self, *args):

        # Set invalid state until it's reconfirmed to be valid by the
        # scheduled callback so any form of creation is held back until
        # valid again
        self.stateChanged.emit(False)
        self.schedule(self._on_data_changed, 500, channel="gui")

    def on_selection_changed(self, *args):
        plugin = self.list_families.currentItem().data(PluginRole)
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
        outliner. This way users don't accidently perform Maya commands
        whilst trying to name an instance.

        """

    def refresh(self):
        has_families = False
        presets = config.get_presets().get('standalone_publish', {})

        for key, creator in presets.get('families', {}).items():
            creator = namedtuple("Creator", creator.keys())(*creator.values())

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
