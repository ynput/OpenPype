"""Load a layout in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import bpy

from openpype import lib
from openpype.pipeline import (
    legacy_create,
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)


class BlendLayoutLoader(plugin.AssetLoader):
    """Load layout from a .blend file."""

    families = ["layout"]
    representations = ["blend"]

    label = "Link Layout"
    icon = "code-fork"
    color = "orange"

    def _remove(self, asset_group):
        objects = list(asset_group.children)

        for obj in objects:
            if obj.type == 'MESH':
                for material_slot in list(obj.material_slots):
                    if material_slot.material:
                        bpy.data.materials.remove(material_slot.material)
                bpy.data.meshes.remove(obj.data)
            elif obj.type == 'ARMATURE':
                objects.extend(obj.children)
                bpy.data.armatures.remove(obj.data)
            elif obj.type == 'CURVE':
                bpy.data.curves.remove(obj.data)
            elif obj.type == 'EMPTY':
                objects.extend(obj.children)
                bpy.data.objects.remove(obj)

    def _remove_asset_and_library(self, asset_group):
        libpath = asset_group.get(AVALON_PROPERTY).get('libpath')

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).all_objects:
            if obj.get(AVALON_PROPERTY).get('libpath') == libpath:
                count += 1

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(libpath))
            bpy.data.libraries.remove(library)

    def _process(
        self, libpath, asset_group, group_name, asset, representation, actions
    ):
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.objects = data_from.objects

        parent = bpy.context.scene.collection

        empties = [obj for obj in data_to.objects if obj.type == 'EMPTY']

        container = None

        for empty in empties:
            if (empty.get(AVALON_PROPERTY) and
                    empty.get(AVALON_PROPERTY).get('family') == 'layout'):
                container = empty
                break

        assert container, "No asset group found"

        # Children must be linked before parents,
        # otherwise the hierarchy will break
        objects = []
        nodes = list(container.children)

        allowed_types = ['ARMATURE', 'MESH', 'EMPTY']

        for obj in nodes:
            if obj.type in allowed_types:
                obj.parent = asset_group

        for obj in nodes:
            if obj.type in allowed_types:
                objects.append(obj)
                nodes.extend(list(obj.children))

        objects.reverse()

        constraints = []

        armatures = [obj for obj in objects if obj.type == 'ARMATURE']

        for armature in armatures:
            for bone in armature.pose.bones:
                for constraint in bone.constraints:
                    if hasattr(constraint, 'target'):
                        constraints.append(constraint)

        for obj in objects:
            parent.objects.link(obj)

        for obj in objects:
            local_obj = plugin.prepare_data(obj)

            action = None

            if actions:
                action = actions.get(local_obj.name, None)

            if local_obj.type == 'MESH':
                plugin.prepare_data(local_obj.data)

                if obj != local_obj:
                    for constraint in constraints:
                        if constraint.target == obj:
                            constraint.target = local_obj

                for material_slot in local_obj.material_slots:
                    if material_slot.material:
                        plugin.prepare_data(material_slot.material)
            elif local_obj.type == 'ARMATURE':
                plugin.prepare_data(local_obj.data)

                if action is not None:
                    if local_obj.animation_data is None:
                        local_obj.animation_data_create()
                    local_obj.animation_data.action = action
                elif (local_obj.animation_data and
                      local_obj.animation_data.action is not None):
                    plugin.prepare_data(
                        local_obj.animation_data.action)

                # Set link the drivers to the local object
                if local_obj.data.animation_data:
                    for d in local_obj.data.animation_data.drivers:
                        for v in d.driver.variables:
                            for t in v.targets:
                                t.id = local_obj

            elif local_obj.type == 'EMPTY':
                creator_plugin = lib.get_creator_by_name("CreateAnimation")
                if not creator_plugin:
                    raise ValueError("Creator plugin \"CreateAnimation\" was "
                                     "not found.")

                legacy_create(
                    creator_plugin,
                    name=local_obj.name.split(':')[-1] + "_animation",
                    asset=asset,
                    options={"useSelection": False,
                             "asset_group": local_obj},
                    data={"dependencies": representation}
                )

            if not local_obj.get(AVALON_PROPERTY):
                local_obj[AVALON_PROPERTY] = dict()

            avalon_info = local_obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

        objects.reverse()

        armatures = [
            obj for obj in bpy.data.objects
            if obj.type == 'ARMATURE' and obj.library is None]
        arm_act = {}

        # The armatures with an animation need to be at the center of the
        # scene to be hooked correctly by the curves modifiers.
        for armature in armatures:
            if armature.animation_data and armature.animation_data.action:
                arm_act[armature] = armature.animation_data.action
                armature.animation_data.action = None
                armature.location = (0.0, 0.0, 0.0)
                for bone in armature.pose.bones:
                    bone.location = (0.0, 0.0, 0.0)
                    bone.rotation_euler = (0.0, 0.0, 0.0)

        curves = [obj for obj in data_to.objects if obj.type == 'CURVE']

        for curve in curves:
            curve_name = curve.name.split(':')[0]
            curve_obj = bpy.data.objects.get(curve_name)

            local_obj = plugin.prepare_data(curve)
            plugin.prepare_data(local_obj.data)

            # Curves need to reset the hook, but to do that they need to be
            # in the view layer.
            parent.objects.link(local_obj)
            plugin.deselect_all()
            local_obj.select_set(True)
            bpy.context.view_layer.objects.active = local_obj
            if local_obj.library is None:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.hook_reset()
                bpy.ops.object.mode_set(mode='OBJECT')
            parent.objects.unlink(local_obj)

            local_obj.use_fake_user = True

            for mod in local_obj.modifiers:
                mod.object = bpy.data.objects.get(f"{mod.object.name}")

            if not local_obj.get(AVALON_PROPERTY):
                local_obj[AVALON_PROPERTY] = dict()

            avalon_info = local_obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

            local_obj.parent = curve_obj
            objects.append(local_obj)

        for armature in armatures:
            if arm_act.get(armature):
                armature.animation_data.action = arm_act[armature]

        while bpy.data.orphans_purge(do_local_ids=False):
            pass

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
        representation = str(context["representation"]["_id"])

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

        objects = self._process(
            libpath, asset_group, group_name, asset, representation, None)

        for child in asset_group.children:
            if child.get(AVALON_PROPERTY):
                avalon_container.objects.link(child)

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

        self[:] = objects
        return objects

    def update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all objects of the current collection, load the new
        ones and add them to the collection.
        If the objects of the collection are used in another collection they
        will not be removed, only unlinked. Normally this should not be the
        case though.

        Warning:
            No nested collections are supported at the moment!
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
                    instance_name = obj_meta.get('instance_name')
                    actions[instance_name] = rig.animation_data.action

        mat = asset_group.matrix_basis.copy()

        # Remove the children of the asset_group first
        for child in list(asset_group.children):
            self._remove_asset_and_library(child)

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get('libpath') == group_libpath:
                count += 1

        self._remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(group_libpath))
            bpy.data.libraries.remove(library)

        self._process(str(libpath), asset_group, object_name, actions)

        avalon_container = bpy.data.collections.get(AVALON_CONTAINERS)
        for child in asset_group.children:
            if child.get(AVALON_PROPERTY):
                avalon_container.objects.link(child)

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

        Warning:
            No nested collections are supported at the moment!
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)

        if not asset_group:
            return False

        # Remove the children of the asset_group first
        for child in list(asset_group.children):
            self._remove_asset_and_library(child)

        self._remove_asset_and_library(asset_group)

        return True
