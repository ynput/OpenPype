import os

from openpype.settings import get_project_settings
from openpype.pipeline import Anatomy
from openpype.hosts.unreal.api.pipeline import (
    send_request,
)
from openpype.widgets.message_window import Window


def start_rendering():
    """
    Start the rendering process.
    """

    # Get selected sequences
    selection = send_request("get_selected_assets")

    if not selection:
        Window(
            parent=None,
            title="No assets selected",
            message="No assets selected. Select a render instance.",
            level="warning")
        raise RuntimeError(
            "No assets selected. You need to select a render instance.")

    try:
        project = os.environ.get("AVALON_PROJECT")
        anatomy = Anatomy(project)
        root = anatomy.roots['renders']
    except Exception as e:
        raise RuntimeError(
            "Could not find render root in anatomy settings.") from e

    render_dir = f"{root}/{project}"

    data = get_project_settings(project)
    config_path = data.get("unreal").get("render_config_path")
    render_format = data.get("unreal").get("render_format", "png")
    preroll_frames = data.get("unreal").get("preroll_frames", 0)

    send_request(
        "start_rendering",
        params={
            "selection": selection,
            "render_dir": render_dir,
            "config_path": config_path,
            "render_format": render_format,
            "preroll_frames": preroll_frames})
