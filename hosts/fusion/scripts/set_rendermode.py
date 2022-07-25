from Qt import QtWidgets
import qtawesome
from openpype.hosts.fusion.api import get_current_comp


_help = {"local": "Render the comp on your own machine and publish "
                  "it from that the destination folder",
         "farm": "Submit a Fusion render job to a Render farm to use all other"
                 " computers and add a publish job"}


class SetRenderMode(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self._comp = get_current_comp()
        self._comp_name = self._get_comp_name()

        self.setWindowTitle("Set Render Mode")
        self.setFixedSize(300, 175)

        layout = QtWidgets.QVBoxLayout()

        # region comp info
        comp_info_layout = QtWidgets.QHBoxLayout()

        update_btn = QtWidgets.QPushButton(qtawesome.icon("fa.refresh",
                                                          color="white"), "")
        update_btn.setFixedWidth(25)
        update_btn.setFixedHeight(25)

        comp_information = QtWidgets.QLineEdit()
        comp_information.setEnabled(False)

        comp_info_layout.addWidget(comp_information)
        comp_info_layout.addWidget(update_btn)
        # endregion comp info

        # region modes
        mode_options = QtWidgets.QComboBox()
        mode_options.addItems(_help.keys())

        mode_information = QtWidgets.QTextEdit()
        mode_information.setReadOnly(True)
        # endregion modes

        accept_btn = QtWidgets.QPushButton("Accept")

        layout.addLayout(comp_info_layout)
        layout.addWidget(mode_options)
        layout.addWidget(mode_information)
        layout.addWidget(accept_btn)

        self.setLayout(layout)

        self.comp_information = comp_information
        self.update_btn = update_btn

        self.mode_options = mode_options
        self.mode_information = mode_information

        self.accept_btn = accept_btn

        self.connections()
        self.update()

        # Force updated render mode help text
        self._update_rendermode_info()

    def connections(self):
        """Build connections between code and buttons"""

        self.update_btn.clicked.connect(self.update)
        self.accept_btn.clicked.connect(self._set_comp_rendermode)
        self.mode_options.currentIndexChanged.connect(
            self._update_rendermode_info)

    def update(self):
        """Update all information in the UI"""

        self._comp = get_current_comp()
        self._comp_name = self._get_comp_name()
        self.comp_information.setText(self._comp_name)

        # Update current comp settings
        mode = self._get_comp_rendermode()
        index = self.mode_options.findText(mode)
        self.mode_options.setCurrentIndex(index)

    def _update_rendermode_info(self):
        rendermode = self.mode_options.currentText()
        self.mode_information.setText(_help[rendermode])

    def _get_comp_name(self):
        return self._comp.GetAttrs("COMPS_Name")

    def _get_comp_rendermode(self):
        return self._comp.GetData("openpype.rendermode") or "local"

    def _set_comp_rendermode(self):
        rendermode = self.mode_options.currentText()
        self._comp.SetData("openpype.rendermode", rendermode)

        self._comp.Print("Updated render mode to '%s'\n" % rendermode)
        self.hide()

    def _validation(self):
        ui_mode = self.mode_options.currentText()
        comp_mode = self._get_comp_rendermode()

        return comp_mode == ui_mode
