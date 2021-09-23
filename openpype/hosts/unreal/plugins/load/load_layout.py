import os
import json

import unreal
from unreal import EditorAssetLibrary
from unreal import EditorLevelLibrary
from unreal import MathLibrary as umath

from avalon import api, pipeline
from avalon.unreal import lib
from avalon.unreal import pipeline as unreal_pipeline


class LayoutLoader(api.Loader):
    """Load Layout from a JSON file"""

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout"
    icon = "code-fork"
    color = "orange"

    def _get_asset_containers(self, path):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        asset_content = EditorAssetLibrary.list_assets(
            path, recursive=True)

        asset_containers = []

        # Get all the asset containers
        for a in asset_content:
            obj = ar.get_asset_by_object_path(a)
            if obj.get_asset().get_class().get_name() == 'AssetContainer':
                asset_containers.append(obj)

        return asset_containers

    def _get_loader(self, loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshFBXLoader"
        elif family == 'model':
            name = "StaticMeshFBXLoader"
        elif family == 'camera':
            name = "CameraLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    def _process_family(self, assets, classname, transform):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        for asset in assets:
            obj = ar.get_asset_by_object_path(asset).get_asset()
            if obj.get_class().get_name() == classname:
                actor = EditorLevelLibrary.spawn_actor_from_object(
                    obj,
                    transform.get('translation')
                )
                actor.set_actor_rotation(unreal.Rotator(
                    umath.radians_to_degrees(
                        transform.get('rotation').get('x')),
                    -umath.radians_to_degrees(
                        transform.get('rotation').get('y')),
                    umath.radians_to_degrees(
                        transform.get('rotation').get('z')),
                ), False)
                actor.set_actor_scale3d(transform.get('scale'))

    def _process(self, libpath, asset_dir, loaded = []):
        with open(libpath, "r") as fp:
            data = json.load(fp)

        all_loaders = api.discover(api.Loader)

        # loaded = []

        for element in data:
            reference = element.get('reference_fbx')

            if reference in loaded:
                continue

            loaded.append(reference)

            family = element.get('family')
            loaders = api.loaders_from_representation(
                all_loaders, reference)
            loader = self._get_loader(loaders, family)

            if not loader:
                continue

            instance_name = element.get('instance_name')

            options = {
                "asset_dir": asset_dir
            }

            assets = api.load(
                loader,
                reference,
                namespace=instance_name,
                options=options
            )

            instances = [
                item for item in data 
                if item.get('reference_fbx') == reference]

            for instance in instances:
                transform = instance.get('transform')

                if family == 'model':
                    self._process_family(assets, 'StaticMesh', transform)
                elif family == 'rig':
                    self._process_family(assets, 'SkeletalMesh', transform)

    def _remove_family(self, assets, components, classname, propname):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        objects = []
        for a in assets:
            obj = ar.get_asset_by_object_path(a)
            if obj.get_asset().get_class().get_name() == classname:
                objects.append(obj)
        for obj in objects:
            for comp in components:
                if comp.get_editor_property(propname) == obj.get_asset():
                    comp.get_owner().destroy_actor()

    def _remove_actors(self, path):
        asset_containers = self._get_asset_containers(path)

        # Get all the static and skeletal meshes components in the level
        components = EditorLevelLibrary.get_all_level_actors_components()
        static_meshes_comp = [
            c for c in components 
            if c.get_class().get_name() == 'StaticMeshComponent']
        skel_meshes_comp = [
            c for c in components 
            if c.get_class().get_name() == 'SkeletalMeshComponent']

        # For all the asset containers, get the static and skeletal meshes.
        # Then, check the components in the level and destroy the matching
        # actors.
        for asset_container in asset_containers:
            package_path = asset_container.get_editor_property('package_path')
            family = EditorAssetLibrary.get_metadata_tag(
                asset_container.get_asset(), 'family')
            assets = EditorAssetLibrary.list_assets(
                str(package_path), recursive=False)
            if family == 'model':
                self._remove_family(
                    assets, static_meshes_comp, 'StaticMesh', 'static_mesh')
            elif family == 'rig':
                self._remove_family(
                    assets, skel_meshes_comp, 'SkeletalMesh', 'skeletal_mesh')

    def load(self, context, name, namespace, options):
        """
        Load and containerise representation into Content Browser.

        This is two step process. First, import FBX to temporary path and
        then call `containerise()` on it - this moves all content to new
        directory and then it will create AssetContainer there and imprint it
        with metadata. This will mark this path as container.

        Args:
            context (dict): application context
            name (str): subset name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            data (dict): Those would be data to be imprinted. This is not used
                         now, data are imprinted by `containerise()`.

        Returns:
            list(str): list of container content
        """
        # Create directory for asset and avalon container
        root = "/Game/Avalon/Assets"
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()
        asset_dir, container_name = tools.create_unique_asset_name(
            "{}/{}/{}".format(root, asset, name), suffix="")

        container_name += suffix

        EditorAssetLibrary.make_directory(asset_dir)

        self._process(self.fname, asset_dir)

        # Create Asset Container
        lib.create_avalon_container(
            container=container_name, path=asset_dir)

        data = {
            "schema": "openpype:container-2.0",
            "id": pipeline.AVALON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"]
        }
        unreal_pipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        asset_content = EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        source_path = api.get_representation_path(representation)
        destination_path = container["namespace"]

        self._remove_actors(destination_path)

        with open(source_path, "r") as fp:
            data = json.load(fp)

        references = [e.get('reference_fbx') for e in data]
        asset_containers = self._get_asset_containers(destination_path)
        loaded = []

        # Delete all the assets imported with the previous version of the 
        # layout, if they're not in the new layout.
        for asset_container in asset_containers:
            if asset_container.get_editor_property(
                'asset_name') == container["objectName"]:
                    continue
            ref = EditorAssetLibrary.get_metadata_tag(
                asset_container.get_asset(), 'representation')
            ppath = asset_container.get_editor_property('package_path')

            if ref not in references:
                # If the asset is not in the new layout, delete it.
                # Also check if the parent directory is empty, and delete that
                # as well, if it is.
                EditorAssetLibrary.delete_directory(ppath)

                parent = os.path.dirname(str(ppath))
                parent_content = EditorAssetLibrary.list_assets(
                    parent, recursive=False, include_folder=True
                )

                if len(parent_content) == 0:
                    EditorAssetLibrary.delete_directory(parent)
            else:
                # If the asset is in the new layout, search the instances in 
                # the JSON file, and create actors for them.
                for element in data:
                    if element.get('reference_fbx') == ref:
                        if ref not in loaded:
                            loaded.append(ref)

                        assets = EditorAssetLibrary.list_assets(
                            ppath, recursive=True, include_folder=False)

                        transform = element.get('transform')
                        family = element.get('family')

                        if family == 'model':
                            self._process_family(
                                assets, 'StaticMesh', transform)
                        elif family == 'rig':
                            self._process_family(
                                assets, 'SkeletalMesh', transform)

        self._process(source_path, destination_path, loaded)

        container_path = "{}/{}".format(container["namespace"],
                                        container["objectName"])
        # update metadata
        unreal_pipeline.imprint(
            container_path,
            {
                "representation": str(representation["_id"]),
                "parent": str(representation["parent"])
            })

        asset_content = EditorAssetLibrary.list_assets(
            destination_path, recursive=True, include_folder=False)

        for a in asset_content:
            EditorAssetLibrary.save_asset(a)

    def remove(self, container):
        """
        First, destroy all actors of the assets to be removed. Then, deletes
        the asset's directory.
        """
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        self._remove_actors(path)

        EditorAssetLibrary.delete_directory(path)

        asset_content = EditorAssetLibrary.list_assets(
            parent_path, recursive=False
        )

        if len(asset_content) == 0:
            EditorAssetLibrary.delete_directory(parent_path)
