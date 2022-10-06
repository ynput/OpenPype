"""Load audio in Blender."""

from pathlib import Path
from typing import Dict, Tuple, Union

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class AudioLoader(plugin.AssetLoader):
    """Load audio in Blender."""

    families = ["audio"]
    representations = ["wav"]

    label = "Load Audio"
    icon = "volume-up"
    color = "orange"
    color_tag = "COLOR_02"

    def _remove_audio(self, audio):
        # Blender needs the Sequence Editor in the current window, to be able
        # to remove the audio. We take one of the areas in the window, save its
        # type, and switch to the Sequence Editor. After removing the audio,
        # we switch back to the previous area.
        window_manager = bpy.context.window_manager
        old_type = window_manager.windows[-1].screen.areas[0].type
        window_manager.windows[-1].screen.areas[0].type = "SEQUENCE_EDITOR"

        # We override the context to load the audio in the sequence editor.
        context = bpy.context.copy()
        context["area"] = window_manager.windows[-1].screen.areas[0]

        # We deselect all sequencer strips, and then select the one we
        # need to remove.
        bpy.ops.sequencer.select_all(context, action="DESELECT")
        bpy.context.scene.sequence_editor.sequences_all[audio].select = True

        bpy.ops.sequencer.delete(context)

        window_manager.windows[-1].screen.areas[0].type = old_type

        bpy.data.sounds.remove(bpy.data.sounds[audio])

    def _process(self, libpath, asset_group):
        # Blender needs the Sequence Editor in the current window, to be able
        # to load the audio. We take one of the areas in the window, save its
        # type, and switch to the Sequence Editor. After loading the audio,
        # we switch back to the previous area.
        window_manager = bpy.context.window_manager
        old_type = window_manager.windows[-1].screen.areas[0].type
        window_manager.windows[-1].screen.areas[0].type = "SEQUENCE_EDITOR"

        # We override the context to load the audio in the sequence editor.
        context = bpy.context.copy()
        context["area"] = window_manager.windows[-1].screen.areas[0]

        bpy.ops.sequencer.sound_strip_add(
            context, filepath=libpath, frame_start=1
        )

        window_manager.windows[-1].screen.areas[0].type = old_type

    def process_asset(*args, **kwargs) -> bpy.types.Collection:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        asset_group = super().process_asset(*args, **kwargs)

        libpath = Path(asset_group[AVALON_PROPERTY]["libpath"])
        asset_group[AVALON_PROPERTY]["audio"] = libpath.name

        return asset_group

    def exec_update(
        self, container: Dict, representation: Dict
    ) -> Tuple[str, Union[bpy.types.Collection, bpy.types.Object]]:
        """Update the loaded asset"""

        self._remove_audio(container["audio"])

        libpath, asset_group = super().exec_update(container, representation)

        asset_group[AVALON_PROPERTY]["audio"] = libpath.name

        return libpath, asset_group

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene."""
        self._remove_audio(container["audio"])
        return super().exec_remove(container)
