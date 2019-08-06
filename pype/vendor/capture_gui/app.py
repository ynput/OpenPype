import json
import logging
import os
import tempfile

import capture
import maya.cmds as cmds

from .vendor.Qt import QtCore, QtWidgets, QtGui
from . import lib
from . import plugin
from . import presets
from . import version
from . import tokens
from .accordion import AccordionWidget

log = logging.getLogger("Capture Gui")


class ClickLabel(QtWidgets.QLabel):
    """A QLabel that emits a clicked signal when clicked upon."""
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        return super(ClickLabel, self).mouseReleaseEvent(event)


class PreviewWidget(QtWidgets.QWidget):
    """The playblast image preview widget.

    Upon refresh it will retrieve the options through the function set as
    `options_getter` and make a call to `capture.capture()` for a single
    frame (playblasted) snapshot. The result is displayed as image.
    """

    preview_width = 320
    preview_height = 180

    def __init__(self, options_getter, validator, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Add attributes
        self.options_getter = options_getter
        self.validator = validator
        self.preview = ClickLabel()
        self.preview.setFixedWidth(self.preview_width)
        self.preview.setFixedHeight(self.preview_height)

        tip = "Click to force a refresh"
        self.preview.setToolTip(tip)
        self.preview.setStatusTip(tip)

        # region Build
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)
        self.layout.addWidget(self.preview)
        # endregion Build

        # Connect widgets to functions
        self.preview.clicked.connect(self.refresh)

    def refresh(self):
        """Refresh the playblast preview"""

        frame = cmds.currentTime(query=True)

        # When playblasting outside of an undo queue it seems that undoing
        # actually triggers a reset to frame 0. As such we sneak in the current
        # time into the undo queue to enforce correct undoing.
        cmds.currentTime(frame, update=True)

        # check if plugin outputs are correct
        valid = self.validator()
        if not valid:
            return

        with lib.no_undo():
            options = self.options_getter()
            tempdir = tempfile.mkdtemp()

            # override settings that are constants for the preview
            options = options.copy()
            options['filename'] = None
            options['complete_filename'] = os.path.join(tempdir, "temp.jpg")
            options['width'] = self.preview_width
            options['height'] = self.preview_height
            options['viewer'] = False
            options['frame'] = frame
            options['off_screen'] = True
            options['format'] = "image"
            options['compression'] = "jpg"
            options['sound'] = None

            fname = capture.capture(**options)
            if not fname:
                log.warning("Preview failed")
                return

            image = QtGui.QPixmap(fname)
            self.preview.setPixmap(image)
            os.remove(fname)

    def showEvent(self, event):
        """Initialize when shown"""
        self.refresh()
        event.accept()


class PresetWidget(QtWidgets.QWidget):
    """Preset Widget

    Allows the user to set preferences and create presets to load before
    capturing.

    """

    preset_loaded = QtCore.Signal(dict)
    config_opened = QtCore.Signal()

    id = "Presets"
    label = "Presets"

    def __init__(self, inputs_getter, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.inputs_getter = inputs_getter

        layout = QtWidgets.QHBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        presets = QtWidgets.QComboBox()
        presets.setFixedWidth(220)
        presets.addItem("*")

        # Icons
        icon_path = os.path.join(os.path.dirname(__file__), "resources")
        save_icon = os.path.join(icon_path, "save.png")
        load_icon = os.path.join(icon_path, "import.png")
        config_icon = os.path.join(icon_path, "config.png")

        # Create buttons
        save = QtWidgets.QPushButton()
        save.setIcon(QtGui.QIcon(save_icon))
        save.setFixedWidth(30)
        save.setToolTip("Save Preset")
        save.setStatusTip("Save Preset")

        load = QtWidgets.QPushButton()
        load.setIcon(QtGui.QIcon(load_icon))
        load.setFixedWidth(30)
        load.setToolTip("Load Preset")
        load.setStatusTip("Load Preset")

        config = QtWidgets.QPushButton()
        config.setIcon(QtGui.QIcon(config_icon))
        config.setFixedWidth(30)
        config.setToolTip("Preset configuration")
        config.setStatusTip("Preset configuration")

        layout.addWidget(presets)
        layout.addWidget(save)
        layout.addWidget(load)
        layout.addWidget(config)

        # Make available for all methods
        self.presets = presets
        self.config = config
        self.load = load
        self.save = save

        # Signals
        self.save.clicked.connect(self.on_save_preset)
        self.load.clicked.connect(self.import_preset)
        self.config.clicked.connect(self.config_opened)
        self.presets.currentIndexChanged.connect(self.load_active_preset)

        self._process_presets()

    def _process_presets(self):
        """Adds all preset files from preset paths to the Preset widget.

        Returns:
            None

        """
        for presetfile in presets.discover():
            self.add_preset(presetfile)

    def import_preset(self):
        """Load preset files to override output values"""

        path = self._default_browse_path()
        filters = "Text file (*.json)"
        dialog = QtWidgets.QFileDialog
        filename, _ = dialog.getOpenFileName(self, "Open preference file",
                                             path, filters)
        if not filename:
            return

        # create new entry in combobox
        self.add_preset(filename)

        # read file
        return self.load_active_preset()

    def load_active_preset(self):
        """Load the active preset.

        Returns:
            dict: The preset inputs.

        """
        current_index = self.presets.currentIndex()
        filename = self.presets.itemData(current_index)
        if not filename:
            return {}

        preset = lib.load_json(filename)

        # Emit preset load signal
        log.debug("Emitting preset_loaded: {0}".format(filename))
        self.preset_loaded.emit(preset)

        # Ensure we preserve the index after loading the changes
        # for all the plugin widgets
        self.presets.blockSignals(True)
        self.presets.setCurrentIndex(current_index)
        self.presets.blockSignals(False)

        return preset

    def add_preset(self, filename):
        """Add the filename to the preset list.

        This also sets the index to the filename.

        Returns:
            None

        """

        filename = os.path.normpath(filename)
        if not os.path.exists(filename):
            log.warning("Preset file does not exist: {0}".format(filename))
            return

        label = os.path.splitext(os.path.basename(filename))[0]
        item_count = self.presets.count()

        paths = [self.presets.itemData(i) for i in range(item_count)]
        if filename in paths:
            log.info("Preset is already in the "
                     "presets list: {0}".format(filename))
            item_index = paths.index(filename)
        else:
            self.presets.addItem(label, userData=filename)
            item_index = item_count

        self.presets.blockSignals(True)
        self.presets.setCurrentIndex(item_index)
        self.presets.blockSignals(False)

        return item_index

    def _default_browse_path(self):
        """Return the current browse path for save/load preset.

        If a preset is currently loaded it will use that specific path
        otherwise it will go to the last registered preset path.

        Returns:
            str: Path to use as default browse location.

        """

        current_index = self.presets.currentIndex()
        path = self.presets.itemData(current_index)

        if not path:
            # Fallback to last registered preset path
            paths = presets.preset_paths()
            if paths:
                path = paths[-1]

        return path

    def save_preset(self, inputs):
        """Save inputs to a file"""

        path = self._default_browse_path()
        filters = "Text file (*.json)"
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                            "Save preferences",
                                                            path,
                                                            filters)
        if not filename:
            return

        with open(filename, "w") as f:
            json.dump(inputs, f, sort_keys=True,
                      indent=4, separators=(',', ': '))

        self.add_preset(filename)

        return filename

    def get_presets(self):
        """Return all currently listed presets"""
        configurations = [self.presets.itemText(i) for
                          i in range(self.presets.count())]

        return configurations

    def on_save_preset(self):
        """Save the inputs of all the plugins in a preset."""

        inputs = self.inputs_getter(as_preset=True)
        self.save_preset(inputs)

    def apply_inputs(self, settings):

        path = settings.get("selected", None)
        index = self.presets.findData(path)
        if index == -1:
            # If the last loaded preset still exists but wasn't on the
            # "discovered preset paths" then add it.
            if os.path.exists(path):
                log.info("Adding previously selected preset explicitly: %s",
                         path)
                self.add_preset(path)
                return
            else:
                log.warning("Previously selected preset is not available: %s",
                            path)
                index = 0

        self.presets.setCurrentIndex(index)

    def get_inputs(self, as_preset=False):

        if as_preset:
            # Don't save the current preset into the preset because
            # that would just be recursive and make no sense
            return {}
        else:
            current_index = self.presets.currentIndex()
            selected = self.presets.itemData(current_index)
            return {"selected": selected}


class App(QtWidgets.QWidget):
    """The main application in which the widgets are placed"""

    # Signals
    options_changed = QtCore.Signal(dict)
    playblast_start = QtCore.Signal(dict)
    playblast_finished = QtCore.Signal(dict)
    viewer_start = QtCore.Signal(dict)

    # Attributes
    object_name = "CaptureGUI"
    application_sections = ["config", "app"]

    def __init__(self, title, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        # Settings
        # Remove pointer for memory when closed
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.settingfile = self._ensure_config_exist()
        self.plugins = {"app": list(),
                        "config": list()}

        self._config_dialog = None
        self._build_configuration_dialog()

        # region Set Attributes
        title_version = "{} v{}".format(title, version.version)
        self.setObjectName(self.object_name)
        self.setWindowTitle(title_version)
        self.setMinimumWidth(380)

        # Set dialog window flags so the widget can be correctly parented
        # to Maya main window
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Dialog)
        self.setProperty("saveWindowPref", True)
        # endregion Set Attributes

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Add accordion widget (Maya attribute editor style)
        self.widgetlibrary = AccordionWidget(self)
        self.widgetlibrary.setRolloutStyle(AccordionWidget.Maya)

        # Add separate widgets
        self.widgetlibrary.addItem("Preview",
                                   PreviewWidget(self.get_outputs,
                                                 self.validate,
                                                 parent=self),
                                   collapsed=True)

        self.presetwidget = PresetWidget(inputs_getter=self.get_inputs,
                                         parent=self)
        self.widgetlibrary.addItem("Presets", self.presetwidget)

        # add plug-in widgets
        for widget in plugin.discover():
            self.add_plugin(widget)

        self.layout.addWidget(self.widgetlibrary)

        # add standard buttons
        self.apply_button = QtWidgets.QPushButton("Capture")
        self.layout.addWidget(self.apply_button)

        # default actions
        self.apply_button.clicked.connect(self.apply)

        # signals and slots
        self.presetwidget.config_opened.connect(self.show_config)
        self.presetwidget.preset_loaded.connect(self.apply_inputs)

        self.apply_inputs(self._read_widget_configuration())

    def apply(self):
        """Run capture action with current settings"""

        valid = self.validate()
        if not valid:
            return

        options = self.get_outputs()
        filename = options.get("filename", None)

        self.playblast_start.emit(options)

        # The filename can be `None` when the
        # playblast will *not* be saved.
        if filename is not None:
            # Format the tokens in the filename
            filename = tokens.format_tokens(filename, options)

            # expand environment variables
            filename = os.path.expandvars(filename)

            # Make relative paths absolute to the "images" file rule by default
            if not os.path.isabs(filename):
                root = lib.get_project_rule("images")
                filename = os.path.join(root, filename)

            # normalize (to remove double slashes and alike)
            filename = os.path.normpath(filename)

        options["filename"] = filename

        # Perform capture and store returned filename with extension
        options["filename"] = lib.capture_scene(options)

        self.playblast_finished.emit(options)
        filename = options["filename"]  # get filename after callbacks

        # Show viewer
        viewer = options.get("viewer", False)
        if viewer:
            if filename and os.path.exists(filename):
                self.viewer_start.emit(options)
                lib.open_file(filename)
            else:
                raise RuntimeError("Can't open playblast because file "
                                   "doesn't exist: {0}".format(filename))

        return filename

    def apply_inputs(self, inputs):
        """Apply all the settings of the widgets.

        Arguments:
            inputs (dict): input values per plug-in widget

        Returns:
            None

        """
        if not inputs:
            return

        widgets = self._get_plugin_widgets()
        widgets.append(self.presetwidget)
        for widget in widgets:
            widget_inputs = inputs.get(widget.id, None)
            if not widget_inputs:
                continue
            widget.apply_inputs(widget_inputs)

    def show_config(self):
        """Show the advanced configuration"""
        # calculate center of main widget
        geometry = self.geometry()
        self._config_dialog.move(QtCore.QPoint(geometry.x()+30,
                                               geometry.y()))
        self._config_dialog.show()

    def add_plugin(self, plugin):
        """Add an options widget plug-in to the UI"""

        if plugin.section not in self.application_sections:
            log.warning("{}'s section is invalid: "
                        "{}".format(plugin.label, plugin.section))
            return

        widget = plugin(parent=self)
        widget.initialize()
        widget.options_changed.connect(self.on_widget_settings_changed)
        self.playblast_finished.connect(widget.on_playblast_finished)

        # Add to plug-ins in its section
        self.plugins[widget.section].append(widget)

        # Implement additional settings depending on section
        if widget.section == "app":
            if not widget.hidden:
                item = self.widgetlibrary.addItem(widget.label, widget)
                # connect label change behaviour
                widget.label_changed.connect(item.setTitle)

        # Add the plugin in a QGroupBox to the configuration dialog
        if widget.section == "config":
            layout = self._config_dialog.layout()
            # create group box
            group_widget = QtWidgets.QGroupBox(widget.label)
            group_layout = QtWidgets.QVBoxLayout(group_widget)
            group_layout.addWidget(widget)

            layout.addWidget(group_widget)

    def validate(self):
        """Validate whether the outputs of the widgets are good.

        Returns:
            bool: Whether it's valid to capture the current settings.

        """

        errors = list()
        for widget in self._get_plugin_widgets():
            widget_errors = widget.validate()
            if widget_errors:
                errors.extend(widget_errors)

        if errors:
            message_title = "%s Validation Error(s)" % len(errors)
            message = "\n".join(errors)
            QtWidgets.QMessageBox.critical(self,
                                           message_title,
                                           message,
                                           QtWidgets.QMessageBox.Ok)
            return False

        return True

    def get_outputs(self):
        """Return settings for a capture as currently set in the Application.

        Returns:
            dict: Current output settings

        """

        # Get settings from widgets
        outputs = dict()
        for widget in self._get_plugin_widgets():
            widget_outputs = widget.get_outputs()
            if not widget_outputs:
                continue

            for key, value in widget_outputs.items():

                # We merge dictionaries by updating them so we have
                # the "mixed" values of both settings
                if isinstance(value, dict) and key in outputs:
                    outputs[key].update(value)
                else:
                    outputs[key] = value

        return outputs

    def get_inputs(self, as_preset=False):
        """Return the inputs per plug-in widgets by `plugin.id`.

        Returns:
            dict: The inputs per widget

        """

        inputs = dict()
        # Here we collect all the widgets from which we want to store the
        # current inputs. This will be restored in the next session
        # The preset widget is added to make sure the user starts with the
        # previously selected preset configuration
        config_widgets = self._get_plugin_widgets()
        config_widgets.append(self.presetwidget)
        for widget in config_widgets:
            widget_inputs = widget.get_inputs(as_preset=as_preset)
            if not isinstance(widget_inputs, dict):
                log.debug("Widget inputs are not a dictionary "
                          "'{}': {}".format(widget.id, widget_inputs))
                return

            if not widget_inputs:
                continue

            inputs[widget.id] = widget_inputs

        return inputs

    def on_widget_settings_changed(self):
        """Set current preset to '*' on settings change"""

        self.options_changed.emit(self.get_outputs)
        self.presetwidget.presets.setCurrentIndex(0)

    def _build_configuration_dialog(self):
        """Build a configuration to store configuration widgets in"""

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Capture - Preset Configuration")
        QtWidgets.QVBoxLayout(dialog)

        self._config_dialog = dialog

    def _ensure_config_exist(self):
        """Create the configuration file if it does not exist yet.

        Returns:
            unicode: filepath of the configuration file

        """

        userdir = os.path.expanduser("~")
        capturegui_dir = os.path.join(userdir, "CaptureGUI")
        capturegui_inputs = os.path.join(capturegui_dir, "capturegui.json")
        if not os.path.exists(capturegui_dir):
            os.makedirs(capturegui_dir)

        if not os.path.isfile(capturegui_inputs):
            config = open(capturegui_inputs, "w")
            config.close()

        return capturegui_inputs

    def _store_widget_configuration(self):
        """Store all used widget settings in the local json file"""

        inputs = self.get_inputs(as_preset=False)
        path = self.settingfile

        with open(path, "w") as f:
            log.debug("Writing JSON file: {0}".format(path))
            json.dump(inputs, f, sort_keys=True,
                      indent=4, separators=(',', ': '))

    def _read_widget_configuration(self):
        """Read the stored widget inputs"""

        inputs = {}
        path = self.settingfile

        if not os.path.isfile(path) or os.stat(path).st_size == 0:
            return inputs

        with open(path, "r") as f:
            log.debug("Reading JSON file: {0}".format(path))
            try:
                inputs = json.load(f)
            except ValueError as error:
                log.error(str(error))

        return inputs

    def _get_plugin_widgets(self):
        """List all plug-in widgets.

        Returns:
            list: The plug-in widgets in *all* sections

        """

        widgets = list()
        for section in self.plugins.values():
            widgets.extend(section)

        return widgets

    # override close event to ensure the input are stored

    def closeEvent(self, event):
        """Store current configuration upon closing the application."""

        self._store_widget_configuration()
        for section_widgets in self.plugins.values():
            for widget in section_widgets:
                widget.uninitialize()

        event.accept()
