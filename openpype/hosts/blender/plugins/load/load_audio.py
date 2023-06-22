"""Load audio in Blender."""

from pathlib import Path
from typing import Dict, List, Set, Tuple

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.properties import OpenpypeContainer
from openpype.hosts.blender.api.utils import AVALON_PROPERTY


class AudioLoader(plugin.AssetLoader):
    """Load audio in Blender."""

    families = ["audio"]
    representations = ["wav"]

    label = "Load Audio"
    icon = "volume-up"
    color = "orange"

    load_type = "APPEND"  # TODO meaningless here, must be refactored

    def _load_library_datablocks(
        self,
        libpath: Path,
        container_name: str,
        container: OpenpypeContainer = None,
        **_kwargs
    ) -> Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
        """OVERRIDE Load datablocks from blend file library.

        Args:
            libpath (Path): Path of library.
            container_name (str): Name of container to be loaded.
            container (OpenpypeContainer): Load into existing container.
                Defaults to None.

        Returns:
            Tuple[OpenpypeContainer, Set[bpy.types.ID]]:
                (Created scene container, Loaded datablocks)
        """

        # Append audio as sound in the sequence editor
        sound_seq = bpy.context.scene.sequence_editor.sequences.new_sound(
            container_name,
            libpath.as_posix(),
            1,
            bpy.context.scene.frame_start,
        )

        # Put into a container
        datablocks = [sound_seq.sound]
        container = self._containerize_datablocks(
            container_name, datablocks, container
        )

        # Keep audio sequence in the container
        container["sequence_name"] = sound_seq.name

        return container, datablocks

    def load(self, *args, **kwargs):
        """OVERRIDE.

        Keep container metadata in sound datablock to allow container
        auto creation of theses datablocks.
        """
        container, datablocks = super().load(*args, **kwargs)

        # Set container metadata to sound datablock
        datablocks[0][AVALON_PROPERTY] = container.get(AVALON_PROPERTY)

        return container, datablocks

    def update(
        self, *args, **kwargs
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """OVERRIDE Update an existing container from a Blender scene."""
        self.switch(*args, **kwargs)

    def switch(
        self, container_metadata: Dict, representation: Dict
    ) -> Tuple[OpenpypeContainer, List[bpy.types.ID]]:
        """OVERRIDE Switch an existing container from a Blender scene."""
        # Remove audio sequence
        self._remove_audio_sequence(container_metadata)

        container, datablocks = super().update(
            container_metadata, representation
        )

        # Set container metadata to sound datablock
        sound = datablocks[0]
        sound[AVALON_PROPERTY] = container.get(AVALON_PROPERTY)

        return container, datablocks

    def remove(self, container: Dict) -> bool:
        """OVERRIDE Remove an existing container from a Blender scene."""
        # Remove audio sequence
        self._remove_audio_sequence(container)

        return super().remove(container)

    def _remove_audio_sequence(self, container_metadata: Dict):
        """Remove audio sequence from the sequence editor

        Args:
            container (Dict): Container OpenPype metadata
        """
        container_metadata = self._get_scene_container(container_metadata)
        sound_seq = bpy.context.scene.sequence_editor.sequences.get(
            container_metadata["sequence_name"]
        )
        if sound_seq:
            bpy.context.scene.sequence_editor.sequences.remove(sound_seq)
