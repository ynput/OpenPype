"""Load a layout in Blender."""

import json
from pathlib import Path
from pprint import pformat
from typing import Dict, Optional

import bpy

from openpype.pipeline import (
    discover_loader_plugins,
    remove_container,
    load_container,
    get_representation_path,
    loaders_from_representation,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api.pipeline import (
    AVALON_INSTANCES,
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)
from openpype.hosts.blender.api import plugin


class JsonLayoutLoader(plugin.AssetLoader):
    """Load layout published from Unreal."""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "code-fork"
    color = "orange"

    animation_creator_name = "CreateAnimation"

    def _remove(self, asset_group):
        objects = list(asset_group.children)

        for obj in objects:
            remove_container(obj.get(AVALON_PROPERTY))

    def _remove_animation_instances(self, asset_group):
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if instances:
            for obj in list(asset_group.children):
                anim_collection = instances.children.get(
                    obj.name + "_animation")
                if anim_collection:
                    bpy.data.collections.remove(anim_collection)

    def _get_loader(self, loaders, family):
        name = ""
        if family == 'rig':
            name = "BlendRigLoader"
        elif family == 'model':
            name = "BlendModelLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    def _process(self, libpath, asset, asset_group, actions):
        plugin.deselect_all()

        with open(libpath, "r") as fp:
            data = json.load(fp)

        all_loaders = discover_loader_plugins()

        for element in data:
            reference = element.get('reference')
            family = element.get('family')

            loaders = loaders_from_representation(all_loaders, reference)
            loader = self._get_loader(loaders, family)

            if not loader:
                continue

            instance_name = element.get('instance_name')

            action = None

            if actions:
                action = actions.get(instance_name, None)

            options = {
                'parent': asset_group,
                'transform': element.get('transform'),
                'action': action,
                'create_animation': True if family == 'rig' else False,
                'animation_asset': asset
            }

            if element.get('animation'):
                options['animation_file'] = str(Path(libpath).with_suffix(
                    '')) + "." + element.get('animation')

            # This should return the loaded asset, but the load call will be
            # added to the queue to run in the Blender main thread, so
            # at this time it will not return anything. The assets will be
            # loaded in the next Blender cycle, so we use the options to
            # set the transform, parent and assign the action, if there is one.
            load_container(
                loader,
                reference,
                namespace=instance_name,
                options=options
            )

        # Camera creation when loading a layout is not necessary for now,
        # but the code is worth keeping in case we need it in the future.
        # # Create the camera asset and the camera instance
        # creator_plugin = lib.get_creator_by_name("CreateCamera")
        # if not creator_plugin:
        #     raise ValueError("Creator plugin \"CreateCamera\" was "
        #                      "not found.")

        # legacy_create(
        #     creator_plugin,
        #     name="camera",
        #     # name=f"{unique_number}_{subset}_animation",
        #     asset=asset,
        #     options={"useSelection": False}
        #     # data={"dependencies": str(context["representation"]["_id"])}
        # )

    def process_asset(self,
                      context: dict,
                      name: str,
                      namespace: Optional[str] = None,
                      options: Optional[Dict] = None):
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
        asset_group.empty_display_type = 'SINGLE_ARROW'
        avalon_container.objects.link(asset_group)

        self._process(libpath, asset, asset_group, None)

        bpy.context.scene.collection.objects.link(asset_group)

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
            "objectName": group_name
        }

        self[:] = asset_group.children
        return asset_group.children

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = Path(get_representation_path(representation))
        extension = libpath.suffix.lower()

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
        assert extension in plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
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

        actions = {}

        for obj in asset_group.children:
            obj_meta = obj.get(AVALON_PROPERTY)
            if obj_meta.get('family') == 'rig':
                rig = None
                for child in obj.children:
                    if child.type == 'ARMATURE':
                        rig = child
                        break
                if not rig:
                    raise Exception("No armature in the rig asset group.")
                if rig.animation_data and rig.animation_data.action:
                    namespace = obj_meta.get('namespace')
                    actions[namespace] = rig.animation_data.action

        mat = asset_group.matrix_basis.copy()

        self._remove_animation_instances(asset_group)

        self._remove(asset_group)

        self._process(str(libpath), asset_group, actions)

        asset_group.matrix_basis = mat

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

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

        self._remove_animation_instances(asset_group)

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        return True
