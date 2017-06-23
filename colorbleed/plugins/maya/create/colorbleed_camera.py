import avalon.maya


class CreateCamera(avalon.maya.Creator):
    """Single baked camera extraction"""

    name = "cameraDefault"
    label = "Camera"
    family = "colorbleed.camera"

    # def process(self):
    #     pass