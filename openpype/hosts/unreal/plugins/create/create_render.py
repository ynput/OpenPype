import unreal

from openpype.pipeline import legacy_io
from openpype.hosts.unreal.api import pipeline
from openpype.hosts.unreal.api.plugin import Creator


class CreateRender(Creator):
    """Create instance for sequence for rendering"""

    name = "unrealRender"
    label = "Unreal - Render"
    family = "render"
    icon = "cube"
    asset_types = ["LevelSequence"]

    root = "/Game/OpenPype/PublishInstances"
    suffix = "_INS"

    def process(self):
        subset = self.data["subset"]

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        # Get the master sequence and the master level.
        # There should be only one sequence and one level in the directory.
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"/Game/OpenPype/{self.data['asset']}"],
            recursive_paths=False)
        sequences = ar.get_assets(filter)
        ms = sequences[0].get_editor_property('object_path')
        filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[f"/Game/OpenPype/{self.data['asset']}"],
            recursive_paths=False)
        levels = ar.get_assets(filter)
        ml = levels[0].get_editor_property('object_path')

        selection = []
        if (self.options or {}).get("useSelection"):
            sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
            selection = [
                a.get_path_name() for a in sel_objects
                if a.get_class().get_name() in self.asset_types]
        else:
            selection.append(self.data['sequence'])

        unreal.log(f"selection: {selection}")

        path = f"{self.root}"
        unreal.EditorAssetLibrary.make_directory(path)

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        for a in selection:
            ms_obj = ar.get_asset_by_object_path(ms).get_asset()

            seq_data = None

            if a == ms:
                seq_data = {
                    "sequence": ms_obj,
                    "output": f"{ms_obj.get_name()}",
                    "frame_range": (
                        ms_obj.get_playback_start(), ms_obj.get_playback_end())
                }
            else:
                seq_data_list = [{
                    "sequence": ms_obj,
                    "output": f"{ms_obj.get_name()}",
                    "frame_range": (
                        ms_obj.get_playback_start(), ms_obj.get_playback_end())
                }]

                for s in seq_data_list:
                    subscenes = pipeline.get_subsequences(s.get('sequence'))

                    for ss in subscenes:
                        curr_data = {
                            "sequence": ss.get_sequence(),
                            "output": (f"{s.get('output')}/"
                                       f"{ss.get_sequence().get_name()}"),
                            "frame_range": (
                                ss.get_start_frame(), ss.get_end_frame() - 1)
                        }

                        if ss.get_sequence().get_path_name() == a:
                            seq_data = curr_data
                            break
                        seq_data_list.append(curr_data)

                    if seq_data is not None:
                        break

            if not seq_data:
                continue

            d = self.data.copy()
            d["members"] = [a]
            d["sequence"] = a
            d["master_sequence"] = ms
            d["master_level"] = ml
            d["output"] = seq_data.get('output')
            d["frameStart"] = seq_data.get('frame_range')[0]
            d["frameEnd"] = seq_data.get('frame_range')[1]

            container_name = f"{subset}{self.suffix}"
            pipeline.create_publish_instance(
                instance=container_name, path=path)
            pipeline.imprint(f"{path}/{container_name}", d)
