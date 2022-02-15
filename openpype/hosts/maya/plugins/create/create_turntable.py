from openpype.hosts.maya.api import plugin
from openpype.api import get_project_settings
from openpype.lib import get_creator_by_name
import avalon.api

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
        asset = avalon.api.Session["AVALON_ASSET"]
        create = avalon.api.create
        instance = super(CreateTurnTable, self).process()

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        CreateTurntable_setting = settings['maya']['create']['CreateTurntable']

        path = CreateTurntable_setting ['templateFile'].get(platform.system().lower())
        frames = CreateTurntable_setting ['frames']
        modelTransform = CreateTurntable_setting["modelTransform"]
        lightTransform = CreateTurntable_setting["lightTransform"]
        cameraShape = CreateTurntable_setting["cameraShape"]
        fit_factor = CreateTurntable_setting["fitFactor"]

        namespace="turntable"
        if path :
            # reference template file
            cmds.file(path,
                    reference=True,
                    groupReference=True,
                    namespace=namespace,
                    groupName="_GRP",
            )

            # # get animation time and set key frames
            cmds.setKeyframe(instance, t=1001, v=0.0, at="ry", itt="linear", ott="linear")
            cmds.setKeyframe(instance, t=int(int(frames)/2)+1001, v=360.0 , at="ry", itt="linear", ott="linear")
            cmds.setKeyframe(namespace +":"+ modelTransform, t=1001, v=0.0, at="ry", itt="linear", ott="linear")
            cmds.setKeyframe(namespace +":"+ modelTransform, t=int(int(frames)/2)+1001, v=360.0 , at="ry", itt="linear", ott="linear")

            ## second turn
            cmds.setKeyframe(namespace +":"+ lightTransform, t=int(int(frames)/2)+1001, v=0.0, at="ry", itt="linear", ott="linear")
            cmds.setKeyframe(namespace +":"+ lightTransform, t=int(frames)+1001, v=360.0 , at="ry", itt="linear", ott="linear")

            ## fit camera to content
            content = cmds.sets(instance, query=True)
            cmds.select(content, r=1)
            cmds.viewFit( namespace +":"+ cameraShape, f=fit_factor)

            cmds.delete(instance)

            Creator = get_creator_by_name("CreateRender")

            container = create(Creator,
                        name=self.name,
                        asset=asset,
                        options= {"useSelection":True})
