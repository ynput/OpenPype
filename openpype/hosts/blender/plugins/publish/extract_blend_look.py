import bpy

from openpype.hosts.blender.plugins.publish.extract_blend import ExtractBlend


class ExtractBlendLook(ExtractBlend):
    """Extract a blend file with materials and meshes."""

    label = "Extract Look"
    families = ["look"]
    optional = True

    pack_images = True

    def process(self, instance):
        """Override `process` to keep users of materials.

        Users are reassigned when loading materials.
        """
        self.log.info("Performing extraction...")

        # Get all objects materials
        # TODO optimize with user_map
        for obj in {
            o
            for o in instance
            if isinstance(o, bpy.types.Object) and o.type == "MESH"
        }:
            if len(obj.material_slots):
                obj_materials = set()
                for mtl_slot in obj.material_slots:
                    material = mtl_slot.material
                    if material:
                        # Keep users' names of material
                        material_users = set(material.get("users", set()))
                        material["users"] = list(material_users | {obj.name})

                        obj_materials.add(material)

                        # Keep polygons material indexes for objects.
                        if len(obj_materials) > 1:
                            material["indexes"] = material.get("indexes", [])
                            material["indexes"] = {
                                obj.name: [
                                    face.material_index
                                    for face in obj.data.polygons
                                ]
                            }

        super().process(instance)
