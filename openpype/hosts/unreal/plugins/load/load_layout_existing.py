# -*- coding: utf-8 -*-
"""Loader for apply layout to already existing assets."""
import json
from pathlib import Path

from openpype.client import get_representations
from openpype.pipeline import (
    discover_loader_plugins,
    loaders_from_representation,
    load_container,
    get_representation_path,
    AYON_CONTAINER_ID,
    get_current_project_name,
)
from openpype.hosts.unreal.api.plugin import UnrealBaseLoader
from openpype.hosts.unreal.api.pipeline import (
    send_request,
    containerise,
)


class ExistingLayoutLoader(UnrealBaseLoader):
    """
    Load Layout for an existing scene, and match the existing assets.
    """

    families = ["layout"]
    representations = ["json"]

    label = "Load Layout on Existing Scene"
    icon = "code-fork"
    color = "orange"

    delete_unmatched_assets = True

    @classmethod
    def apply_settings(cls, project_settings, *args, **kwargs):
        super(ExistingLayoutLoader, cls).apply_settings(
            project_settings, *args, **kwargs
        )
        cls.delete_unmatched_assets = (
            project_settings["unreal"]["delete_unmatched_assets"]
        )

    def _create_container(
        self, asset_name, asset_dir, asset, representation, parent, family
    ):
        container_name = f"{asset_name}_CON"

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": asset_dir,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": self.__class__.__name__,
            "representation_id": representation,
            "version_id": parent,
            "family": family
        }

        container = containerise(asset_dir, container_name, data)

        return container.get_path_name()

    @staticmethod
    def _get_fbx_loader(loaders, family):
        name = ""
        if family == 'camera':
            name = "CameraLoader"
        elif family == 'model':
            name = "StaticMeshFBXLoader"
        elif family == 'rig':
            name = "SkeletalMeshFBXLoader"
        return (
            next(
                (
                    loader for loader in loaders if loader.__name__ == name
                ),
                None
            )
            if name
            else None
        )

    @staticmethod
    def _get_abc_loader(loaders, family):
        name = ""
        if family == 'model':
            name = "StaticMeshAlembicLoader"
        elif family == 'rig':
            name = "SkeletalMeshAlembicLoader"
        return (
            next(
                (
                    loader for loader in loaders if loader.__name__ == name
                ),
                None
            )
            if name
            else None
        )

    def _get_representation(self, element, repre_docs_by_version_id):
        representation = None
        repr_format = None
        if element.get('representation'):
            repre_docs = repre_docs_by_version_id[element.get("version")]
            if not repre_docs:
                self.log.error(
                    f"No valid representation found for version "
                    f"{element.get('version')}")
                return None, None
            repre_doc = repre_docs[0]
            representation = str(repre_doc["_id"])
            repr_format = repre_doc["name"]

        # This is to keep compatibility with old versions of the
        # json format.
        elif element.get('reference_fbx'):
            representation = element.get('reference_fbx')
            repr_format = 'fbx'
        elif element.get('reference_abc'):
            representation = element.get('reference_abc')
            repr_format = 'abc'

        return representation, repr_format

    def _load_representation(
        self, family, representation, repr_format, instance_name, all_loaders
    ):
        loaders = loaders_from_representation(
            all_loaders, representation)

        loader = None

        if repr_format == 'fbx':
            loader = self._get_fbx_loader(loaders, family)
        elif repr_format == 'abc':
            loader = self._get_abc_loader(loaders, family)

        if not loader:
            self.log.error(
                f"No valid loader found for {representation}")
            return []

        return load_container(loader, representation, namespace=instance_name)

    @staticmethod
    def _get_valid_repre_docs(project_name, version_ids):
        valid_formats = ['fbx', 'abc']

        repre_docs = list(get_representations(
            project_name,
            representation_names=valid_formats,
            version_ids=version_ids
        ))

        return {
            str(repre_doc["parent"]): repre_doc for repre_doc in repre_docs}

    @staticmethod
    def _get_layout_data(data, project_name):
        assets = []
        repre_ids = set()

        # Get all the representations in the JSON from the database.
        for asset in data:
            if repre_id := asset.get('representation'):
                repre_ids.add(repre_id)
                assets.append(asset)

        repre_docs = get_representations(
            project_name, representation_ids=repre_ids
        )
        repre_docs_by_id = {
            str(repre_doc["_id"]): repre_doc
            for repre_doc in repre_docs
        }

        layout_data = []
        version_ids = set()
        for asset in assets:
            repre_id = asset.get("representation")
            repre_doc = repre_docs_by_id.get(repre_id)
            if not repre_doc:
                raise AssertionError("Representation not found")
            if not repre_doc.get('data') and not repre_doc['data'].get('path'):
                raise AssertionError("Representation does not have path")
            if not repre_doc.get('context'):
                raise AssertionError("Representation does not have context")

            layout_data.append((repre_doc, asset))
            version_ids.add(repre_doc["parent"])

        return layout_data, version_ids

    def _process(self, lib_path, project_name):
        with open(lib_path, "r") as fp:
            data = json.load(fp)

        all_loaders = discover_loader_plugins()

        layout_data, version_ids = self._get_layout_data(data, project_name)

        # Prequery valid repre documents for all elements at once
        valid_repre_doc_by_version_id = self._get_valid_repre_docs(
            project_name, version_ids)

        containers = []
        actors_matched = []

        for (repr_data, lasset) in layout_data:
            # For every actor in the scene, check if it has a representation
            # in those we got from the JSON. If so, create a container for it.
            # Otherwise, remove it from the scene.

            matched, mesh_path = send_request(
                "match_actor",
                params={
                    "actors_matched": actors_matched,
                    "lasset": lasset,
                    "repr_data": repr_data})

            # If an actor has not been found for this representation,
            # we check if it has been loaded already by checking all the
            # loaded containers. If so, we add it to the scene. Otherwise,
            # we load it.
            if matched:
                asset = repr_data.get('context').get('asset')
                subset = repr_data.get('context').get('subset')
                container = self._create_container(
                    f"{asset}_{subset}", mesh_path, asset,
                    repr_data.get('_id'), repr_data.get('parent'),
                    repr_data.get('context').get('family')
                )
                containers.append(container)

                continue

            loaded = send_request(
                "spawn_actors",
                params={
                    "repr_data": repr_data,
                    "lasset": lasset})

            if loaded:
                # The asset was already loaded, and we spawned it in the scene,
                # so we can continue.
                continue

            # If we get here, it means that the asset was not loaded yet,
            # so we load it and spawn it in the scene.
            representation, repr_format = self._get_representation(
                lasset, valid_repre_doc_by_version_id)

            family = lasset.get('family')
            instance_name = lasset.get('instance_name')

            assets = self._load_representation(
                family, representation, repr_format, instance_name,
                all_loaders)

            send_request(
                "spawn_actors",
                params={
                    "assets": assets, "lasset": lasset})

        # Remove not matched actors, if the option is set.
        if self.delete_unmatched_assets:
            send_request(
                "remove_unmatched_actors",
                params={"actors_matched": actors_matched})

        return containers

    def load(self, context, name=None, namespace=None, options=None):
        """Load and containerise representation into Content Browser.

        Load and apply layout to already existing assets in Unreal.
        It will create a container for each asset in the scene, and a
        container for the layout.

        Args:
            context (dict): application context
            name (str): subset name
            namespace (str): in Unreal this is basically path to container.
                             This is not passed here, so namespace is set
                             by `containerise()` because only then we know
                             real path.
            options (dict): Those would be data to be imprinted. This is not
                            used now, data are imprinted by `containerise()`.
        """
        asset = context.get('asset').get('name')
        asset_name = f"{asset}_{name}" if asset else name

        container_name = f"{asset}_{name}_CON"

        curr_level = send_request("get_current_level")

        if not curr_level:
            raise AssertionError("Current level not saved")

        project_name = context["project"]["name"]
        path = self.filepath_from_context(context)
        containers = self._process(path, project_name)

        curr_level_path = Path(curr_level).parent.as_posix()

        data = {
            "schema": "ayon:container-2.0",
            "id": AYON_CONTAINER_ID,
            "asset": asset,
            "namespace": curr_level_path,
            "container_name": container_name,
            "asset_name": asset_name,
            "loader": str(self.__class__.__name__),
            "representation_id": str(context["representation"]["_id"]),
            "version_id": str(context["representation"]["parent"]),
            "family": context["representation"]["context"]["family"],
            "loaded_assets": containers
        }

        containerise(curr_level_path, container_name, data)

    def update(self, container, representation):
        asset_dir = container.get('namespace')
        container_name = container['objectName']

        source_path = get_representation_path(representation)
        project_name = get_current_project_name()
        containers = self._process(source_path, project_name)

        data = {
            "representation_id": str(representation["_id"]),
            "version_id": str(representation["parent"]),
            "loaded_assets": containers
        }

        containerise(asset_dir, container_name, data)
