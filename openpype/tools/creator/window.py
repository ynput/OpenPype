import sys
import inspect
import traceback
import re

from Qt import QtWidgets, QtCore, QtGui
from avalon.vendor import qtawesome
import six
from avalon import api, io, style

from .widgets import CreateErrorMessageBox
from avalon.tools import lib
from openpype.api import get_current_project_settings

module = sys.modules[__name__]
module.window = None
module.root = api.registered_root()

HelpRole = QtCore.Qt.UserRole + 2
FamilyRole = QtCore.Qt.UserRole + 3
ExistsRole = QtCore.Qt.UserRole + 4
PluginRole = QtCore.Qt.UserRole + 5

Separator = "---separator---"

# TODO regex should be defined by schema
SubsetAllowedSymbols = "a-zA-Z0-9_."


class SubsetNameValidator(QtGui.QRegExpValidator):

    invalid = QtCore.Signal(set)
    pattern = "^[{}]*$".format(SubsetAllowedSymbols)

    def __init__(self):
        reg = QtCore.QRegExp(self.pattern)
        super(SubsetNameValidator, self).__init__(reg)

    def validate(self, input, pos):
        results = super(SubsetNameValidator, self).validate(input, pos)
        if results[0] == self.Invalid:
            self.invalid.emit(self.invalid_chars(input))
        return results

    def invalid_chars(self, input):
        invalid = set()
        re_valid = re.compile(self.pattern)
        for char in input:
            if char == " ":
                invalid.add("' '")
                continue
            if not re_valid.match(char):
                invalid.add(char)
        return invalid


class SubsetNameLineEdit(QtWidgets.QLineEdit):

    report = QtCore.Signal(str)
    colors = {
        "empty": (QtGui.QColor("#78879b"), ""),
        "exists": (QtGui.QColor("#4E76BB"), "border-color: #4E76BB;"),
        "new": (QtGui.QColor("#7AAB8F"), "border-color: #7AAB8F;"),
    }

    def __init__(self, *args, **kwargs):
        super(SubsetNameLineEdit, self).__init__(*args, **kwargs)

        validator = SubsetNameValidator()
        self.setValidator(validator)
        self.setToolTip("Only alphanumeric characters (A-Z a-z 0-9), "
                        "'_' and '.' are allowed.")

        self._status_color = self.colors["empty"][0]

        anim = QtCore.QPropertyAnimation()
        anim.setTargetObject(self)
        anim.setPropertyName(b"status_color")
        anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        anim.setDuration(300)
        anim.setStartValue(QtGui.QColor("#C84747"))  # `Invalid` status color
        self.animation = anim

        validator.invalid.connect(self.on_invalid)

    def on_invalid(self, invalid):
        message = "Invalid character: %s" % ", ".join(invalid)
        self.report.emit(message)
        self.animation.stop()
        self.animation.start()

    def as_empty(self):
        self._set_border("empty")
        self.report.emit("Empty subset name ..")

    def as_exists(self):
        self._set_border("exists")
        self.report.emit("Existing subset, appending next version.")

    def as_new(self):
        self._set_border("new")
        self.report.emit("New subset, creating first version.")

    def _set_border(self, status):
        qcolor, style = self.colors[status]
        self.animation.setEndValue(qcolor)
        self.setStyleSheet(style)

    def _get_status_color(self):
        return self._status_color

    def _set_status_color(self, color):
        self._status_color = color
        self.setStyleSheet("border-color: %s;" % color.name())

    status_color = QtCore.Property(QtGui.QColor,
                                   _get_status_color,
                                   _set_status_color)


class Window(QtWidgets.QDialog):

    stateChanged = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle("Instance Creator")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        if not parent:
            self.setWindowFlags(
                self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
            )

        # Store the widgets for lookup in here
        self.data = dict()

        # Store internal states in here
        self.state = {
            "valid": False
        }
        # Message dialog when something goes wrong during creation
        self.message_dialog = None

        body = QtWidgets.QWidget()
        lists = QtWidgets.QWidget()
        footer = QtWidgets.QWidget()

        container = QtWidgets.QWidget()

        listing = QtWidgets.QListWidget()
        listing.setSortingEnabled(True)
        asset = QtWidgets.QLineEdit()
        name = SubsetNameLineEdit()
        result = QtWidgets.QLineEdit()
        result.setStyleSheet("color: gray;")
        result.setEnabled(False)

        # region Menu for default subset names

        subset_button = QtWidgets.QPushButton()
        subset_button.setFixedWidth(18)
        subset_menu = QtWidgets.QMenu(subset_button)
        subset_button.setMenu(subset_menu)

        # endregion

        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(name)
        name_layout.addWidget(subset_button)
        name_layout.setSpacing(3)
        name_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(container)

        header = FamilyDescriptionWidget(parent=self)
        layout.addWidget(header)

        layout.addWidget(QtWidgets.QLabel("Family"))
        layout.addWidget(listing)
        layout.addWidget(QtWidgets.QLabel("Asset"))
        layout.addWidget(asset)
        layout.addWidget(QtWidgets.QLabel("Subset"))
        layout.addLayout(name_layout)
        layout.addWidget(result)
        layout.setContentsMargins(0, 0, 0, 0)

        options = QtWidgets.QWidget()

        useselection_chk = QtWidgets.QCheckBox("Use selection")
        useselection_chk.setCheckState(QtCore.Qt.Checked)

        layout = QtWidgets.QGridLayout(options)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(useselection_chk, 1, 1)

        layout = QtWidgets.QHBoxLayout(lists)
        layout.addWidget(container)
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(body)
        layout.addWidget(lists)
        layout.addWidget(options, 0, QtCore.Qt.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)

        create_btn = QtWidgets.QPushButton("Create")
        # Need to store error_msg to prevent garbage collection.
        self.error_msg = QtWidgets.QLabel()
        self.error_msg.setFixedHeight(20)

        layout = QtWidgets.QVBoxLayout(footer)
        layout.addWidget(create_btn)
        layout.addWidget(self.error_msg)
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(body)
        layout.addWidget(footer)

        self.data = {
            "Create Button": create_btn,
            "Listing": listing,
            "Use Selection Checkbox": useselection_chk,
            "Subset": name,
            "Subset Menu": subset_menu,
            "Result": result,
            "Asset": asset,
            "Error Message": self.error_msg,
        }

        for _name, widget in self.data.items():
            widget.setObjectName(_name)

        create_btn.clicked.connect(self.on_create)
        name.returnPressed.connect(self.on_create)
        name.textChanged.connect(self.on_data_changed)
        name.report.connect(self.echo)
        asset.textChanged.connect(self.on_data_changed)
        listing.currentItemChanged.connect(self.on_selection_changed)
        listing.currentItemChanged.connect(header.set_item)

        self.stateChanged.connect(self._on_state_changed)

        # Defaults
        self.resize(300, 500)
        name.setFocus()
        create_btn.setEnabled(False)

    def _on_state_changed(self, state):
        self.state["valid"] = state
        self.data["Create Button"].setEnabled(state)

    def _build_menu(self, default_names):
        """Create optional predefined subset names

        Args:
            default_names(list): all predefined names

        Returns:
             None
        """

        menu = self.data["Subset Menu"]
        button = menu.parent()

        # Get and destroy the action group
        group = button.findChild(QtWidgets.QActionGroup)
        if group:
            group.deleteLater()

        state = any(default_names)
        button.setEnabled(state)
        if state is False:
            return

        # Build new action group
        group = QtWidgets.QActionGroup(button)
        for name in default_names:
            if name == Separator:
                menu.addSeparator()
                continue
            action = group.addAction(name)
            menu.addAction(action)

        group.triggered.connect(self._on_action_clicked)

    def _on_action_clicked(self, action):
        name = self.data["Subset"]
        name.setText(action.text())

    def _on_data_changed(self):
        listing = self.data["Listing"]
        asset_name = self.data["Asset"]
        subset = self.data["Subset"]
        result = self.data["Result"]

        item = listing.currentItem()
        user_input_text = subset.text()
        asset_name = asset_name.text()

        # Early exit if no asset name
        if not asset_name.strip():
            self._build_menu([])
            item.setData(ExistsRole, False)
            self.echo("Asset name is required ..")
            self.stateChanged.emit(False)
            return

        # Get the asset from the database which match with the name
        asset_doc = io.find_one(
            {"name": asset_name, "type": "asset"},
            projection={"_id": 1}
        )
        # Get plugin
        plugin = item.data(PluginRole)
        if asset_doc and plugin:
            project_name = io.Session["AVALON_PROJECT"]
            asset_id = asset_doc["_id"]
            task_name = io.Session["AVALON_TASK"]

            # Calculate subset name with Creator plugin
            subset_name = plugin.get_subset_name(
                user_input_text, task_name, asset_id, project_name
            )
            # Force replacement of prohibited symbols
            # QUESTION should Creator care about this and here should be only
            #   validated with schema regex?

            # Allow curly brackets in subset name for dynamic keys
            curly_left = "__cbl__"
            curly_right = "__cbr__"
            tmp_subset_name = (
                subset_name
                .replace("{", curly_left)
                .replace("}", curly_right)
            )
            # Replace prohibited symbols
            tmp_subset_name = re.sub(
                "[^{}]+".format(SubsetAllowedSymbols),
                "",
                tmp_subset_name
            )
            subset_name = (
                tmp_subset_name
                .replace(curly_left, "{")
                .replace(curly_right, "}")
            )
            result.setText(subset_name)

            # Get all subsets of the current asset
            subset_docs = io.find(
                {
                    "type": "subset",
                    "parent": asset_id
                },
                {"name": 1}
            )
            existing_subset_names = set(subset_docs.distinct("name"))
            existing_subset_names_low = set(
                _name.lower()
                for _name in existing_subset_names
            )

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

            if subset_hints:
                if defaults:
                    defaults.append(Separator)
                defaults.extend(subset_hints)
            self._build_menu(defaults)

            # Indicate subset existence
            if not user_input_text:
                subset.as_empty()
            elif subset_name.lower() in existing_subset_names_low:
                # validate existence of subset name with lowered text
                #   - "renderMain" vs. "rensermain" mean same path item for
                #   windows
                subset.as_exists()
            else:
                subset.as_new()

            item.setData(ExistsRole, True)

        else:
            subset_name = user_input_text
            self._build_menu([])
            item.setData(ExistsRole, False)

            if not plugin:
                self.echo("No registered families ..")
            else:
                self.echo("Asset '%s' not found .." % asset_name)

        # Update the valid state
        valid = (
            subset_name.strip() != "" and
            item.data(QtCore.Qt.ItemIsEnabled) and
            item.data(ExistsRole)
        )
        self.stateChanged.emit(valid)

    def on_data_changed(self, *args):

        # Set invalid state until it's reconfirmed to be valid by the
        # scheduled callback so any form of creation is held back until
        # valid again
        self.stateChanged.emit(False)

        lib.schedule(self._on_data_changed, 500, channel="gui")

    def on_selection_changed(self, *args):
        name = self.data["Subset"]
        item = self.data["Listing"].currentItem()

        plugin = item.data(PluginRole)
        if plugin is None:
            return

        default = None
        if hasattr(plugin, "get_default_variant"):
            default = plugin.get_default_variant()

        if not default:
            if plugin.defaults and isinstance(plugin.defaults, list):
                default = plugin.defaults[0]
            else:
                default = "Default"

        name.setText(default)

        self.on_data_changed()

    def keyPressEvent(self, event):
        """Custom keyPressEvent.

        Override keyPressEvent to do nothing so that Maya's panels won't
        take focus when pressing "SHIFT" whilst mouse is over viewport or
        outliner. This way users don't accidently perform Maya commands
        whilst trying to name an instance.

        """

    def refresh(self):

        listing = self.data["Listing"]
        asset = self.data["Asset"]
        asset.setText(api.Session["AVALON_ASSET"])

        listing.clear()

        has_families = False

        creators = api.discover(api.Creator)

        for creator in creators:
            label = creator.label or creator.family
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, True)
            item.setData(HelpRole, creator.__doc__)
            item.setData(FamilyRole, creator.family)
            item.setData(PluginRole, creator)
            item.setData(ExistsRole, False)
            listing.addItem(item)

            has_families = True

        if not has_families:
            item = QtWidgets.QListWidgetItem("No registered families")
            item.setData(QtCore.Qt.ItemIsEnabled, False)
            listing.addItem(item)

        pype_project_setting = (
            get_current_project_settings()
            ["global"]
            ["tools"]
            ["creator"]
            ["families_smart_select"]
        )
        item = None
        family_type = None
        task_name = io.Session.get('AVALON_TASK', None)
        if task_name:
            for key, value in pype_project_setting.items():
                for t_name in value:
                    if t_name in task_name.lower():
                        family_type = key
                        break
                if family_type:
                    break
            if family_type:
                items = listing.findItems(family_type, QtCore.Qt.MatchExactly)
                if len(items) > 0:
                    item = items[0]
                    listing.setCurrentItem(item)
        if not item:
            listing.setCurrentItem(listing.item(0))

    def on_create(self):

        # Do not allow creation in an invalid state
        if not self.state["valid"]:
            return

        asset = self.data["Asset"]
        listing = self.data["Listing"]
        result = self.data["Result"]

        item = listing.currentItem()
        if item is None:
            return

        subset_name = result.text()
        asset = asset.text()
        family = item.data(FamilyRole)
        Creator = item.data(PluginRole)
        use_selection = self.data["Use Selection Checkbox"].isChecked()

        variant = self.data["Subset"].text()

        error_info = None
        try:
            api.create(
                Creator,
                subset_name,
                asset,
                options={"useSelection": use_selection},
                data={"variant": variant}
            )

        except api.CreatorError as exc:
            self.echo("Creator error: {}".format(str(exc)))
            error_info = (str(exc), None)

        except Exception as exc:
            self.echo("Program error: %s" % str(exc))

            exc_type, exc_value, exc_traceback = sys.exc_info()
            formatted_traceback = "".join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            ))
            error_info = (str(exc), formatted_traceback)

        if error_info:
            box = CreateErrorMessageBox(
                family, subset_name, asset, *error_info
            )
            box.show()
            # Store dialog so is not garbage collected before is shown
            self.message_dialog = box

        else:
            self.echo("Created %s .." % subset_name)

    def echo(self, message):
        widget = self.data["Error Message"]
        widget.setText(str(message))
        widget.show()

        lib.schedule(lambda: widget.setText(""), 5000, channel="message")


class FamilyDescriptionWidget(QtWidgets.QWidget):
    """A family description widget.

    Shows a family icon, family name and a help description.
    Used in creator header.

     _________________
    |  ____           |
    | |icon| FAMILY   |
    | |____| help     |
    |_________________|

    """

    SIZE = 35

    def __init__(self, parent=None):
        super(FamilyDescriptionWidget, self).__init__(parent=parent)

        # Header font
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(14)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        icon = QtWidgets.QLabel()
        icon.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Maximum)

        # Add 4 pixel padding to avoid icon being cut off
        icon.setFixedWidth(self.SIZE + 4)
        icon.setFixedHeight(self.SIZE + 4)
        icon.setStyleSheet("""
        QLabel {
            padding-right: 5px;
        }
        """)

        label_layout = QtWidgets.QVBoxLayout()
        label_layout.setSpacing(0)

        family = QtWidgets.QLabel("family")
        family.setFont(font)
        family.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)

        help = QtWidgets.QLabel("help")
        help.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        label_layout.addWidget(family)
        label_layout.addWidget(help)

        layout.addWidget(icon)
        layout.addLayout(label_layout)

        self.help = help
        self.family = family
        self.icon = icon

    def set_item(self, item):
        """Update elements to display information of a family item.

        Args:
            item (dict): A family item as registered with name, help and icon

        Returns:
            None

        """
        if not item:
            return

        # Support a font-awesome icon
        plugin = item.data(PluginRole)
        icon_name = getattr(plugin, "icon", None) or "info-circle"
        try:
            icon = qtawesome.icon("fa.{}".format(icon_name), color="white")
            pixmap = icon.pixmap(self.SIZE, self.SIZE)
        except Exception:
            print("BUG: Couldn't load icon \"fa.{}\"".format(str(icon_name)))
            # Create transparent pixmap
            pixmap = QtGui.QPixmap()
            pixmap.fill(QtCore.Qt.transparent)
        pixmap = pixmap.scaled(self.SIZE, self.SIZE)

        # Parse a clean line from the Creator's docstring
        docstring = inspect.getdoc(plugin)
        help = docstring.splitlines()[0] if docstring else ""

        self.icon.setPixmap(pixmap)
        self.family.setText(item.data(FamilyRole))
        self.help.setText(help)


def show(debug=False, parent=None):
    """Display asset creator GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): When provided parent the interface
            to this QObject.

    """

    try:
        module.window.close()
        del(module.window)
    except (AttributeError, RuntimeError):
        pass

    if debug:
        from avalon import mock
        for creator in mock.creators:
            api.register_plugin(api.Creator, creator)

        import traceback
        sys.excepthook = lambda typ, val, tb: traceback.print_last()

        io.install()

        any_project = next(
            project for project in io.projects()
            if project.get("active", True) is not False
        )

        api.Session["AVALON_PROJECT"] = any_project["name"]
        module.project = any_project["name"]

    with lib.application():
        window = Window(parent)
        window.setStyleSheet(style.load_stylesheet())
        window.refresh()
        window.show()

        module.window = window

        # Pull window to the front.
        module.window.raise_()
        module.window.activateWindow()
