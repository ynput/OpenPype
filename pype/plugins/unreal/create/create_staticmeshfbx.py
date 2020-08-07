import unreal
from pype.hosts.unreal.plugin import Creator
from avalon.unreal import (
    instantiate,
)


class CreateStaticMeshFBX(Creator):
    """Static FBX geometry"""

    name = "unrealStaticMeshMain"
    label = "Unreal - Static Mesh"
    family = "unrealStaticMesh"
    icon = "cube"
    asset_types = ["StaticMesh"]

    root = "/Game"
    suffix = "_INS"

    def __init__(self, *args, **kwargs):
        super(CreateStaticMeshFBX, self).__init__(*args, **kwargs)

    def process(self):

        name = self.data["subset"]

        selection = []
        if (self.options or {}).get("useSelection"):
            sel_objects = unreal.EditorUtilityLibrary.get_selected_assets()
            selection = [a.get_path_name() for a in sel_objects]

        unreal.log("selection: {}".format(selection))
        instantiate(self.root, name, self.data, selection, self.suffix)
