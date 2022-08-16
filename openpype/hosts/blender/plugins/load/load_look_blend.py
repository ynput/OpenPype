"""Load and assign extracted materials from look task."""

from typing import Dict

import bpy

from openpype.hosts.blender.api import plugin


class BlendLookLoader(plugin.AssetLoader):
    """Load and assign extracted materials from look task."""

    families = ["look"]
    representations = ["blend materials"]

    label = "Load Materials"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_07"
    no_namespace = True

    def _process(self, libpath, asset_group):

        container = self._load_library_collection(libpath)

        materials_assignment = container["materials_assignment"].to_dict()
        materials_indexes = container["materials_indexes"].to_dict()

        asset_group["materials_assignment"] = materials_assignment

        for obj in bpy.context.scene.objects:
            obj_name = obj.name
            original_name = obj_name.split(":")[-1]

            materials = materials_assignment.get(original_name)
            if materials and obj.type == "MESH":

                if obj.override_library or obj.library:
                    obj = plugin.make_local(obj)

                for idx, material in enumerate(materials):
                    if len(obj.material_slots) <= idx:
                        obj.data.materials.append(material)
                    obj.material_slots[idx].link = "OBJECT"
                    obj.material_slots[idx].material = material

                plugin.link_to_collection(obj, asset_group)

            mtl_idx = materials_indexes.get(original_name)
            if mtl_idx and obj.type == "MESH":
                for idx, face in enumerate(obj.data.polygons):
                    face.material_index = (
                        mtl_idx[idx] if len(mtl_idx) > idx else 0
                    )

    @staticmethod
    def _remove_container(container: Dict) -> bool:
        """Remove an existing container from a Blender scene.
        Arguments:
            container: Container to remove.
        Returns:
            bool: Whether the container was deleted.
        """
        object_name = container["objectName"]
        asset_group = bpy.data.collections.get(object_name)

        if not asset_group:
            return False

        # Unassign materials.
        if asset_group.get("materials_assignment"):

            mtl_assignment = asset_group["materials_assignment"].to_dict()

            for obj in bpy.context.scene.objects:
                obj_name = obj.name
                original_name = obj_name.split(":")[-1]

                materials = mtl_assignment.get(original_name)
                if materials and obj.type == "MESH":
                    for idx, material in enumerate(materials):
                        if len(obj.material_slots) > idx:
                            obj.material_slots[idx].material = None
                        material.use_fake_user = False
                    while len(obj.data.materials):
                        obj.data.materials.pop()

        # Unlink all child objects and collections.
        for obj in asset_group.objects:
            asset_group.objects.unlink(obj)
        for child in asset_group.children:
            asset_group.children.unlink(child)

        plugin.remove_container(asset_group)
        plugin.orphans_purge()

        return True
