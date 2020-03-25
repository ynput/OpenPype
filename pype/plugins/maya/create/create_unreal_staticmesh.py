import avalon.maya


class CreateUnrealStaticMesh(avalon.maya.Creator):
    name = "staticMeshMain"
    label = "Unreal - Static Mesh"
    family = "unrealStaticMesh"
    icon = "cube"

    def __init__(self, *args, **kwargs):
        super(CreateUnrealStaticMesh, self).__init__(*args, **kwargs)
