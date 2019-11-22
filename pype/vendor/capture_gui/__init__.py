from .vendor.Qt import QtWidgets
from . import app
from . import lib


def main(show=True):
    """Convenience method to run the Application inside Maya.

    Args:
        show (bool): Whether to directly show the instantiated application.
            Defaults to True. Set this to False if you want to manage the
            application (like callbacks) prior to showing the interface.

    Returns:
        capture_gui.app.App: The pyblish gui application instance.

    """
    # get main maya window to parent widget to
    parent = lib.get_maya_main_window()
    instance = parent.findChild(QtWidgets.QWidget, app.App.object_name)
    if instance:
        instance.close()

    # launch app
    window = app.App(title="Capture GUI", parent=parent)
    if show:
        window.show()

    return window
