"""Shared functionality for pipeline plugins for Blender."""

from pathlib import Path
from typing import Dict, List, Optional

import bpy

from avalon import api

VALID_EXTENSIONS = [".blend"]


def model_name(asset: str, subset: str, namespace: Optional[str] = None) -> str:
    """Return a consistent name for a model asset."""
    name = f"{asset}_{subset}"
    if namespace:
        name = f"{namespace}:{name}"
    return name


class AssetLoader(api.Loader):
    """A basic AssetLoader for Blender

    This will implement the basic logic for linking/appending assets
    into another Blender scene.

    The `update` method should be implemented by a sub-class, because
    it's different for different types (e.g. model, rig, animation,
    etc.).
    """

    @staticmethod
    def _get_instance_empty(instance_name: str, nodes: List) -> Optional[bpy.types.Object]:
        """Get the 'instance empty' that holds the collection instance."""
        for node in nodes:
            if not isinstance(node, bpy.types.Object):
                continue
            if (node.type == 'EMPTY' and node.instance_type == 'COLLECTION'
                    and node.instance_collection and node.name == instance_name):
                return node
        return None

    @staticmethod
    def _get_instance_collection(instance_name: str, nodes: List) -> Optional[bpy.types.Collection]:
        """Get the 'instance collection' (container) for this asset."""
        for node in nodes:
            if not isinstance(node, bpy.types.Collection):
                continue
            if node.name == instance_name:
                return node
        return None

    @staticmethod
    def _get_library_from_container(container: bpy.types.Collection) -> bpy.types.Library:
        """Find the library file from the container.

        It traverses the objects from this collection, checks if there is only
        1 library from which the objects come from and returns the library.

        Warning:
            No nested collections are supported at the moment!
        """
        assert not container.children, "Nested collections are not supported."
        assert container.objects, "The collection doesn't contain any objects."
        libraries = set()
        for obj in container.objects:
            assert obj.library, f"'{obj.name}' is not linked."
            libraries.add(obj.library)

        assert len(libraries) == 1, "'{container.name}' contains objects from more then 1 library."

        return list(libraries)[0]

    def process_asset(self,
                      context: dict,
                      name: str,
                      namespace: Optional[str] = None,
                      options: Optional[Dict] = None):
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def load(self,
             context: dict,
             name: Optional[str] = None,
             namespace: Optional[str] = None,
             options: Optional[Dict] = None) -> Optional[bpy.types.Collection]:
        """Load asset via database

        Arguments:
            context: Full parenthood of representation to load
            name: Use pre-defined name
            namespace: Use pre-defined namespace
            options: Additional settings dictionary
        """
        # TODO (jasper): make it possible to add the asset several times by
        # just re-using the collection
        assert Path(self.fname).exists(), f"{self.fname} doesn't exist."

        self.process_asset(
            context=context,
            name=name,
            namespace=namespace,
            options=options,
        )

        # Only containerise if anything was loaded by the Loader.
        nodes = self[:]
        if not nodes:
            return None

        # Only containerise if it's not already a collection from a .blend file.
        representation = context["representation"]["name"]
        if representation != "blend":
            from avalon.blender.pipeline import containerise
            return containerise(
                name=name,
                namespace=namespace,
                nodes=nodes,
                context=context,
                loader=self.__class__.__name__,
            )

        asset = context["asset"]["name"]
        subset = context["subset"]["name"]
        instance_name = model_name(asset, subset, namespace)

        return self._get_instance_collection(instance_name, nodes)

    def update(self, container: Dict, representation: Dict):
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")

    def remove(self, container: Dict) -> bool:
        """Must be implemented by a sub-class"""
        raise NotImplementedError("Must be implemented by a sub-class")
