from pype.lib import abstract_collect_render, RenderInstance
import pyblish.api
from avalon import api
import os
import copy

from avalon import aftereffects

class CollectAERender(abstract_collect_render.AbstractCollectRender):

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect After Effects Render Layers"

    def get_instances(self, context):
        instances = []

        current_file = context.data["currentFile"]
        version = context.data["version"]
        asset_entity = context.data["assetEntity"]
        project_entity = context.data["projectEntity"]

        for inst in aftereffects.stub().get_metadata().values():
            if inst["family"] == "render" and inst["active"]:
                instance = RenderInstance(
                    version=version,
                    time="",
                    source=current_file,
                    label="{} - farm".format(inst["subset"]),
                    subset=inst["subset"],
                    asset=context.data["assetEntity"]["name"],
                    attachTo=False,
                    setMembers='',
                    publish=True,
                    renderer='aerender',
                    name=inst["subset"],
                    resolutionWidth=asset_entity["data"].get(
                        "resolutionWidth",
                        project_entity["data"]["resolutionWidth"]),
                    resolutionHeight=asset_entity["data"].get(
                        "resolutionHeight",
                        project_entity["data"]["resolutionHeight"]),
                    pixelAspect=1,
                    tileRendering=False,
                    tilesX=0,
                    tilesY=0,
                    frameStart=asset_entity["data"]["frameStart"],
                    frameEnd=asset_entity["data"]["frameEnd"],
                    frameStep=1
                    )
                instance._anatomy = context.data["anatomy"]
                instance._anatomyData = context.data["anatomyData"]
                instances.append(instance)

        return instances

    def get_expected_files(self, render_instance):
        anatomy = render_instance._anatomy
        anatomy_data = copy.deepcopy(render_instance._anatomyData)
        anatomy_data["family"] = render_instance.family
        anatomy_data["version"] = render_instance.version
        anatomy_data["subset"] = render_instance.subset
        padding = anatomy.templates.get("frame_padding", 4)
        anatomy_data.update({
            "frame": f"%0{padding}d",
            "representation": "aif"
        })

        anatomy_filled = anatomy.format(anatomy_data)
        import json
        print("anatomy_filled::{}".format(json.dumps(anatomy_filled, indent=4)))

        render_path = anatomy_filled["render"]["path"]
        return [render_path]
