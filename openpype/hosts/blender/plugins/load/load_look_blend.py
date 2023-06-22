"""Load and assign extracted materials from look task."""

import bpy

from openpype.hosts.blender.api import plugin


class MaterialLookLoader(plugin.AssetLoader):
    """Load and assign extracted materials from .blend file."""

    label = "Load Materials"
    color = "orange"
    no_namespace = True

    bl_types = frozenset({bpy.types.Material})

    def load(self, *args, **kwargs):
        """Override `load` to reassign loaded materials to original objects."""
        container, datablocks = super().load(*args, **kwargs)

        # Reassign materials to original objects by their names
        # TODO this is a build first workfile feature
        for material in datablocks:
            users = material.get("users", [])
            for user_name in users:
                obj = bpy.data.objects.get(user_name)
                if obj:
                    # Append material to object
                    obj.data.materials.append(material)

                    # Assign indexes
                    mtl_idx = material.get("indexes", {}).get(user_name)
                    if not mtl_idx:
                        continue

                    for idx, face in enumerate(obj.data.polygons):
                        face.material_index = (
                            mtl_idx[idx] if len(mtl_idx) > idx else 0
                        )

        return container, datablocks


class LinkLookLoader(MaterialLookLoader):
    """Link materials from a .blend file."""

    families = ["look"]
    representations = ["blend"]

    label = "Link Material"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendLookLoader(MaterialLookLoader):
    """Append materials from a .blend file."""

    families = ["look"]
    representations = ["blend"]

    label = "Append Material"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
