import json
from pathlib import Path

import unreal
from unreal import EditorLevelLibrary

from openpype.client import get_representations
from openpype.pipeline import (
    discover_loader_plugins,
    loaders_from_representation,
    load_container,
    get_representation_path,
    AYON_CONTAINER_ID,
    legacy_io,
)
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as upipeline


class ExistingLayoutLoader(plugin.Loader):
    """
    Load Layout for an existing scene, and match the existing assets.
    """

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout on Existing Scene"
    icon = "code-fork"
    color = "orange"
    ASSET_ROOT = "/Game/Ayon"

    delete_unmatched_assets = True

    @classmethod
    def apply_settings(cls, project_settings, *args, **kwargs):
        super(ExistingLayoutLoader, cls).apply_settings(
            project_settings, *args, **kwargs
        )
        cls.delete_unmatched_assets = (
            project_settings["unreal"]["delete_unmatched_assets"]
        )

    @staticmethod
    def _create_container(
        asset_name, asset_dir, asset, representation, parent, family
    ):
        container_name = f"{asset_name}_CON"

        container = None
        if not unreal.EditorAssetLibrary.does_asset_exist(
            f"{asset_dir}/{container_name}"
        ):
            container = upipeline.create_container(container_name, asset_dir)
        else:
            ar = unreal.AssetRegistryHelpers.get_asset_registry()
            obj = ar.get_asset_by_object_path(
                f"{asset_dir}/{container_name}.{container_name}")
            container = obj.get_asset()

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            # "loader": str(self.__class__.__name__),
            "representation": representation,
            "parent": parent,
            "family": family
        }

        upipeline.imprint(
            "{}/{}".format(asset_dir, container_name), data)

        return container.get_path_name()

    @staticmethod
    def _get_current_level():
        ue_version = unreal.SystemLibrary.get_engine_version().split('.')
        ue_major = ue_version[0]

        if ue_major == '4':
            return EditorLevelLibrary.get_editor_world()
        elif ue_major == '5':
            return unreal.LevelEditorSubsystem().get_current_level()

        raise NotImplementedError(
            f"Unreal version {ue_major} not supported")

    def _transform_from_basis(self, transform, basis):
        """Transform a transform from a basis to a new basis."""
        # Get the basis matrix
        basis_matrix = unreal.Matrix(
            basis[0],
            basis[1],
            basis[2],
            basis[3]
        )
        transform_matrix = unreal.Matrix(
            transform[0],
            transform[1],
            transform[2],
            transform[3]
        )

        new_transform = (
            basis_matrix.get_inverse() * transform_matrix * basis_matrix)

        return new_transform.transform()

    def _spawn_actor(self, obj, lasset):
        actor = EditorLevelLibrary.spawn_actor_from_object(
            obj, unreal.Vector(0.0, 0.0, 0.0)
        )

        actor.set_actor_label(lasset.get('instance_name'))

        transform = lasset.get('transform_matrix')
        basis = lasset.get('basis')

        computed_transform = self._transform_from_basis(transform, basis)

        actor.set_actor_transform(computed_transform, False, True)

    @staticmethod
    def _get_fbx_loader(loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshFBXLoader"
        elif family == 'model' or family == 'staticMesh':
            name = "StaticMeshFBXLoader"
        elif family == 'camera':
            name = "CameraLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    @staticmethod
    def _get_abc_loader(loaders, family):
        name = ""
        if family == 'rig':
            name = "SkeletalMeshAlembicLoader"
        elif family == 'model':
            name = "StaticMeshAlembicLoader"

        if name == "":
            return None

        for loader in loaders:
            if loader.__name__ == name:
                return loader

        return None

    def _load_asset(self, repr_data, representation, instance_name, family):
        repr_format = repr_data.get('name')

        all_loaders = discover_loader_plugins()
        loaders = loaders_from_representation(
            all_loaders, representation)

        loader = None

        if repr_format == 'fbx':
            loader = self._get_fbx_loader(loaders, family)
        elif repr_format == 'abc':
            loader = self._get_abc_loader(loaders, family)

        if not loader:
            self.log.error(f"No valid loader found for {representation}")
            return []

        # This option is necessary to avoid importing the assets with a
        # different conversion compared to the other assets. For ABC files,
        # it is in fact impossible to access the conversion settings. So,
        # we must assume that the Maya conversion settings have been applied.
        options = {
            "default_conversion": True
        }

        assets = load_container(
            loader,
            representation,
            namespace=instance_name,
            options=options
        )

        return assets

    def _get_valid_repre_docs(self, project_name, version_ids):
        valid_formats = ['fbx', 'abc']

        repre_docs = list(get_representations(
            project_name,
            representation_names=valid_formats,
            version_ids=version_ids
        ))
        repre_doc_by_version_id = {}
        for repre_doc in repre_docs:
            version_id = str(repre_doc["parent"])
            repre_doc_by_version_id[version_id] = repre_doc
        return repre_doc_by_version_id

    def _process(self, lib_path, project_name):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        actors = EditorLevelLibrary.get_all_level_actors()

        with open(lib_path, "r") as fp:
            data = json.load(fp)

        elements = []
        repre_ids = set()
        # Get all the representations in the JSON from the database.
        for element in data:
            repre_id = element.get('representation')
            if repre_id:
                repre_ids.add(repre_id)
                elements.append(element)

        repre_docs = get_representations(
            project_name, representation_ids=repre_ids
        )
        repre_docs_by_id = {
            str(repre_doc["_id"]): repre_doc
            for repre_doc in repre_docs
        }
        layout_data = []
        version_ids = set()
        for element in elements:
            repre_id = element.get("representation")
            repre_doc = repre_docs_by_id.get(repre_id)
            if not repre_doc:
                raise AssertionError("Representation not found")
            if not (repre_doc.get('data') or repre_doc['data'].get('path')):
                raise AssertionError("Representation does not have path")
            if not repre_doc.get('context'):
                raise AssertionError("Representation does not have context")

            layout_data.append((repre_doc, element))
            version_ids.add(repre_doc["parent"])

        # Prequery valid repre documents for all elements at once
        valid_repre_doc_by_version_id = self._get_valid_repre_docs(
            project_name, version_ids)
        containers = []
        actors_matched = []

        for (repr_data, lasset) in layout_data:
            # For every actor in the scene, check if it has a representation in
            # those we got from the JSON. If so, create a container for it.
            # Otherwise, remove it from the scene.
            found = False

            for actor in actors:
                if not actor.get_class().get_name() == 'StaticMeshActor':
                    continue
                if actor in actors_matched:
                    continue

                # Get the original path of the file from which the asset has
                # been imported.
                smc = actor.get_editor_property('static_mesh_component')
                mesh = smc.get_editor_property('static_mesh')
                import_data = mesh.get_editor_property('asset_import_data')
                filename = import_data.get_first_filename()
                path = Path(filename)

                if (not path.name or
                        path.name not in repr_data.get('data').get('path')):
                    continue

                actor.set_actor_label(lasset.get('instance_name'))

                mesh_path = Path(mesh.get_path_name()).parent.as_posix()

                # Create the container for the asset.
                asset = repr_data.get('context').get('asset')
                subset = repr_data.get('context').get('subset')
                container = self._create_container(
                    f"{asset}_{subset}", mesh_path, asset,
                    repr_data.get('_id'), repr_data.get('parent'),
                    repr_data.get('context').get('family')
                )
                containers.append(container)

                # Set the transform for the actor.
                transform = lasset.get('transform_matrix')
                basis = lasset.get('basis')

                computed_transform = self._transform_from_basis(
                    transform, basis)
                actor.set_actor_transform(computed_transform, False, True)

                actors_matched.append(actor)
                found = True
                break

            # If an actor has not been found for this representation,
            # we check if it has been loaded already by checking all the
            # loaded containers. If so, we add it to the scene. Otherwise,
            # we load it.
            if found:
                continue

            all_containers = upipeline.ls()

            loaded = False

            for container in all_containers:
                repr = container.get('representation')

                if not repr == str(repr_data.get('_id')):
                    continue

                asset_dir = container.get('namespace')

                filter = unreal.ARFilter(
                    class_names=["StaticMesh"],
                    package_paths=[asset_dir],
                    recursive_paths=False)
                assets = ar.get_assets(filter)

                for asset in assets:
                    obj = asset.get_asset()
                    self._spawn_actor(obj, lasset)

                loaded = True
                break

            # If the asset has not been loaded yet, we load it.
            if loaded:
                continue

            assets = self._load_asset(
                valid_repre_doc_by_version_id.get(lasset.get('version')),
                lasset.get('representation'),
                lasset.get('instance_name'),
                lasset.get('family')
            )

            for asset in assets:
                obj = ar.get_asset_by_object_path(asset).get_asset()
                if not obj.get_class().get_name() == 'StaticMesh':
                    continue
                self._spawn_actor(obj, lasset)

                break

        # Check if an actor was not matched to a representation.
        # If so, remove it from the scene.
        for actor in actors:
            if not actor.get_class().get_name() == 'StaticMeshActor':
                continue
            if actor not in actors_matched:
                self.log.warning(f"Actor {actor.get_name()} not matched.")
                if self.delete_unmatched_assets:
                    EditorLevelLibrary.destroy_actor(actor)

        return containers

    def load(self, context, name, namespace, options):
        print("Loading Layout and Match Assets")

        asset = context.get('asset').get('name')
        asset_name = f"{asset}_{name}" if asset else name
        container_name = f"{asset}_{name}_CON"

        curr_level = self._get_current_level()

        if not curr_level:
            raise AssertionError("Current level not saved")

        project_name = context["project"]["name"]
        path = self.filepath_from_context(context)
        containers = self._process(path, project_name)

        curr_level_path = Path(
            curr_level.get_outer().get_path_name()).parent.as_posix()

        if not unreal.EditorAssetLibrary.does_asset_exist(
            f"{curr_level_path}/{container_name}"
        ):
            upipeline.create_container(
                container=container_name, path=curr_level_path)

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": curr_level_path,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["_id"],
            "parent": context["representation"]["parent"],
            "family": context["representation"]["context"]["family"],
            "loaded_assets": containers
        }
        upipeline.imprint(f"{curr_level_path}/{container_name}", data)

    def update(self, container, representation):
        asset_dir = container.get('namespace')

        source_path = get_representation_path(representation)
        project_name = legacy_io.active_project()
        containers = self._process(source_path, project_name)

        data = {
            "representation": str(representation["_id"]),
            "parent": str(representation["parent"]),
            "loaded_assets": containers
        }
        upipeline.imprint(
            "{}/{}".format(asset_dir, container.get('container_name')), data)
