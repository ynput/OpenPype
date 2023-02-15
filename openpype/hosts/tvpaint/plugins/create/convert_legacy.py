import collections

from openpype.pipeline.create.creator_plugins import (
    SubsetConvertorPlugin,
    cache_and_get_instances,
)
from openpype.hosts.tvpaint.api.plugin import SHARED_DATA_KEY
from openpype.hosts.tvpaint.api.lib import get_groups_data


class TVPaintLegacyConverted(SubsetConvertorPlugin):
    identifier = "tvpaint.legacy.converter"

    def find_instances(self):
        instances_by_identifier = cache_and_get_instances(
            self, SHARED_DATA_KEY, self.host.list_instances
        )
        if instances_by_identifier[None]:
            self.add_convertor_item("Convert legacy instances")

    def convert(self):
        current_instances = self.host.list_instances()
        to_convert = collections.defaultdict(list)
        converted = False
        for instance in current_instances:
            if instance.get("creator_identifier") is not None:
                continue
            converted = True

            family = instance.get("family")
            if family in (
                "renderLayer",
                "renderPass",
                "renderScene",
                "review",
                "workfile",
            ):
                to_convert[family].append(instance)
            else:
                instance["keep"] = False

        # Skip if nothing was changed
        if not converted:
            self.remove_convertor_item()
            return

        self._convert_render_layers(
            to_convert["renderLayer"], current_instances)
        self._convert_render_passes(
            to_convert["renderpass"], current_instances)
        self._convert_render_scenes(
            to_convert["renderScene"], current_instances)
        self._convert_workfiles(
            to_convert["workfile"], current_instances)
        self._convert_reviews(
            to_convert["review"], current_instances)

        new_instances = [
            instance
            for instance in current_instances
            if instance.get("keep") is not False
        ]
        self.host.write_instances(new_instances)
        # remove legacy item if all is fine
        self.remove_convertor_item()

    def _convert_render_layers(self, render_layers, current_instances):
        if not render_layers:
            return

        render_layers_by_group_id = {}
        for instance in current_instances:
            if instance.get("creator_identifier") == "render.layer":
                group_id = instance["creator_identifier"]["group_id"]
                render_layers_by_group_id[group_id] = instance

        groups_by_id = {
            group["group_id"]: group
            for group in get_groups_data()
        }
        for render_layer in render_layers:
            group_id = render_layer.pop("group_id")
            if group_id in render_layers_by_group_id:
                render_layer["keep"] = False
                continue
            render_layer["creator_identifier"] = "render.layer"
            render_layer["instance_id"] = render_layer.pop("uuid")
            render_layer["creator_attributes"] = {
                "group_id": group_id
            }
            render_layer["family"] = "render"
            group = groups_by_id[group_id]
            group["variant"] = group["name"]

    def _convert_render_passes(self, render_passes, current_instances):
        if not render_passes:
            return

        render_layers_by_group_id = {}
        for instance in current_instances:
            if instance.get("creator_identifier") == "render.layer":
                group_id = instance["creator_identifier"]["group_id"]
                render_layers_by_group_id[group_id] = instance

        for render_pass in render_passes:
            group_id = render_pass.pop("group_id")
            render_layer = render_layers_by_group_id.get(group_id)
            if not render_layer:
                render_pass["keep"] = False
                continue

            render_pass["creator_identifier"] = "render.pass"
            render_pass["instance_id"] = render_pass.pop("uuid")
            render_pass["family"] = "render"

            render_pass["creator_attributes"] = {
                "render_layer_instance_id": render_layer["instance_id"]
            }
            render_pass["variant"] = render_pass.pop("pass")
            render_pass.pop("renderlayer")

    def _convert_render_scenes(self, render_scenes, current_instances):
        for render_scene in render_scenes:
            render_scene["keep"] = False

    def _convert_workfiles(self, workfiles, current_instances):
        for render_scene in workfiles:
            render_scene["keep"] = False

    def _convert_reviews(self, reviews, current_instances):
        for render_scene in reviews:
            render_scene["keep"] = False
