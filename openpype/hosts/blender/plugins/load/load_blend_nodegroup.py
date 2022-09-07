"""Load and assign extracted nodegroups."""

from typing import Dict, Optional, Union

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY
from openpype.pipeline import legacy_io


class LinkBlenderNodegroupLoader(plugin.AssetLoader):
    """Link nodegroups with source collection from a .blend file."""

    families = ["blender.nodegroup"]
    representations = ["blend"]

    label = "Link Nodegroup with reference"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_06"
    order = 0

    def _process(self, libpath, asset_group):
        self._link_blend(libpath, asset_group)


class AppendBlenderNodegroupLoader(plugin.AssetLoader):
    """Append nodegroups with source collection from a .blend file."""

    families = ["blender.nodegroup"]
    representations = ["blend"]

    label = "Append Nodegroup with reference"
    icon = "paperclip"
    color = "orange"
    color_tag = "COLOR_06"
    order = 2

    def _process(self, libpath, asset_group):
        self._append_blend(libpath, asset_group)


class OnlyDataLoader(plugin.AssetLoader):
    """Intermediate class for loading only data blocks without source objects."""

    representations = ["blend"]
    link: bool

    def process_asset(
        self,
        context: dict,
        name: str,
        namespace: Optional[str] = None,
        options: Optional[Dict] = None,
    ) -> bpy.types.Collection:
        """[OVERRIDE].

        Arguments:
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            context: Full parenthood of representation to load
            options: Additional settings dictionary
        """
        libpath = self.fname
        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        # TODO Make it a common function with plugin
        if self.no_namespace or legacy_io.Session.get("AVALON_ASSET") == asset:
            group_name = plugin.asset_name(asset, subset)
            namespace = ""
        else:
            unique_number = plugin.get_unique_number(asset, subset)
            group_name = plugin.asset_name(asset, subset, unique_number)
            namespace = namespace or f"{asset}_{unique_number}"

        # Create backdrop collection
        scene = bpy.context.scene
        backdrop_instance = scene.backdrop_op_instances.add()
        backdrop_instance.name = f"{asset}_{subset}"
        backdrop_instance[AVALON_PROPERTY] = {}

        backdrop_instance["children"] = self._load_node_groups(
            libpath, link=True
        )

        self._update_metadata(backdrop_instance, context, namespace, libpath)

        return backdrop_instance

    def _process(self, libpath, asset_group):
        # Load node groups and keep them
        asset_group["children"] = self._load_node_groups(
            libpath, link=self.link
        )

    def _update_process(
        self, container: Dict, representation: Dict
    ) -> Union[bpy.types.Collection, bpy.types.Object]:
        """[OVERRIDE] Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        """
        # Keep used nodegroups in modifiers
        modifiers_users = {}
        for o in bpy.data.objects:
            modifiers_users.update(
                {
                    m.node_group.name: m
                    for m in o.modifiers
                    if m.type == "NODES"
                }
            )

        super()._update_process(container, representation)

        # Set nodegroups back in modifiers
        for n in bpy.data.node_groups:
            modifier = modifiers_users.get(n.name)
            if modifier:
                modifier.node_group = n

    def _remove_container(self, container: Dict) -> bool:
        """[OVERRIDE] Remove an existing container from a Blender scene.

        Arguments:
            container: Container to remove.

        Returns:
            Whether the container was deleted.
        """

        super()._remove_container(container)

        # Remove node group
        instance_index = bpy.context.scene.backdrop_op_instances.find(
            container["objectName"]
        )
        backdrop_instance = bpy.context.scene.backdrop_op_instances[
            instance_index
        ]
        for child in [c for c in backdrop_instance["children"] if c]:
            node_group_index = bpy.data.node_groups.get(child.name)
            bpy.data.node_groups.remove(node_group_index)

        # Remove backdrop instance PropertyGroup
        bpy.context.scene.backdrop_op_instances.remove(instance_index)

    @staticmethod
    def _load_node_groups(libpath: str, link: False):
        """Load nodegroups from libpath library.

        Args:
            libpath (str): Library path to load data from
            link (False): Append or Link data
        """
        with bpy.data.libraries.load(libpath, link=link, relative=False) as (
            data_from,
            data_to,
        ):
            data_to.node_groups = data_from.node_groups
            return data_to.node_groups


class LinkBlenderNodegroupOnlyDataLoader(OnlyDataLoader):
    """Link only nodegroups from a .blend file."""

    families = ["blender.nodegroup"]

    label = "Link Nodegroup only"
    icon = "arrow-circle-o-down"
    color = "orange"
    color_tag = "COLOR_06"
    order = 1


class AppendBlenderNodegroupOnlyDataLoader(OnlyDataLoader):
    """Append only nodegroups from a .blend file."""

    families = ["blender.nodegroup"]

    label = "Append Nodegroup only"
    icon = "arrow-circle-down"
    color = "orange"
    color_tag = "COLOR_06"
    order = 3
