import logging
import contextlib
import nuke

from avalon import io


log = logging.getLogger(__name__)


def reset_resolution():
    """Set resolution to project resolution."""
    project = io.find_one({"type": "project"})
    p_data = project["data"]

    width = p_data.get("resolution_width",
                       p_data.get("resolutionWidth"))
    height = p_data.get("resolution_height",
                        p_data.get("resolutionHeight"))

    if not all([width, height]):
        missing = ", ".join(["width", "height"])
        msg = "No resolution information `{0}` found for '{1}'.".format(
            missing,
            project["name"])
        log.warning(msg)
        nuke.message(msg)
        return

    current_width = nuke.root()["format"].value().width()
    current_height = nuke.root()["format"].value().height()

    if width != current_width or height != current_height:

        fmt = None
        for f in nuke.formats():
            if f.width() == width and f.height() == height:
                fmt = f.name()

        if not fmt:
            nuke.addFormat(
                "{0} {1} {2}".format(int(width), int(height), project["name"])
            )
            fmt = project["name"]

        nuke.root()["format"].setValue(fmt)


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
