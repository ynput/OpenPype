"""Load a model asset in Blender."""

from typing import Dict, List, Optional

import bpy

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin


class BlendModelLoader(plugin.AssetLoader):
    """Load models from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.
    """

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_04"

    _downstream_tasks = ("Rigging", "Modeling", "Texture", "Lookdev")

    def _load_blend(self, libpath, asset_group):
        # Load collections from libpath library.
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.collections = data_from.collections

        # Get the right asset container from imported collections.
        container = self._get_container_from_collections(
            data_to.collections, self.families
        )
        assert container, "No asset container found"

        if isinstance(asset_group, bpy.types.Collection):
            # Create override library for container and elements.
            override = container.override_hierarchy_create(
                bpy.context.scene, bpy.context.view_layer
            )
            # Force override object data like meshes and curves.
            overridden_data = set()
            for obj in set(override.all_objects):
                if obj.data and obj.data not in overridden_data:
                    obj.data.override_create(remap_local_usages=True)
                    overridden_data.add(obj.data)

            # Move objects and child collections from override to asset_group.
            plugin.link_to_collection(override.objects, asset_group)
            plugin.link_to_collection(override.children, asset_group)

            # Clear override container and assign objects variables.
            bpy.data.collections.remove(override)
            objects = list(asset_group.all_objects)

        # If asset_group is an Empty, set instance collection with container.
        elif isinstance(asset_group, bpy.types.Object):
            asset_group.instance_collection = container
            asset_group.instance_type = 'COLLECTION'
            objects = list(container.all_objects)

        # Purge useless datablocks and selection.
        plugin.orphans_purge()
        plugin.deselect_all()

        return objects

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

        # Get the main collection to parent asset group.
        parent_collection = plugin.get_main_collection()

        # Create override library if current task needed it.
        if (
            legacy_io.Session.get("AVALON_TASK") in self._downstream_tasks and
            legacy_io.Session.get("AVALON_ASSET") == asset
        ):
            group_name = plugin.asset_name(asset, subset)
            asset_group = bpy.data.collections.new(group_name)
            asset_group.color_tag = self.color_tag
            parent_collection.children.link(asset_group)
        else:
            unique_number = plugin.get_unique_number(asset, subset)
            group_name = plugin.asset_name(asset, subset, unique_number)
            namespace = namespace or f"{asset}_{unique_number}"
            asset_group = bpy.data.objects.new(group_name, object_data=None)
            asset_group.empty_display_type = 'SINGLE_ARROW'
            parent_collection.objects.link(asset_group)

            plugin.deselect_all()

            if options is not None:
                parent = options.get('parent')
                transform = options.get('transform')

                if parent and transform:
                    location = transform.get('translation')
                    rotation = transform.get('rotation')
                    scale = transform.get('scale')

                    asset_group.location = (
                        location.get('x'),
                        location.get('y'),
                        location.get('z')
                    )
                    asset_group.rotation_euler = (
                        rotation.get('x'),
                        rotation.get('y'),
                        rotation.get('z')
                    )
                    asset_group.scale = (
                        scale.get('x'),
                        scale.get('y'),
                        scale.get('z')
                    )

                    bpy.context.view_layer.objects.active = parent
                    asset_group.select_set(True)

                    bpy.ops.object.parent_set(keep_transform=True)

                    plugin.deselect_all()

        objects = self._load_blend(libpath, asset_group)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = objects
        return objects

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset"""
        self._update_blend(container, representation)

    def exec_remove(self, container) -> bool:
        """Remove the existing container from Blender scene"""
        return self._remove_container(container)
