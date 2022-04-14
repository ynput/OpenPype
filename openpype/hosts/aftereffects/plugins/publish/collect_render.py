import os
import re
import tempfile
import attr

import pyblish.api

from openpype.settings import get_project_settings
from openpype.lib import abstract_collect_render
from openpype.lib.abstract_collect_render import RenderInstance

from openpype.hosts.aftereffects.api import get_stub


@attr.s
class AERenderInstance(RenderInstance):
    # extend generic, composition name is needed
    comp_name = attr.ib(default=None)
    comp_id = attr.ib(default=None)
    fps = attr.ib(default=None)
    projectEntity = attr.ib(default=None)
    stagingDir = attr.ib(default=None)
    app_version = attr.ib(default=None)


class CollectAERender(abstract_collect_render.AbstractCollectRender):

    order = pyblish.api.CollectorOrder + 0.400
    label = "Collect After Effects Render Layers"
    hosts = ["aftereffects"]

    # internal
    family_remapping = {
        "render": ("render.farm", "farm"),   # (family, label)
        "renderLocal": ("render", "local")
    }
    padding_width = 6
    rendered_extension = 'png'

    stub = get_stub()

    def get_instances(self, context):
        instances = []

        app_version = self.stub.get_app_version()
        app_version = app_version[0:4]

        current_file = context.data["currentFile"]
        version = context.data["version"]
        asset_entity = context.data["assetEntity"]
        project_entity = context.data["projectEntity"]

        compositions = self.stub.get_items(True)
        compositions_by_id = {item.id: item for item in compositions}
        for inst in self.stub.get_metadata():
            schema = inst.get('schema')
            # loaded asset container skip it
            if schema and 'container' in schema:
                continue

            if not inst["members"]:
                raise ValueError("Couldn't find id, unable to publish. " +
                                 "Please recreate instance.")
            item_id = inst["members"][0]

            work_area_info = self.stub.get_work_area(int(item_id))

            if not work_area_info:
                self.log.warning("Orphaned instance, deleting metadata")
                self.stub.remove_instance(int(item_id))
                continue

            frameStart = work_area_info.workAreaStart

            frameEnd = round(work_area_info.workAreaStart +
                             float(work_area_info.workAreaDuration) *
                             float(work_area_info.frameRate)) - 1
            fps = work_area_info.frameRate
            # TODO add resolution when supported by extension

            if inst["family"] in self.family_remapping.keys() \
                    and inst["active"]:
                remapped_family = self.family_remapping[inst["family"]]
                instance = AERenderInstance(
                    family=remapped_family[0],
                    families=[remapped_family[0]],
                    version=version,
                    time="",
                    source=current_file,
                    label="{} - {}".format(inst["subset"], remapped_family[1]),
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
                    frameStart=frameStart,
                    frameEnd=frameEnd,
                    frameStep=1,
                    toBeRenderedOn='deadline',
                    fps=fps,
                    app_version=app_version
                )

                comp = compositions_by_id.get(int(item_id))
                if not comp:
                    raise ValueError("There is no composition for item {}".
                                     format(item_id))
                instance.comp_name = comp.name
                instance.comp_id = item_id
                instance._anatomy = context.data["anatomy"]
                instance.anatomyData = context.data["anatomyData"]

                instance.outputDir = self._get_output_dir(instance)
                instance.context = context

                settings = get_project_settings(os.getenv("AVALON_PROJECT"))
                reviewable_subset_filter = \
                    (settings["deadline"]
                             ["publish"]
                             ["ProcessSubmittedJobOnFarm"]
                             ["aov_filter"])

                if inst["family"] == "renderLocal":
                    # for local renders
                    instance.anatomyData["version"] = instance.version
                    instance.anatomyData["subset"] = instance.subset
                    instance.stagingDir = tempfile.mkdtemp()
                    instance.projectEntity = project_entity

                    if self.hosts[0] in reviewable_subset_filter.keys():
                        for aov_pattern in \
                                reviewable_subset_filter[self.hosts[0]]:
                            if re.match(aov_pattern, instance.subset):
                                instance.families.append("review")
                                instance.review = True
                                break

                self.log.info("New instance:: {}".format(instance))
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
            (list) of absolute urls to rendered file
        """
        start = render_instance.frameStart
        end = render_instance.frameEnd

        # pull file name from Render Queue Output module
        render_q = self.stub.get_render_info()
        if not render_q:
            raise ValueError("No file extension set in Render Queue")
        _, ext = os.path.splitext(os.path.basename(render_q.file_name))

        base_dir = self._get_output_dir(render_instance)
        expected_files = []
        if "#" not in render_q.file_name:  # single frame (mov)W
            path = os.path.join(base_dir, "{}_{}_{}.{}".format(
                render_instance.asset,
                render_instance.subset,
                "v{:03d}".format(render_instance.version),
                ext.replace('.', '')
            ))
            expected_files.append(path)
        else:
            for frame in range(start, end + 1):
                path = os.path.join(base_dir, "{}_{}_{}.{}.{}".format(
                    render_instance.asset,
                    render_instance.subset,
                    "v{:03d}".format(render_instance.version),
                    str(frame).zfill(self.padding_width),
                    ext.replace('.', '')
                ))
                expected_files.append(path)
        return expected_files

    def _get_output_dir(self, render_instance):
        """
            Returns dir path of rendered files, used in submit_publish_job
            for metadata.json location.
            Should be in separate folder inside of work area.

        Args:
            render_instance (RenderInstance):

        Returns:
            (str): absolute path to rendered files
        """
        # render to folder of workfile
        base_dir = os.path.dirname(render_instance.source)
        file_name, _ = os.path.splitext(
            os.path.basename(render_instance.source))
        base_dir = os.path.join(base_dir, 'renders', 'aftereffects', file_name)

        # for submit_publish_job
        return base_dir
