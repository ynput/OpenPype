"""Load a model asset in Blender."""

from typing import Dict, Optional, Union

import bpy

from openpype.pipeline import legacy_io
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import MODEL_DOWNSTREAM


class BlendModelLoader(plugin.AssetLoader):
    """Load models from a .blend file."""

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_04"

    def _apply_options(self, asset_group, options):
        """Apply load options fro asset_group."""

        transform = options.get("transform")
        parent = options.get("parent")

        if isinstance(asset_group, bpy.types.Object):
            if transform:
                location = transform.get("translation")
                rotation = transform.get("rotation")
                scale = transform.get("scale")

                asset_group.location = [location[n] for n in "xyz"]
                asset_group.rotation_euler = [rotation[n] for n in "xyz"]
                asset_group.scale = [scale[n] for n in "xyz"]

            if isinstance(parent, bpy.types.Object):
                bpy.ops.object.parent_set(
                    plugin.create_blender_context(
                        active=bpy.context.scene.objects.get(parent),
                        selected=[asset_group]
                    ),
                    keep_transform=True
                )
            elif isinstance(parent, bpy.types.Collection):
                for current_parent in asset_group.users_collection:
                    current_parent.children.unlink(asset_group)
                plugin.link_to_collection(asset_group, parent)

        elif (
            isinstance(asset_group, bpy.types.Collection)
            and isinstance(parent, bpy.types.Collection)
        ):
            # clear collection parenting
            for collection in bpy.data.collections:
                if asset_group in collection.children.values():
                    collection.children.unlink(asset_group)
            # reparenting with the option value
            plugin.link_to_collection(asset_group, parent)

    def _process(self, libpath, asset_group):

        # If asset_group is a Collection, we proceed with usual load blend.
        if isinstance(asset_group, bpy.types.Collection):
            self._load_blend(libpath, asset_group)

        # If asset_group is an Empty, set instance collection with container.
        elif isinstance(asset_group, bpy.types.Object):
            container = self._load_library_collection(libpath)
            asset_group.instance_collection = container
            asset_group.instance_type = "COLLECTION"

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Union[bpy.types.Object, bpy.types.Collection]:
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
        if legacy_io.Session.get("AVALON_TASK") in MODEL_DOWNSTREAM:
            group_name = plugin.asset_name(asset, subset)
            namespace = None
            asset_group = bpy.data.collections.new(group_name)
            if hasattr(asset_group, "color_tag"):
                asset_group.color_tag = self.color_tag
            parent_collection.children.link(asset_group)
        else:
            unique_number = plugin.get_unique_number(asset, subset)
            group_name = plugin.asset_name(asset, subset, unique_number)
            namespace = namespace or f"{asset}_{unique_number}"
            asset_group = bpy.data.objects.new(group_name, object_data=None)
            parent_collection.objects.link(asset_group)

        self._process(libpath, asset_group)

        if options is not None:
            self._apply_options(asset_group, options)

        self._update_metadata(
            asset_group, context, name, namespace, asset_name, libpath
        )

        self[:] = plugin.get_container_objects(asset_group)

        return asset_group
