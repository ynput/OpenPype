import unreal
from openpype.hosts.unreal.api.plugin import Creator
from avalon.unreal import pipeline


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

        print(self.data)

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
            d["map"] = unreal.EditorLevelLibrary.get_editor_world().get_path_name()
            asset = ar.get_asset_by_object_path(a).get_asset()
            container_name = f"{asset.get_name()}{self.suffix}"
            pipeline.create_publish_instance(instance=container_name, path=path)
            pipeline.imprint("{}/{}".format(path, container_name), d)
