from capture_gui.vendor.Qt import QtCore, QtWidgets
import capture_gui.plugin
import capture_gui.lib as lib
import capture


class ViewportPlugin(capture_gui.plugin.Plugin):
    """Plugin to apply viewport visibilities and settings"""

    id = "Viewport Options"
    label = "Viewport Options"
    section = "config"
    order = 70

    def __init__(self, parent=None):
        super(ViewportPlugin, self).__init__(parent=parent)

        # set inherited attributes
        self.setObjectName(self.label)

        # custom atttributes
        self.show_type_actions = list()

        # get information
        self.show_types = lib.get_show_object_types()

        # set main layout for widget
        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # build
        # region Menus
        menus_vlayout = QtWidgets.QHBoxLayout()

        # Display Lights
        self.display_light_menu = self._build_light_menu()
        self.display_light_menu.setFixedHeight(20)

        # Show
        self.show_types_button = QtWidgets.QPushButton("Show")
        self.show_types_button.setFixedHeight(20)
        self.show_types_menu = self._build_show_menu()
        self.show_types_button.setMenu(self.show_types_menu)

        # fill layout
        menus_vlayout.addWidget(self.display_light_menu)
        menus_vlayout.addWidget(self.show_types_button)

        # endregion Menus

        # region Checkboxes
        checkbox_layout = QtWidgets.QGridLayout()
        self.high_quality = QtWidgets.QCheckBox()
        self.high_quality.setText("Force Viewport 2.0 + AA")
        self.override_viewport = QtWidgets.QCheckBox("Override viewport "
                                                     "settings")
        self.override_viewport.setChecked(True)

        # two sided lighting
        self.two_sided_ligthing = QtWidgets.QCheckBox("Two Sided Ligthing")
        self.two_sided_ligthing.setChecked(False)

        # show
        self.shadows = QtWidgets.QCheckBox("Shadows")
        self.shadows.setChecked(False)

        checkbox_layout.addWidget(self.override_viewport, 0, 0)
        checkbox_layout.addWidget(self.high_quality, 0, 1)
        checkbox_layout.addWidget(self.two_sided_ligthing, 1, 0)
        checkbox_layout.addWidget(self.shadows, 1, 1)
        # endregion Checkboxes

        self._layout.addLayout(checkbox_layout)
        self._layout.addLayout(menus_vlayout)

        self.connections()

    def connections(self):

        self.high_quality.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.options_changed)
        self.override_viewport.stateChanged.connect(self.on_toggle_override)

        self.two_sided_ligthing.stateChanged.connect(self.options_changed)
        self.shadows.stateChanged.connect(self.options_changed)

        self.display_light_menu.currentIndexChanged.connect(
            self.options_changed
        )

    def _build_show_menu(self):
        """Build the menu to select which object types are shown in the output.

        Returns:
            QtGui.QMenu: The visibilities "show" menu.

        """

        menu = QtWidgets.QMenu(self)
        menu.setObjectName("ShowShapesMenu")
        menu.setWindowTitle("Show")
        menu.setFixedWidth(180)
        menu.setTearOffEnabled(True)

        # Show all check
        toggle_all = QtWidgets.QAction(menu, text="All")
        toggle_none = QtWidgets.QAction(menu, text="None")
        menu.addAction(toggle_all)
        menu.addAction(toggle_none)
        menu.addSeparator()

        # add plugin shapes if any
        for shape in self.show_types:
            action = QtWidgets.QAction(menu, text=shape)
            action.setCheckable(True)
            # emit signal when the state is changed of the checkbox
            action.toggled.connect(self.options_changed)
            menu.addAction(action)
            self.show_type_actions.append(action)

        # connect signals
        toggle_all.triggered.connect(self.toggle_all_visbile)
        toggle_none.triggered.connect(self.toggle_all_hide)

        return menu

    def _build_light_menu(self):
        """Build lighting menu.

        Create the menu items for the different types of lighting for
        in the viewport

        Returns:
            None

        """

        menu = QtWidgets.QComboBox(self)

        # names cane be found in
        display_lights = (("Use Default Lighting", "default"),
                          ("Use All Lights", "all"),
                          ("Use Selected Lights", "active"),
                          ("Use Flat Lighting", "flat"),
                          ("Use No Lights", "none"))

        for label, name in display_lights:
            menu.addItem(label, userData=name)

        return menu

    def on_toggle_override(self):
        """Enable or disable show menu when override is checked"""
        state = self.override_viewport.isChecked()
        self.show_types_button.setEnabled(state)
        self.high_quality.setEnabled(state)
        self.display_light_menu.setEnabled(state)
        self.shadows.setEnabled(state)
        self.two_sided_ligthing.setEnabled(state)

    def toggle_all_visbile(self):
        """Set all object types off or on depending on the state"""
        for action in self.show_type_actions:
            action.setChecked(True)

    def toggle_all_hide(self):
        """Set all object types off or on depending on the state"""
        for action in self.show_type_actions:
            action.setChecked(False)

    def get_show_inputs(self):
        """Return checked state of show menu items

        Returns:
            dict: The checked show states in the widget.

        """

        show_inputs = {}
        # get all checked objects
        for action in self.show_type_actions:
            label = action.text()
            name = self.show_types.get(label, None)
            if name is None:
                continue
            show_inputs[name] = action.isChecked()

        return show_inputs

    def get_displaylights(self):
        """Get and parse the currently selected displayLights options.

        Returns:
            dict: The display light options

        """
        indx = self.display_light_menu.currentIndex()
        return {"displayLights": self.display_light_menu.itemData(indx),
                "shadows": self.shadows.isChecked(),
                "twoSidedLighting": self.two_sided_ligthing.isChecked()}

    def get_inputs(self, as_preset):
        """Return the widget options

        Returns:
            dict: The input settings of the widgets.

        """
        inputs = {"high_quality": self.high_quality.isChecked(),
                  "override_viewport_options": self.override_viewport.isChecked(),
                  "displayLights": self.display_light_menu.currentIndex(),
                  "shadows": self.shadows.isChecked(),
                  "twoSidedLighting": self.two_sided_ligthing.isChecked()}

        inputs.update(self.get_show_inputs())

        return inputs

    def apply_inputs(self, inputs):
        """Apply the saved inputs from the inputs configuration

        Arguments:
            settings (dict): The input settings to apply.

        """

        # get input values directly from input given
        override_viewport = inputs.get("override_viewport_options", True)
        high_quality = inputs.get("high_quality", True)
        displaylight = inputs.get("displayLights", 0)   # default lighting
        two_sided_ligthing = inputs.get("twoSidedLighting", False)
        shadows = inputs.get("shadows", False)

        self.high_quality.setChecked(high_quality)
        self.override_viewport.setChecked(override_viewport)
        self.show_types_button.setEnabled(override_viewport)

        # display light menu
        self.display_light_menu.setCurrentIndex(displaylight)
        self.shadows.setChecked(shadows)
        self.two_sided_ligthing.setChecked(two_sided_ligthing)

        for action in self.show_type_actions:
            system_name = self.show_types[action.text()]
            state = inputs.get(system_name, True)
            action.setChecked(state)

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """
        outputs = dict()

        high_quality = self.high_quality.isChecked()
        override_viewport_options = self.override_viewport.isChecked()

        if override_viewport_options:
            outputs['viewport2_options'] = dict()
            outputs['viewport_options'] = dict()

            if high_quality:
                # force viewport 2.0 and AA
                outputs['viewport_options']['rendererName'] = 'vp2Renderer'
                outputs['viewport2_options']['multiSampleEnable'] = True
                outputs['viewport2_options']['multiSampleCount'] = 8

            show_per_type = self.get_show_inputs()
            display_lights = self.get_displaylights()
            outputs['viewport_options'].update(show_per_type)
            outputs['viewport_options'].update(display_lights)
        else:
            # TODO: When this fails we should give the user a warning
            # Use settings from the active viewport
            outputs = capture.parse_active_view()

            # Remove the display options and camera attributes
            outputs.pop("display_options", None)
            outputs.pop("camera", None)

            # Remove the current renderer because there's already
            # renderer plug-in handling that
            outputs["viewport_options"].pop("rendererName", None)

            # Remove all camera options except depth of field
            dof = outputs["camera_options"]["depthOfField"]
            outputs["camera_options"] = {"depthOfField": dof}

        return outputs
