import sys
import contextlib
import re
import nuke
from PySide2 import QtCore, QtWidgets


def get_main_window():
    """Acquire Nuke's main window"""
    main_window = None
    if main_window is None:

        top_widgets = QtWidgets.QApplication.topLevelWidgets()
        name = "Foundry::UI::DockMainWindow"
        for widget in top_widgets:
            if (
                widget.inherits("QMainWindow")
                and widget.metaObject().className() == name
            ):
                main_window = widget
                break
    return main_window

class CustomScriptDialog(QtWidgets.QDialog):
    """A Popup that moves itself to bottom right of screen on show event.

    The UI contains a message label and a red highlighted button to "show"
    or perform another custom action from this pop-up.

    """

    on_clicked = QtCore.Signal()
    on_line_changed = QtCore.Signal(str)
    context = None



    def __init__(self, parent=None, *args, **kwargs):
        super(CustomScriptDialog, self).__init__(parent=parent,
                                                 *args,
                                                 **kwargs)
        self.setContentsMargins(0, 0, 0, 0)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        frame_layout = QtWidgets.QHBoxLayout()
        frame_layout.setContentsMargins(10, 5, 10, 10)
        selection_layout = QtWidgets.QHBoxLayout()
        selection_layout.setContentsMargins(10, 5, 10, 10)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(10, 5, 10, 10)

        # Increase spacing slightly for readability
        frame_layout.setSpacing(10)
        button_layout.setSpacing(10)
        name = QtWidgets.QLabel("Frame Range: ")
        name.setStyleSheet("""
        QLabel {
            font-size: 12px;
        }
        """)
        line_edit = QtWidgets.QLineEdit(
            "%s-%s" % (nuke.root().firstFrame(),
                       nuke.root().lastFrame()))
        selection_name = QtWidgets.QLabel("Use Selection")
        selection_name.setStyleSheet("""
        QLabel {
            font-size: 12px;
        }
        """)
        has_selection = QtWidgets.QCheckBox()
        button = QtWidgets.QPushButton("Execute")
        button.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                             QtWidgets.QSizePolicy.Maximum)
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                             QtWidgets.QSizePolicy.Maximum)

        frame_layout.addWidget(name)
        frame_layout.addWidget(line_edit)
        selection_layout.addWidget(selection_name)
        selection_layout.addWidget(has_selection)
        button_layout.addWidget(button)
        button_layout.addWidget(cancel)
        layout.addLayout(frame_layout)
        layout.addLayout(selection_layout)
        layout.addLayout(button_layout)
        # Default size
        self.resize(100, 40)

        self.widgets = {
            "name": name,
            "line_edit": line_edit,
            "selection": has_selection,
            "button": button,
            "cancel": cancel
        }
        # Signals
        has_selection.toggled.connect(self.emit_click_with_state)
        line_edit.textChanged.connect(self.on_line_edit_changed)
        button.clicked.connect(self._on_clicked)
        cancel.clicked.connect(self.close)
        self.update_values()
        # Set default title
        self.setWindowTitle("Custom Popup")

    def update_values(self):
        self.widgets["selection"].isChecked()

    def emit_click_with_state(self):
        """Emit the on_clicked signal with the toggled state"""
        checked = self.widgets["selection"].isChecked()
        return checked

    def set_name(self, name):
        self.widgets['name'].setText(name)

    def set_line_edit(self, line_edit):
        self.widgets['line_edit'].setText(line_edit)
        print(line_edit)

    def setButtonText(self, text):
        self.widgets["button"].setText(text)

    def setCancelText(self, text):
        self.widgets["cancel"].setText(text)

    def on_line_edit_changed(self):
        line_edit = self.widgets['line_edit'].text()
        self.on_line_changed.emit(line_edit)
        return self.set_line_edit(line_edit)

    def _on_clicked(self):
        """Callback for when the 'show' button is clicked.

        Raises the parent (if any)

        """
        frame_range = self.widgets['line_edit'].text()
        selected = self.widgets["selection"].isChecked()
        pattern = r"^(?P<start>-?[0-9]+)(?:(?:-+)(?P<end>-?[0-9]+))?$"
        match = re.match(pattern, frame_range)
        frame_start = int(match.group("start"))
        frame_end = int(match.group("end"))
        if not nuke.allNodes("Read"):
            return
        for read_node in nuke.allNodes("Read"):
            if selected:
                if not nuke.selectedNodes():
                    return
                if read_node in nuke.selectedNodes():
                    read_node["frame_mode"].setValue("start_at")
                    read_node["frame"].setValue(frame_range)
                    read_node["first"].setValue(frame_start)
                    read_node["last"].setValue(frame_end)
            else:
                read_node["frame_mode"].setValue("start_at")
                read_node["frame"].setValue(frame_range)
                read_node["first"].setValue(frame_start)
                read_node["last"].setValue(frame_end)

        self.close()

        return False

    def showEvent(self, event):
        # Position popup based on contents on show event
        return super(CustomScriptDialog, self).showEvent(event)


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication(sys.argv)
    yield
    app.exec_()


if __name__ == "__main__":
    with application():
        dialog = CustomScriptDialog()
        dialog.show()
