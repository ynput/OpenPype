"""Load a rig asset in Blender."""

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
from openpype.hosts.blender.api import (
    plugin,
    get_selection,
)
from openpype.hosts.blender.api.pipeline import (
    AVALON_CONTAINERS,
    AVALON_PROPERTY,
)


class BlendRigLoader(plugin.AssetLoader):
    """Load rigs from a .blend file."""

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
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

    def _process(self, libpath, asset_group, group_name, action):
        with bpy.data.libraries.load(
            libpath, link=True, relative=False
        ) as (data_from, data_to):
            data_to.objects = data_from.objects

        parent = bpy.context.scene.collection

        empties = [obj for obj in data_to.objects if obj.type == 'EMPTY']

        container = None

        for empty in empties:
            if empty.get(AVALON_PROPERTY):
                container = empty
                break

        assert container, "No asset group found"

        # Children must be linked before parents,
        # otherwise the hierarchy will break
        objects = []
        nodes = list(container.children)

        allowed_types = ['ARMATURE', 'MESH']

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
            local_obj = plugin.prepare_data(obj, group_name)

            if local_obj.type == 'MESH':
                plugin.prepare_data(local_obj.data, group_name)

                if obj != local_obj:
                    for constraint in constraints:
                        if constraint.target == obj:
                            constraint.target = local_obj

                for material_slot in local_obj.material_slots:
                    if material_slot.material:
                        plugin.prepare_data(material_slot.material, group_name)
            elif local_obj.type == 'ARMATURE':
                plugin.prepare_data(local_obj.data, group_name)

                if action is not None:
                    if local_obj.animation_data is None:
                        local_obj.animation_data_create()
                    local_obj.animation_data.action = action
                elif (local_obj.animation_data and
                      local_obj.animation_data.action is not None):
                    plugin.prepare_data(
                        local_obj.animation_data.action, group_name)

                # Set link the drivers to the local object
                if local_obj.data.animation_data:
                    for d in local_obj.data.animation_data.drivers:
                        for v in d.driver.variables:
                            for t in v.targets:
                                t.id = local_obj

            if not local_obj.get(AVALON_PROPERTY):
                local_obj[AVALON_PROPERTY] = dict()

            avalon_info = local_obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

        objects.reverse()

        curves = [obj for obj in data_to.objects if obj.type == 'CURVE']

        for curve in curves:
            local_obj = plugin.prepare_data(curve, group_name)
            plugin.prepare_data(local_obj.data, group_name)

            local_obj.use_fake_user = True

            for mod in local_obj.modifiers:
                mod_target_name = mod.object.name
                mod.object = bpy.data.objects.get(
                    f"{group_name}:{mod_target_name}")

            if not local_obj.get(AVALON_PROPERTY):
                local_obj[AVALON_PROPERTY] = dict()

            avalon_info = local_obj[AVALON_PROPERTY]
            avalon_info.update({"container_name": group_name})

            local_obj.parent = asset_group
            objects.append(local_obj)

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

        action = None

        plugin.deselect_all()

        create_animation = False
        anim_file = None

        if options is not None:
            parent = options.get('parent')
            transform = options.get('transform')
            action = options.get('action')
            create_animation = options.get('create_animation')
            anim_file = options.get('animation_file')

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

        objects = self._process(libpath, asset_group, group_name, action)

        if create_animation:
            creator_plugin = lib.get_creator_by_name("CreateAnimation")
            if not creator_plugin:
                raise ValueError("Creator plugin \"CreateAnimation\" was "
                                 "not found.")

            asset_group.select_set(True)

            animation_asset = options.get('animation_asset')

            legacy_create(
                creator_plugin,
                name=namespace + "_animation",
                # name=f"{unique_number}_{subset}_animation",
                asset=animation_asset,
                options={"useSelection": False, "asset_group": asset_group},
                data={"dependencies": str(context["representation"]["_id"])}
            )

            plugin.deselect_all()

        if anim_file:
            bpy.ops.import_scene.fbx(filepath=anim_file, anim_offset=0.0)

            imported = get_selection()

            armature = [
                o for o in asset_group.children if o.type == 'ARMATURE'][0]

            imported_group = [
                o for o in imported if o.type == 'EMPTY'][0]

            for obj in imported:
                if obj.type == 'ARMATURE':
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = obj.animation_data.action

            self._remove(imported_group)
            bpy.data.objects.remove(imported_group)

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

    def exec_update(self, container: Dict, representation: Dict):
        """Update the loaded asset.

        This will remove all children of the asset group, load the new ones
        and add them as children of the group.
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

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get('libpath') == group_libpath:
                count += 1

        # Get the armature of the rig
        objects = asset_group.children
        armature = [obj for obj in objects if obj.type == 'ARMATURE'][0]

        action = None
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action

        mat = asset_group.matrix_basis.copy()

        self._remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(group_libpath))
            bpy.data.libraries.remove(library)

        self._process(str(libpath), asset_group, object_name, action)

        asset_group.matrix_basis = mat

        metadata["libpath"] = str(libpath)
        metadata["representation"] = str(representation["_id"])
        metadata["parent"] = str(representation["parent"])

    def exec_remove(self, container: Dict) -> bool:
        """Remove an existing asset group from a Blender scene.

        Arguments:
            container (openpype:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the asset group was deleted.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.objects.get(object_name)
        libpath = asset_group.get(AVALON_PROPERTY).get('libpath')

        # Check how many assets use the same library
        count = 0
        for obj in bpy.data.collections.get(AVALON_CONTAINERS).objects:
            if obj.get(AVALON_PROPERTY).get('libpath') == libpath:
                count += 1

        if not asset_group:
            return False

        self._remove(asset_group)

        bpy.data.objects.remove(asset_group)

        # If it is the last object to use that library, remove it
        if count == 1:
            library = bpy.data.libraries.get(bpy.path.basename(libpath))
            bpy.data.libraries.remove(library)

        return True
