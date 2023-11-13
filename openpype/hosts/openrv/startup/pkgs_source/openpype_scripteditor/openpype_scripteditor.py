import rv.commands
import rv.qtutils
from rv.rvtypes import MinorMode

from qtpy import QtCore

# On OpenPype installation it moves `openpype.modules` entries into
# `openpype_modules`. However, if OpenPype installation has not triggered yet.
# For example when the openpype_menus RV package hasn't loaded then the move
# of that package hasn't happened. So we'll allow both ways to import to ensure
# it is found
try:
    from openpype_modules.python_console_interpreter.window import PythonInterpreterWidget  # noqa
except ModuleNotFoundError:
    from openpype.modules.python_console_interpreter.window import PythonInterpreterWidget  # noqa


class OpenPypeMenus(MinorMode):

    def __init__(self):
        MinorMode.__init__(self)
        self.init(
            name="py-openpype-scripteditor",
            globalBindings=None,
            overrideBindings=None,
            menu=[
                # Menu name
                # NOTE: If it already exists it will merge with existing
                # and add submenus / menuitems to the existing one
                ("Tools", [
                    # Menuitem name, actionHook (event), key, stateHook
                    (
                        "Script Editor",
                        self.show_scripteditor,
                        None,
                        self.is_active
                    ),
                ])
            ],
            # initialization order
            sortKey="source_setup",
            ordering=25
        )

        self._widget = None

    @property
    def _parent(self):
        return rv.qtutils.sessionWindow()

    def show_scripteditor(self, event):
        """Show the console - create if not exists"""
        if self._widget is not None:
            if self._widget.isVisible():
                # Closing also saves the scripts directly.
                # Thus we prefer to close instead of hide here
                self._widget.close()
                return
            else:
                self._widget.show()
                self._widget.raise_()
                return

        widget = PythonInterpreterWidget(parent=self._parent)
        widget.setWindowTitle("Python Script Editor - OpenRV")
        widget.setWindowFlags(widget.windowFlags() |
                              QtCore.Qt.Dialog |
                              QtCore.Qt.WindowMinimizeButtonHint)
        widget.show()
        widget.raise_()

        self._widget = widget

    def is_active(self):
        if self._widget is not None and self._widget.isVisible():
            return rv.commands.CheckedMenuState
        else:
            return rv.commands.UncheckedMenuState


def createMode():
    return OpenPypeMenus()
