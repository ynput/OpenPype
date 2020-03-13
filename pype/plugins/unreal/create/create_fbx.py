from pype.unreal.plugin import Creator


class CreateFbx(Creator):
    """Static FBX geometry"""

    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"
    asset_types = ["StaticMesh"]

    def __init__(self, *args, **kwargs):
        super(CreateFbx, self).__init__(*args, **kwargs)
