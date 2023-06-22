import logging
import contextlib
import nuke

from qtpy import QtWidgets

log = logging.getLogger(__name__)


@contextlib.contextmanager
def viewer_update_and_undo_stop():
    """Lock viewer from updating and stop recording undo steps"""
    try:
        # stop active viewer to update any change
        viewer = nuke.activeViewer()
        if viewer:
            viewer.stop()
        else:
            log.warning("No available active Viewer")
        nuke.Undo.disable()
        yield
    finally:
        nuke.Undo.enable()


def is_headless():
    """
    Returns:
        bool: headless
    """
    return QtWidgets.QApplication.instance() is None
