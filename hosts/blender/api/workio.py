"""Host API required for Work Files."""

from pathlib import Path
from typing import List, Optional

import bpy

from openpype.pipeline import HOST_WORKFILE_EXTENSIONS


class OpenFileCacher:
    """Store information about opening file.

    When file is opening QApplcation events should not be processed.
    """
    opening_file = False

    @classmethod
    def post_load(cls):
        cls.opening_file = False

    @classmethod
    def set_opening(cls):
        cls.opening_file = True


def open_file(filepath: str) -> Optional[str]:
    """Open the scene file in Blender."""
    OpenFileCacher.set_opening()

    preferences = bpy.context.preferences
    load_ui = preferences.filepaths.use_load_ui
    use_scripts = preferences.filepaths.use_scripts_auto_execute
    result = bpy.ops.wm.open_mainfile(
        filepath=filepath,
        load_ui=load_ui,
        use_scripts=use_scripts,
    )

    if result == {'FINISHED'}:
        return filepath
    return None


def save_file(filepath: str, copy: bool = False) -> Optional[str]:
    """Save the open scene file."""

    preferences = bpy.context.preferences
    compress = preferences.filepaths.use_file_compression
    relative_remap = preferences.filepaths.use_relative_paths
    result = bpy.ops.wm.save_as_mainfile(
        filepath=filepath,
        compress=compress,
        relative_remap=relative_remap,
        copy=copy,
    )

    if result == {'FINISHED'}:
        return filepath
    return None


def current_file() -> Optional[str]:
    """Return the path of the open scene file."""

    current_filepath = bpy.data.filepath
    if Path(current_filepath).is_file():
        return current_filepath
    return None


def has_unsaved_changes() -> bool:
    """Does the open scene file have unsaved changes?"""

    return bpy.data.is_dirty


def file_extensions() -> List[str]:
    """Return the supported file extensions for Blender scene files."""

    return HOST_WORKFILE_EXTENSIONS["blender"]


def work_root(session: dict) -> str:
    """Return the default root to browse for work files."""

    work_dir = session["AVALON_WORKDIR"]
    scene_dir = session.get("AVALON_SCENEDIR")
    if scene_dir:
        return str(Path(work_dir, scene_dir))
    return work_dir
