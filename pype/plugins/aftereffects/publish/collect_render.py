from pype.lib import abstract_collect_render
from pype.lib.abstract_collect_render import RenderInstance
import pyblish.api
import copy
import attr
import os

from avalon import aftereffects


@attr.s
class AERenderInstance(RenderInstance):
    # extend generic, composition name is needed
    comp_name = attr.ib(default=None)


class CollectAERender(abstract_collect_render.AbstractCollectRender):

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect After Effects Render Layers"
    hosts = ["aftereffects"]

    padding_width = 6
    rendered_extension = 'png'

    def get_instances(self, context):
        instances = []

        current_file = context.data["currentFile"]
        version = context.data["version"]
        asset_entity = context.data["assetEntity"]
        project_entity = context.data["projectEntity"]

        compositions = aftereffects.stub().get_items(True)
        compositions_by_id = {item.id: item for item in compositions}
        for item_id, inst in aftereffects.stub().get_metadata().items():
            schema = inst.get('schema')
            # loaded asset container skip it
            if schema and 'container' in schema:
                continue
            if inst["family"] == "render.farm" and inst["active"]:
                instance = AERenderInstance(
                    family=inst["family"],
                    families=[inst["family"]],
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
                    frameStart=int(asset_entity["data"]["frameStart"]),
                    frameEnd=int(asset_entity["data"]["frameEnd"]),
                    frameStep=1,
                    toBeRenderedOn='deadline'
                )

                comp = compositions_by_id.get(int(item_id))
                if not comp:
                    raise ValueError("There is no composition for item {}".
                                     format(item_id))
                instance.comp_name = comp.name
                instance._anatomy = context.data["anatomy"]
                instance.anatomyData = context.data["anatomyData"]

                instance.outputDir = self._get_output_dir(instance)

                instances.append(instance)

        return instances

    def get_expected_files(self, render_instance):
        """
            Returns list of rendered files that should be created by
            Deadline. These are not published directly, they are source
            for later 'submit_publish_job'.

        Args:
            render_instance (RenderInstance): to pull anatomy and parts used
                in url

        Returns:
            (list) of absolut urls to rendered file
        """
        start = render_instance.frameStart
        end = render_instance.frameEnd

        # render to folder of workfile
        base_dir = os.path.dirname(render_instance.source)
        expected_files = []
        for frame in range(start, end + 1):
            path = os.path.join(base_dir, "{}_{}_{}.{}.{}".format(
                        render_instance.asset,
                        render_instance.subset,
                        "v{:03d}".format(render_instance.version),
                        str(frame).zfill(self.padding_width),
                        self.rendered_extension
                    ))
            expected_files.append(path)

        return expected_files

    def _get_output_dir(self, render_instance):
        """
            Returns dir path of published asset. Required for
            'submit_publish_job'.

            It is different from rendered files (expectedFiles), these are
            collected first in some 'staging' area, published later.

        Args:
            render_instance (RenderInstance): to pull anatomy and parts used
                in url

        Returns:
            (str): absolute path to published files
        """
        anatomy = render_instance._anatomy
        anatomy_data = copy.deepcopy(render_instance.anatomyData)
        anatomy_data["family"] = render_instance.family
        anatomy_data["version"] = render_instance.version
        anatomy_data["subset"] = render_instance.subset

        anatomy_filled = anatomy.format(anatomy_data)

        # for submit_publish_job
        return anatomy_filled["render"]["folder"]
