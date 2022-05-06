"""Load an animation in Blender."""

from typing import Dict, List, Optional

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class BlendAnimationLoader(plugin.AssetLoader):
    """Load animations from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["animation"]
    representations = ["blend"]

    label = "Link Animation"
    icon = "code-fork"
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

        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.collections = data_from.collections
            data_to.actions = data_from.actions

        container = None

        # get valid container from loaded collections
        for collection in data_to.collections:
            collection_metadata = collection.get(AVALON_PROPERTY)
            if (
                collection_metadata and
                collection_metadata.get("family") == "animation"
            ):
                container = collection
                break

        assert container, "No asset container found"
        assert data_to.actions, "No actions found"

        target_namespace = container.get(AVALON_PROPERTY).get('namespace')

        action = data_to.actions[0].make_local().copy()

        for collection in bpy.data.collections:
            metadata = collection.get(AVALON_PROPERTY)
            if (
                metadata and
                metadata.get('namespace') == target_namespace
            ):
                for obj in collection.all_objects:
                    if not obj.animation_data:
                        obj.animation_data_create()
                    obj.animation_data.action = action

        plugin.remove_container(container)

        library = bpy.data.libraries.get(bpy.path.basename(libpath))
        bpy.data.libraries.remove(library)

        plugin.orphans_purge()
