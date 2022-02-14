from openpype.hosts.maya.api import plugin
from openpype.api import get_project_settings
from openpype.lib import get_creator_by_name
import avalon.api

import os
import functools
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
        ExtractTurntable_setting = settings['maya']['publish']['ExtractTurntable']

        path = ExtractTurntable_setting ['templateFile'].get(platform.system().lower())
        frames = ExtractTurntable_setting ['frames']
        modelTransform = ExtractTurntable_setting["modelTransform"]
        lightTransform = ExtractTurntable_setting["lightTransform"]
        cameraShape = ExtractTurntable_setting["cameraShape"]

        namespace="turntable"
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

        ## fit camera to object
        fit_factor=0.5
        cmds.viewFit( namespace +":"+ cameraShape, f=fit_factor)

        cmds.delete(instance)

        def with_avalon(func):
            @functools.wraps(func)
            def wrap_avalon(*args, **kwargs):
                global avalon
                if avalon is None:
                    import avalon
                return func(*args, **kwargs)
            return wrap_avalon

        @with_avalon
        def get_creator_by_name(creator_name, case_sensitive=False, use_cache=False):
            """Find creator plugin by name.

            Args:
                creator_name (str): Name of creator class that should be returned.
                case_sensitive (bool): Match of creator plugin name is case sensitive.
                    Set to `False` by default.

            Returns:
                Creator: Return first matching plugin or `None`.
            """
            # Lower input creator name if is not case sensitive
            if not case_sensitive:
                creator_name = creator_name.lower()

            creator_plugins = None
            if use_cache:
                from avalon.pipeline import last_discovered_plugins
                creator_plugins = last_discovered_plugins.get(avalon.api.Creator.__name__)

            if creator_plugins is None:
                creator_plugins = avalon.api.discover(avalon.api.Creator)

            for creator_plugin in creator_plugins:
                _creator_name = creator_plugin.__name__

                # Lower creator plugin name if is not case sensitive
                if not case_sensitive:
                    _creator_name = _creator_name.lower()

                if _creator_name == creator_name:
                    return creator_plugin
            return None

        Creator = get_creator_by_name("CreateRender", use_cache=True)
        self.log.info("creator is .. " + str(Creator))

        container = create(Creator,
                    name="renderingTurnTable",
                    asset=asset)
