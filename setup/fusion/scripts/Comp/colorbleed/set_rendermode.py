import os

from avalon.vendor.Qt import QtCore, QtWidgets
from avalon.vendor import qtawesome
import avalon.fusion as avalon


_help = {"renderlocal": "Render the comp on your own machine and publish "
                        "it from that the destination folder",
         "deadline": "Submit a Fusion render job to Deadline to use all other "
                     "computers and add a publish job"}


class SetRenderMode(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self._comp = avalon.get_current_comp()
        self._comp_name = self._get_comp_name()

        self.setWindowTitle("Set Render Mode - {}".format(self._comp_name))
        self.resize(300, 150)
        self.setFixedSize(300, 150)

        layout = QtWidgets.QVBoxLayout()

        # region comp info
        comp_info_layout = QtWidgets.QHBoxLayout()

        update_btn = QtWidgets.QPushButton(qtawesome.icon("fa.refresh"), "")
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
        mode_information.setEnabled(False)
        # endregion modes

        accept_layout = QtWidgets.QHBoxLayout()
        accept_btn = QtWidgets.QPushButton("Accept")
        validation_state = QtWidgets.QPushButton()
        validation_state.setFixedHeight(15)
        validation_state.setFixedWidth(15)
        validation_state.setEnabled(False)
        validation_state.setStyleSheet("background-color: green")

        accept_layout.addWidget(accept_btn)
        accept_layout.addWidget(validation_state)

        layout.addLayout(comp_info_layout)
        layout.addWidget(mode_options)
        layout.addWidget(mode_information)
        layout.addLayout(accept_layout)

        self.setLayout(layout)

        self.comp_information = comp_information
        self.update_btn = update_btn

        self.mode_options = mode_options
        self.mode_information = mode_information

        self.accept_btn = accept_btn
        self.validation = validation_state

        self.connections()
        self.update()

    def connections(self):
        """Build connections between code and buttons"""

        self.update_btn.clicked.connect(self.update)
        self.accept_btn.clicked.connect(self._set_comp_rendermode)
        self.mode_options.currentIndexChanged.connect(
            self._update_rendermode_info)

    def update(self):
        """Update all information in the UI"""

        self._comp = avalon.get_current_comp()
        self._comp_name = self._get_comp_name()

        self.setWindowTitle("Set Render Mode")
        self.comp_information.setText(self._comp_name)

        self._update_rendermode_info()

    def _update_rendermode_info(self):

        rendermode = self._get_comp_rendermode()
        if rendermode is None:
            rendermode = "renderlocal"

        self.mode_information.setText(_help[rendermode])

    def _get_comp_name(self):
        return os.path.basename(self._comp.GetAttrs("COMPS_FileName"))

    def _get_comp_rendermode(self):
        return self._comp.GetData("colorbleed.rendermode")

    def _set_comp_rendermode(self):
        rendermode = self.mode_options.currentText()
        self._comp.SetData("colorbleed.rendermode", rendermode)

        # Validate the rendermode has been updated correctly
        if not self._validation():
            self.validation.setStyleSheet("background-color: red")
            raise AssertionError("Rendermode in UI is not render mode in comp: "
                                 "%s" % self._comp_name)

        print("Updated render mode for %s to %s" % (self._comp_name, rendermode))

    def _validation(self):
        ui_mode = self.mode_options.currentText()
        comp_mode = self._get_comp_rendermode()

        return comp_mode == ui_mode


if __name__ == '__main__':

    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = SetRenderMode()
    w.show()
    sys.exit(app.exec_())
