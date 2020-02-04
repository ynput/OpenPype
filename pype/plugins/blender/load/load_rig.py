"""Load a rig asset in Blender."""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

import avalon.blender.pipeline
import bpy
import pype.blender
from avalon import api

logger = logging.getLogger("pype").getChild("blender").getChild("load_model")

class BlendRigLoader(pype.blender.AssetLoader):
    """Load rigs from a .blend file.

    Because they come from a .blend file we can simply link the collection that
    contains the model. There is no further need to 'containerise' it.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["rig"]
    representations = ["blend"]

    label = "Link Rig"
    icon = "code-fork"
    color = "orange"

    @staticmethod
    def _get_lib_collection(name: str, libpath: Path) -> Optional[bpy.types.Collection]:
        """Find the collection(s) with name, loaded from libpath.

        Note:
            It is assumed that only 1 matching collection is found.
        """
        for collection in bpy.data.collections:
            if collection.name != name:
                continue
            if collection.library is None:
                continue
            if not collection.library.filepath:
                continue
            collection_lib_path = str(Path(bpy.path.abspath(collection.library.filepath)).resolve())
            normalized_libpath = str(Path(bpy.path.abspath(str(libpath))).resolve())
            if collection_lib_path == normalized_libpath:
                return collection
        return None

    @staticmethod
    def _collection_contains_object(
        collection: bpy.types.Collection, object: bpy.types.Object
    ) -> bool:
        """Check if the collection contains the object."""
        for obj in collection.objects:
            if obj == object:
                return True
        return False

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
        lib_container = pype.blender.plugin.rig_name(asset, subset)
        container_name = pype.blender.plugin.rig_name(
            asset, subset, namespace
        )
        relative = bpy.context.preferences.filepaths.use_relative_paths

        bpy.data.collections.new( lib_container )

        container = bpy.data.collections[lib_container]
        container.name = container_name
        avalon.blender.pipeline.containerise_existing(
            container,
            name,
            namespace,
            context,
            self.__class__.__name__,
        )

        container_metadata = container.get( 'avalon' )

        objects_list = []

        with bpy.data.libraries.load(
            libpath, link=True, relative=relative
        ) as (data_from, data_to):

            data_to.collections = [lib_container]

        scene = bpy.context.scene

        models = [ obj for obj in bpy.data.collections[lib_container].objects if obj.type == 'MESH' ]
        armatures = [ obj for obj in bpy.data.collections[lib_container].objects if obj.type == 'ARMATURE' ]

        for obj in models + armatures:

            scene.collection.objects.link( obj )

            obj = obj.make_local()

            if not obj.get("avalon"):

                obj["avalon"] = dict()

            avalon_info = obj["avalon"]
            avalon_info.update( { "container_name": container_name } )
            objects_list.append( obj )

        container_metadata["objects"] = objects_list

        bpy.ops.object.select_all( action = 'DESELECT' )

        nodes = list(container.objects)
        nodes.append(container)
        self[:] = nodes
        return nodes

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
        instance_name = pype.blender.plugin.rig_name(asset, subset, namespace)

        return self._get_instance_collection(instance_name, nodes)

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

        collection = bpy.data.collections.get(
            container["objectName"]
        )
        libpath = Path(api.get_representation_path(representation))
        extension = libpath.suffix.lower()

        logger.info(
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
        assert extension in pype.blender.plugin.VALID_EXTENSIONS, (
            f"Unsupported file: {libpath}"
        )
        collection_libpath = (
            self._get_library_from_container(collection).filepath
        )
        print( collection_libpath )
        normalized_collection_libpath = (
            str(Path(bpy.path.abspath(collection_libpath)).resolve())
        )
        print( normalized_collection_libpath )
        normalized_libpath = (
            str(Path(bpy.path.abspath(str(libpath))).resolve())
        )
        print( normalized_libpath )
        logger.debug(
            "normalized_collection_libpath:\n  %s\nnormalized_libpath:\n  %s",
            normalized_collection_libpath,
            normalized_libpath,
        )
        if normalized_collection_libpath == normalized_libpath:
            logger.info("Library already loaded, not updating...")
            return
        # Let Blender's garbage collection take care of removing the library
        # itself after removing the objects.
        objects_to_remove = set()
        collection_objects = list()
        collection_objects[:] = collection.objects
        for obj in collection_objects:
            # Unlink every object
            collection.objects.unlink(obj)
            remove_obj = True
            for coll in [
                coll for coll in bpy.data.collections
                if coll != collection
            ]:
                if (
                    coll.objects and
                    self._collection_contains_object(coll, obj)
                ):
                    remove_obj = False
            if remove_obj:
                objects_to_remove.add(obj)

        for obj in objects_to_remove:
            # Only delete objects that are not used elsewhere
            bpy.data.objects.remove(obj)

        instance_empties = [
            obj for obj in collection.users_dupli_group
            if obj.name in collection.name
        ]
        if instance_empties:
            instance_empty = instance_empties[0]
            container_name = instance_empty["avalon"]["container_name"]

        relative = bpy.context.preferences.filepaths.use_relative_paths
        with bpy.data.libraries.load(
            str(libpath), link=True, relative=relative
        ) as (_, data_to):
            data_to.collections = [container_name]

        new_collection = self._get_lib_collection(container_name, libpath)
        if new_collection is None:
            raise ValueError(
                "A matching collection '{container_name}' "
                "should have been found in: {libpath}"
            )

        for obj in new_collection.objects:
            collection.objects.link(obj)
        bpy.data.collections.remove(new_collection)
        # Update the representation on the collection
        avalon_prop = collection[avalon.blender.pipeline.AVALON_PROPERTY]
        avalon_prop["representation"] = str(representation["_id"])

    def remove(self, container: Dict) -> bool:
        """Remove an existing container from a Blender scene.

        Arguments:
            container (avalon-core:container-1.0): Container to remove,
                from `host.ls()`.

        Returns:
            bool: Whether the container was deleted.

        Warning:
            No nested collections are supported at the moment!
        """

        print( container["objectName"] )

        collection = bpy.data.collections.get(
            container["objectName"]
        )
        if not collection:
            return False
        assert not (collection.children), (
            "Nested collections are not supported."
        )

        data = collection.get( "avalon" )
        objects = data["objects"]

        for obj in objects:
            bpy.data.objects.remove( obj )
        
        bpy.data.collections.remove(collection)

        return True
