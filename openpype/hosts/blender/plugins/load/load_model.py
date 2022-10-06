"""Load a model asset in Blender."""

from typing import Dict, Optional, Tuple, Union

import bpy

from openpype.hosts.blender.api import plugin


class LinkModelLoader(plugin.AssetLoader):
    """Link models from a .blend file."""

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_04"
    order = 0

    def _process(self, libpath, asset_group):
        self._link_blend(libpath, asset_group)


class AppendModelLoader(plugin.AssetLoader):
    """Append models from a .blend file."""

    families = ["model"]
    representations = ["blend"]

    label = "Append Model"
    icon = "paperclip"
    color = "orange"
    color_tag = "COLOR_04"
    order = 1

    def _process(self, libpath, asset_group):
        self._append_blend(libpath, asset_group)


class InstanceModelLoader(plugin.AssetLoader):
    """load models from a .blend file as instance collection."""

    families = ["model"]
    representations = ["blend"]

    label = "Instantiate Collection"
    icon = "archive"
    color = "orange"
    color_tag = "COLOR_04"
    order = 2

    def _apply_options(self, asset_group, options):
        """Apply load options fro asset_group."""

        transform = options.get("transform")
        parent = options.get("parent")

        if transform:
            location = transform.get("translation")
            rotation = transform.get("rotation")
            scale = transform.get("scale")

            asset_group.location = [location[n] for n in "xyz"]
            asset_group.rotation_euler = [rotation[n] for n in "xyz"]
            asset_group.scale = [scale[n] for n in "xyz"]

        if isinstance(parent, bpy.types.Object):
            with plugin.context_override(active=parent, selected=asset_group):
                bpy.ops.object.parent_set(keep_transform=True)
        elif isinstance(parent, bpy.types.Collection):
            for current_parent in asset_group.users_collection:
                current_parent.children.unlink(asset_group)
            plugin.link_to_collection(asset_group, parent)

    def _process(self, libpath, asset_group):
        container = self._load_library_collection(libpath)
        asset_group.instance_collection = container
        asset_group.instance_type = "COLLECTION"

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
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

        unique_number = plugin.get_unique_number(asset, subset)
        group_name = plugin.asset_name(asset, subset, unique_number)
        namespace = namespace or f"{asset}_{unique_number}"
        asset_group = bpy.data.objects.new(group_name, object_data=None)
        plugin.get_main_collection().objects.link(asset_group)

        self._process(libpath, asset_group)

        if options is not None:
            self._apply_options(asset_group, options)

        self._update_metadata(asset_group, context, namespace, libpath)

        self[:] = plugin.get_container_objects(asset_group)

        return asset_group

    def exec_switch(
        self, container: Dict, representation: Dict
    ) -> Tuple[Union[bpy.types.Collection, bpy.types.Object]]:
        """Switch the asset using update"""
        if container["loader"] != "InstanceModelLoader":
            raise NotImplementedError("Not implemented yet")

        asset_group = self.exec_update(container, representation)

        # Update namespace if needed

        return asset_group
