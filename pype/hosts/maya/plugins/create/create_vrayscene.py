import avalon.maya


class CreateVRayScene(avalon.maya.Creator):

    label = "VRay Scene"
    family = "vrayscene"
    icon = "cubes"

    def __init__(self, *args, **kwargs):
        super(CreateVRayScene, self).__init__(*args, **kwargs)

        # We don't need subset or asset attributes
        self.data.pop("subset", None)
        self.data.pop("asset", None)
        self.data.pop("active", None)

        self.data.update({
            "id": "avalon.vrayscene",  # We won't be publishing this one
            "suspendRenderJob": False,
            "suspendPublishJob": False,
            "extendFrames": False,
            "pools": "",
            "framesPerTask": 1
        })

        self.options = {"useSelection": False}  # Force no content
