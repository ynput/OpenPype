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

    root = "/Game/AvalonInstances"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateRender, self).__init__(*args, **kwargs)

    def process(self):
        name = self.data["subset"]

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        # Get the master sequence and the master level.
        # There should be only one sequence and one level in the directory.
        filter = unreal.ARFilter(
            class_names=["LevelSequence"],
            package_paths=[f"/Game/OpenPype/{self.data['asset']}"],
            recursive_paths=False)
        sequences = ar.get_assets(filter)
        ms = sequences[0].object_path
        filter = unreal.ARFilter(
            class_names=["World"],
            package_paths=[f"/Game/OpenPype/{self.data['asset']}"],
            recursive_paths=False)
        levels = ar.get_assets(filter)
        ml = levels[0].object_path

        selection = []
        if (self.options or {}).get("useSelection"):
            sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
            selection = [
                a.get_path_name() for a in sel_objects
                if a.get_class().get_name() in self.asset_types]

        unreal.log("selection: {}".format(selection))
        # instantiate(self.root, name, self.data, selection, self.suffix)
        # container_name = "{}{}".format(name, self.suffix)

        # if we specify assets, create new folder and move them there. If not,
        # just create empty folder
        # new_name = pipeline.create_folder(self.root, name)
        path = "{}/{}".format(self.root, name)
        unreal.EditorAssetLibrary.make_directory(path)

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        for a in selection:
            d = self.data.copy()
            d["members"] = [a]
            d["sequence"] = a
            d["master_sequence"] = ms
            d["master_level"] = ml
            asset = ar.get_asset_by_object_path(a).get_asset()
            asset_name = asset.get_name()

            # Get frame range. We need to go through the hierarchy and check
            # the frame range for the children.
            asset_data = legacy_io.find_one({
                "type": "asset",
                "name": asset_name
            })
            id = asset_data.get('_id')

            elements = list(
                legacy_io.find({"type": "asset", "data.visualParent": id}))

            if elements:
                start_frames = []
                end_frames = []
                for e in elements:
                    start_frames.append(e.get('data').get('clipIn'))
                    end_frames.append(e.get('data').get('clipOut'))

                    elements.extend(legacy_io.find({
                        "type": "asset",
                        "data.visualParent": e.get('_id')
                    }))

                min_frame = min(start_frames)
                max_frame = max(end_frames)
            else:
                min_frame = asset_data.get('data').get('clipIn')
                max_frame = asset_data.get('data').get('clipOut')

            d["startFrame"] = min_frame
            d["endFrame"] = max_frame

            container_name = f"{asset_name}{self.suffix}"
            pipeline.create_publish_instance(
                instance=container_name, path=path)
            pipeline.imprint("{}/{}".format(path, container_name), d)
