from openpype.hosts.maya.api import plugin
from openpype.api import get_project_settings
import os
import platform
import maya.cmds as cmds

class CreateTurnTable(plugin.Creator):
    """A Turntable render review for asset"""

    name = "TurnTableMain"
    label = "TurnTable"
    family = "rendering"
    icon = "video-camera"
    defaults = ["TurnTableMain"]



    def process(self):
        instance = super(CreateTurnTable, self).process()

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        ExtractTurntable_setting = settings['maya']['publish']['ExtractTurntable']

        path = ExtractTurntable_setting ['templateFile'].get(platform.system().lower())
        frames = ExtractTurntable_setting ['frames']
        modelTransform = ExtractTurntable_setting["modelTransform"]
        lightTransform = ExtractTurntable_setting["lightTransform"]


        # reference template file
        cmds.file(path,
                reference=True,
                groupReference=True,
                namespace="",
                groupName="_GRP",
        )
        # append selected model while creation and parent it to model grp
        cmds.parent(instance, modelTransform)


        # # get animation time and set key frames
        # cmds.setKeyframe(modelTransform, 0, frames/2, 0, 360, linear)
        # cmds.setKeyframe(lightTransform, frames/2, frames, 0, 360, linear)