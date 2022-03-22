# -*- coding: utf-8 -*-
"""Load camera from FBX."""
import os

from avalon import io
from openpype.pipeline import AVALON_CONTAINER_ID
from openpype.hosts.unreal.api import plugin
from openpype.hosts.unreal.api import pipeline as unreal_pipeline
import unreal  # noqa


class CameraLoader(plugin.Loader):
    """Load Unreal StaticMesh from FBX"""

    families = ["camera"]
    label = "Load Camera"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def load(self, context, name, namespace, data):
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

        # Create directory for asset and OpenPype container
        root = "/Game/OpenPype/Assets"
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()

        unique_number = 1

        if unreal.EditorAssetLibrary.does_directory_exist(f"{root}/{asset}"):
            asset_content = unreal.EditorAssetLibrary.list_assets(
                f"{root}/{asset}", recursive=False, include_folder=True
            )

            # Get highest number to make a unique name
            folders = [a for a in asset_content
                       if a[-1] == "/" and f"{name}_" in a]
            f_numbers = []
            for f in folders:
                # Get number from folder name. Splits the string by "_" and
                # removes the last element (which is a "/").
                f_numbers.append(int(f.split("_")[-1][:-1]))
            f_numbers.sort()
            if not f_numbers:
                unique_number = 1
            else:
                unique_number = f_numbers[-1] + 1

        asset_dir, container_name = tools.create_unique_asset_name(
            f"{root}/{asset}/{name}_{unique_number:02d}", suffix="")

        container_name += suffix

        unreal.EditorAssetLibrary.make_directory(asset_dir)

        sequence = tools.create_asset(
            asset_name=asset_name,
            package_path=asset_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        io_asset = io.Session["AVALON_ASSET"]
        asset_doc = io.find_one({
            "type": "asset",
            "name": io_asset
        })

        data = asset_doc.get("data")

        if data:
            sequence.set_display_rate(unreal.FrameRate(data.get("fps"), 1.0))
            sequence.set_playback_start(data.get("frameStart"))
            sequence.set_playback_end(data.get("frameEnd"))

        settings = unreal.MovieSceneUserImportFBXSettings()
        settings.set_editor_property('reduce_keys', False)

        unreal.SequencerTools.import_fbx(
            unreal.EditorLevelLibrary.get_editor_world(),
            sequence,
            sequence.get_bindings(),
            settings,
            self.fname
        )

        # Create Asset Container
        unreal_pipeline.create_container(
            container=container_name, path=asset_dir)

        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
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

        asset_content = unreal.EditorAssetLibrary.list_assets(
            asset_dir, recursive=True, include_folder=True
        )

        for a in asset_content:
            unreal.EditorAssetLibrary.save_asset(a)

        return asset_content

    def update(self, container, representation):
        path = container["namespace"]

        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        tools = unreal.AssetToolsHelpers().get_asset_tools()

        asset_content = unreal.EditorAssetLibrary.list_assets(
            path, recursive=False, include_folder=False
        )
        asset_name = ""
        for a in asset_content:
            asset = ar.get_asset_by_object_path(a)
            if a.endswith("_CON"):
                loaded_asset = unreal.EditorAssetLibrary.load_asset(a)
                unreal.EditorAssetLibrary.set_metadata_tag(
                    loaded_asset, "representation", str(representation["_id"])
                )
                unreal.EditorAssetLibrary.set_metadata_tag(
                    loaded_asset, "parent", str(representation["parent"])
                )
                asset_name = unreal.EditorAssetLibrary.get_metadata_tag(
                    loaded_asset, "asset_name"
                )
            elif asset.asset_class == "LevelSequence":
                unreal.EditorAssetLibrary.delete_asset(a)

        sequence = tools.create_asset(
            asset_name=asset_name,
            package_path=path,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        io_asset = io.Session["AVALON_ASSET"]
        asset_doc = io.find_one({
            "type": "asset",
            "name": io_asset
        })

        data = asset_doc.get("data")

        if data:
            sequence.set_display_rate(unreal.FrameRate(data.get("fps"), 1.0))
            sequence.set_playback_start(data.get("frameStart"))
            sequence.set_playback_end(data.get("frameEnd"))

        settings = unreal.MovieSceneUserImportFBXSettings()
        settings.set_editor_property('reduce_keys', False)

        unreal.SequencerTools.import_fbx(
            unreal.EditorLevelLibrary.get_editor_world(),
            sequence,
            sequence.get_bindings(),
            settings,
            str(representation["data"]["path"])
        )

    def remove(self, container):
        path = container["namespace"]
        parent_path = os.path.dirname(path)

        unreal.EditorAssetLibrary.delete_directory(path)

        asset_content = unreal.EditorAssetLibrary.list_assets(
            parent_path, recursive=False, include_folder=True
        )

        if len(asset_content) == 0:
            unreal.EditorAssetLibrary.delete_directory(parent_path)
