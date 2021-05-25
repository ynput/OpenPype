"""Load a model asset in Blender."""

from typing import Dict, List, Optional

import os
import json
import bpy

from avalon import blender
import openpype.hosts.blender.api.plugin as plugin


class BlendLookLoader(plugin.AssetLoader):
    """Load models from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.
    """

    families = ["look"]
    representations = ["json"]

    label = "Load Look"
    icon = "code-fork"
    color = "orange"

    def get_all_children(self, obj):
        children = list(obj.children)

        for child in children:
            children.extend(child.children)

        return children

    def _process(self, libpath):
        with open(libpath, "r") as fp:
            data = json.load(fp)

        path = os.path.dirname(libpath)
        materials_path = f"{path}/resources"

        selected = [o for o in bpy.context.scene.objects if o.select_get()]

        materials = []

        for entry in data:
            file = entry.get('fbx_filename')
            if file is None:
                continue

            bpy.ops.import_scene.fbx(filepath=f"{materials_path}/{file}")

            mesh = [o for o in bpy.context.scene.objects if o.select_get()][0]
            material = mesh.data.materials[0]

            texture_file = entry.get('tga_filename')
            if texture_file:
                node_tree = material.node_tree
                pbsdf = node_tree.nodes['Principled BSDF']
                base_color = pbsdf.inputs[0]
                tex_node = base_color.links[0].from_node
                tex_node.image.filepath = f"{materials_path}/{texture_file}"

            materials.append(material)

            for obj in selected:
                for child in self.get_all_children(obj):
                    mesh_name = child.name.split(':')[0]
                    if mesh_name == material.name:
                        child.data.materials.clear()
                        child.data.materials.append(material)
                        break

            bpy.data.objects.remove(mesh)

        return materials

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

        lib_container = plugin.asset_name(
            asset, subset
        )
        unique_number = plugin.get_unique_number(
            asset, subset
        )
        namespace = namespace or f"{asset}_{unique_number}"
        container_name = plugin.asset_name(
            asset, subset, unique_number
        )

        container = bpy.data.collections.new(lib_container)
        container.name = container_name
        blender.pipeline.containerise_existing(
            container,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        metadata = container.get(blender.pipeline.AVALON_PROPERTY)

        metadata["libpath"] = libpath
        metadata["lib_container"] = lib_container

        materials = self._process(libpath)

        # Save the list of imported materials in the metadata container
        metadata["objects"] = materials

        metadata["parent"] = str(context["representation"]["parent"])
        metadata["family"] = context["representation"]["context"]["family"]

        nodes = list(container.objects)
        nodes.append(container)
        self[:] = nodes
        return nodes
