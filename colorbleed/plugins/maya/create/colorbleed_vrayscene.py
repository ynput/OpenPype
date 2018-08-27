from collections import OrderedDict

import avalon.maya


class CreateVRayScene(avalon.maya.Creator):

    label = "VRay Scene"
    family = "colorbleed.vrayscene"
    # icon = "blocks"

    def __init__(self, *args, **kwargs):
        super(CreateVRayScene, self).__init__(*args, **kwargs)

        # We won't be publishing this one
        self.data["id"] = "avalon.vrayscene"

        # We don't need subset or asset attributes
        self.data.pop("subset", None)
        self.data.pop("asset", None)

        data = OrderedDict(**self.data)

        data["camera"] = self._get_camera()
        data["suspendRenderJob"] = False
        data["suspendPublishJob"] = False
        data["includeDefaultRenderLayer"] = False
        data["extendFrames"] = False
        data["pools"] = ""

        self.data = data

        self.options = {"useSelection": False}  # Force no content

    def _get_camera(self):
        from maya import cmds

        return [c for c in cmds.ls(type="camera")
                if cmds.getAttr("%s.renderable" % c)]
