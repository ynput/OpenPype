"""Load audio in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from openpype.pipeline import (
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)


class AudioLoader(plugin.AssetLoader):
    """Load audio in Blender."""

    families = ["audio"]
    representations = ["wav"]

    label = "Load Audio"
    icon = "volume-up"
    color = "orange"

    def process_asset(
        self, context: dict, name: str, namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Optional[List]:
        """
        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        asset_name = plugin.asset_name(asset, subset)
        unique_number = plugin.get_unique_number(asset, subset)
        group_name = plugin.asset_name(asset, subset, unique_number)
        namespace = namespace or f"{asset}_{unique_number}"

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        if not avalon_container:
            avalon_container = bpy.data.collections.new(name=AVALON_CONTAINERS)
            bpy.context.scene.collection.children.link(avalon_container)

        asset_group = bpy.data.objects.new(group_name, object_data=None)
        avalon_container.objects.link(asset_group)

        # Blender needs the Sequence Editor in the current window, to be able
        # to load the audio. We take one of the areas in the window, save its
        # type, and switch to the Sequence Editor. After loading the audio,
        # we switch back to the previous area.
        window_manager = bpy.context.window_manager
        old_type = window_manager.windows[-1].screen.areas[0].type
        window_manager.windows[-1].screen.areas[0].type = "SEQUENCE_EDITOR"

        # We override the context to load the audio in the sequence editor.
        oc = bpy.context.copy()
        oc["area"] = window_manager.windows[-1].screen.areas[0]

        bpy.ops.sequencer.sound_strip_add(oc, filepath=libpath, frame_start=1)

        window_manager.windows[-1].screen.areas[0].type = old_type

        p = Path(libpath)
        audio = p.name

        asset_group[AVALON_PROPERTY] = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "name": name,
            "namespace": namespace or '',
            "loader": str(self.__class__.__name__),
            "representation": str(context["representation"]["_id"]),
            "libpath": libpath,
            "asset_name": asset_name,
            "parent": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"],
            "objectName": group_name,
            "audio": audio
        }

        objects = []
        self[:] = objects
        return [objects]

    def exec_update(self, container: Dict, representation: Dict):
        """Update an audio strip in the sequence editor.

        Arguments:
            container (openpype:container-1.0): Container to update,
                from `host.ls()`.
            representation (openpype:representation-1.0): Representation to
                update, from `host.ls()`.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = Path(get_representation_path(representation))

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert asset_group, (
            f"The asset is not loaded: {container['objectName']}"
        )
        assert libpath, (
            "No existing library file found for {container['objectName']}"
        )
        assert libpath.is_file(), (
            f"The file doesn't exist: {libpath}"
        )

        metadata = asset_group.get(AVALON_PROPERTY)
        group_libpath = metadata["libpath"]

        normalized_group_libpath = (
            str(Path(bpy.path.abspath(group_libpath)).resolve())
        )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        self.log.debug(
            "normalized_group_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_group_libpath,
            normalized_libpath,
        )
        if normalized_group_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        old_audio = container["audio"]
        p = Path(libpath)
        new_audio = p.name

        # Blender needs the Sequence Editor in the current window, to be able
        # to update the audio. We take one of the areas in the window, save its
        # type, and switch to the Sequence Editor. After updating the audio,
        # we switch back to the previous area.
        window_manager = bpy.context.window_manager
        old_type = window_manager.windows[-1].screen.areas[0].type
        window_manager.windows[-1].screen.areas[0].type = "SEQUENCE_EDITOR"

        # We override the context to load the audio in the sequence editor.
        oc = bpy.context.copy()
        oc["area"] = window_manager.windows[-1].screen.areas[0]

        # We deselect all sequencer strips, and then select the one we
        # need to remove.
        bpy.ops.sequencer.select_all(oc, action='DESELECT')
        scene = bpy.context.scene
        scene.sequence_editor.sequences_all[old_audio].select = True

        bpy.ops.sequencer.delete(oc)
        bpy.data.sounds.remove(bpy.data.sounds[old_audio])

        bpy.ops.sequencer.sound_strip_add(
            oc, filepath=str(libpath), frame_start=1)

        window_manager.windows[-1].screen.areas[0].type = old_type

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])
        metadata["parent"] = str(representation["parent"])
        metadata["audio"] = new_audio

    def exec_remove(self, container: Dict) -> bool:
        """Remove an audio strip from the sequence editor and the container.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)

        if not asset_group:
            return False

        audio = container["audio"]

        # Blender needs the Sequence Editor in the current window, to be able
        # to remove the audio. We take one of the areas in the window, save its
        # type, and switch to the Sequence Editor. After removing the audio,
        # we switch back to the previous area.
        window_manager = bpy.context.window_manager
        old_type = window_manager.windows[-1].screen.areas[0].type
        window_manager.windows[-1].screen.areas[0].type = "SEQUENCE_EDITOR"

        # We override the context to load the audio in the sequence editor.
        oc = bpy.context.copy()
        oc["area"] = window_manager.windows[-1].screen.areas[0]

        # We deselect all sequencer strips, and then select the one we
        # need to remove.
        bpy.ops.sequencer.select_all(oc, action='DESELECT')
        bpy.context.scene.sequence_editor.sequences_all[audio].select = True

        bpy.ops.sequencer.delete(oc)

        window_manager.windows[-1].screen.areas[0].type = old_type

        bpy.data.sounds.remove(bpy.data.sounds[audio])

        bpy.data.objects.remove(asset_group)

        return True
