"""Load a model asset in Blender."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import os
import json
import bpy

from openpype.pipeline import get_representation_path
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import (
    containerise_existing,
    AVALON_PROPERTY
)


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

    def _process(self, libpath, container_name, objects):
        with open(libpath, "r") as fp:
            data = json.load(fp)

        path = os.path.dirname(libpath)
        materials_path = f"{path}/resources"

        materials = []

        for entry in data:
            file = entry.get('fbx_filename')
            if file is None:
                continue

            bpy.ops.import_scene.fbx(filepath=f"{materials_path}/{file}")

            mesh = [o for o in bpy.context.scene.objects if o.select_get()][0]
            material = mesh.data.materials[0]
            material.name = f"{material.name}:{container_name}"

            texture_file = entry.get('tga_filename')
            if texture_file:
                node_tree = material.node_tree
                pbsdf = node_tree.nodes['Principled BSDF']
                base_color = pbsdf.inputs[0]
                tex_node = base_color.links[0].from_node
                tex_node.image.filepath = f"{materials_path}/{texture_file}"

            materials.append(material)

            for obj in objects:
                for child in self.get_all_children(obj):
                    mesh_name = child.name.split(':')[0]
                    if mesh_name == material.name.split(':')[0]:
                        child.data.materials.clear()
                        child.data.materials.append(material)
                        break

            bpy.data.objects.remove(mesh)

        return materials, objects

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
        containerise_existing(
            container,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        metadata = container.get(AVALON_PROPERTY)

        metadata["libpath"] = libpath
        metadata["lib_container"] = lib_container

        selected = [o for o in bpy.context.scene.objects if o.select_get()]

        materials, objects = self._process(libpath, container_name, selected)

        # Save the list of imported materials in the metadata container
        metadata["objects"] = objects
        metadata["materials"] = materials

        metadata["parent"] = str(context["representation"]["parent"])
        metadata["family"] = context["representation"]["context"]["family"]

        nodes = list(container.objects)
        nodes.append(container)
        self[:] = nodes
        return nodes

    def update(self, container: Dict, representation: Dict):
        collection = bpy.data.collections.get(container["objectName"])
        libpath = Path(get_representation_path(representation))
        extension = libpath.suffix.lower()

        self.log.info(
            "Container: %s\nRepresentation: %s",
            pformat(container, indent=2),
            pformat(representation, indent=2),
        )

        assert collection, (
            f"The asset is not loaded: {container['objectName']}"
        )
        assert not (collection.children), (
            "Nested collections are not supported."
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

        collection_metadata = collection.get(AVALON_PROPERTY)
        collection_libpath = collection_metadata["libpath"]

        normalized_collection_libpath = (
            str(Path(bpy.path.abspath(collection_libpath)).resolve())
        )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        self.log.debug(
            "normalized_collection_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_collection_libpath,
            normalized_libpath,
        )
        if normalized_collection_libpath == normalized_libpath:
            self.log.info("Library already loaded, not updating...")
            return

        for obj in collection_metadata['objects']:
            for child in self.get_all_children(obj):
                child.data.materials.clear()

        for material in collection_metadata['materials']:
            bpy.data.materials.remove(material)

        namespace = collection_metadata['namespace']
        name = collection_metadata['name']

        container_name = f"{namespace}_{name}"

        materials, objects = self._process(
            libpath, container_name, collection_metadata['objects'])

        collection_metadata["objects"] = objects
        collection_metadata["materials"] = materials
        collection_metadata["libpath"] = str(libpath)
        collection_metadata["representation"] = str(representation["_id"])

    def remove(self, container: Dict) -> bool:
        collection = bpy.data.collections.get(container["objectName"])
        if not collection:
            return False

        collection_metadata = collection.get(AVALON_PROPERTY)

        for obj in collection_metadata['objects']:
            for child in self.get_all_children(obj):
                child.data.materials.clear()

        for material in collection_metadata['materials']:
            bpy.data.materials.remove(material)

        bpy.data.collections.remove(collection)

        return True
