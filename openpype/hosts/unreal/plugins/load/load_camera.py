import os

from avalon import api, io, pipeline
from avalon.unreal import lib
from avalon.unreal import pipeline as unreal_pipeline
import unreal


class CameraLoader(api.Loader):
    """Load Unreal StaticMesh from FBX"""

    families = ["camera"]
    label = "Load Camera"
    representations = ["fbx"]
    icon = "cube"
    color = "orange"

    def _get_data(self, asset_name):
        asset_doc = io.find_one({
            "type": "asset",
            "name": asset_name
        })

        return asset_doc.get("data")

    def _set_sequence_hierarchy(self, seq_i, seq_j, data_i, data_j):
        if data_i:
            seq_i.set_display_rate(unreal.FrameRate(data_i.get("fps"), 1.0))
            seq_i.set_playback_start(data_i.get("frameStart"))
            seq_i.set_playback_end(data_i.get("frameEnd") + 1)

        tracks = seq_i.get_master_tracks()
        track = None
        for t in tracks:
            if t.get_class() == unreal.MovieSceneSubTrack.static_class():
                track = t
                break
        if not track:
            track = seq_i.add_master_track(unreal.MovieSceneSubTrack)

        subscenes = track.get_sections()
        subscene = None
        for s in subscenes:
            if s.get_editor_property('sub_sequence') == seq_j:
                subscene = s
                break
        if not subscene:
            subscene = track.add_section()
            subscene.set_row_index(len(track.get_sections()))
            subscene.set_editor_property('sub_sequence', seq_j)
            subscene.set_range(
                data_j.get("frameStart"),
                data_j.get("frameEnd") + 1)

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

        # Create directory for asset and avalon container
        hierarchy = context.get('asset').get('data').get('parents')
        root = "/Game/Avalon"
        hierarchy_dir = root
        hierarchy_list = []
        for h in hierarchy:
            hierarchy_dir = f"{hierarchy_dir}/{h}"
            hierarchy_list.append(hierarchy_dir)
        asset = context.get('asset').get('name')
        suffix = "_CON"
        if asset:
            asset_name = "{}_{}".format(asset, name)
        else:
            asset_name = "{}".format(name)

        tools = unreal.AssetToolsHelpers().get_asset_tools()

        # Create a unique name for the camera directory
        unique_number = 1
        if unreal.EditorAssetLibrary.does_directory_exist(f"{hierarchy_dir}/{asset}"):
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
            f"{hierarchy_dir}/{asset}/{name}_{unique_number:02d}", suffix="")

        container_name += suffix

        # Get all the sequences in the hierarchy. It will create them, if 
        # they don't exist.
        sequences = []
        i = 0
        for h in hierarchy_list:
            root_content = unreal.EditorAssetLibrary.list_assets(
                h, recursive=False, include_folder=False)

            existing_sequences = [
                unreal.EditorAssetLibrary.find_asset_data(asset)
                for asset in root_content
                if unreal.EditorAssetLibrary.find_asset_data(
                    asset).get_class().get_name() == 'LevelSequence'
            ]

            if not existing_sequences:
                scene = tools.create_asset(
                    asset_name=hierarchy[i],
                    package_path=h,
                    asset_class=unreal.LevelSequence,
                    factory=unreal.LevelSequenceFactoryNew()
                )
                sequences.append(scene)
            else:
                for e in existing_sequences:
                    sequences.append(e.get_asset())

            i += 1

        unreal.EditorAssetLibrary.make_directory(asset_dir)

        cam_seq = tools.create_asset(
            asset_name=f"{asset}_camera",
            package_path=asset_dir,
            asset_class=unreal.LevelSequence,
            factory=unreal.LevelSequenceFactoryNew()
        )

        # Add sequences data to hierarchy
        data_i = self._get_data(sequences[0].get_name())

        for i in range(0, len(sequences) - 1):
            data_j = self._get_data(sequences[i + 1].get_name())

            self._set_sequence_hierarchy(
                sequences[i], sequences[i + 1], data_i, data_j)

            data_i = data_j

        parent_data = self._get_data(sequences[-1].get_name())
        data = self._get_data(asset)
        self._set_sequence_hierarchy(
                sequences[-1], cam_seq, parent_data, data)

        settings = unreal.MovieSceneUserImportFBXSettings()
        settings.set_editor_property('reduce_keys', False)

        if cam_seq:
            unreal.SequencerTools.import_fbx(
                unreal.EditorLevelLibrary.get_editor_world(),
                cam_seq,
                cam_seq.get_bindings(),
                settings,
                self.fname
            )

        # Create Asset Container
        lib.create_avalon_container(container=container_name, path=asset_dir)

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
