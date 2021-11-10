"""
Requires:
    CollectTVPaintWorkfileData

Provides:
    Instances
"""
import os
import re
import copy
import pyblish.api

from openpype.lib import get_subset_name_with_asset_doc


class CollectTVPaintInstances(pyblish.api.InstancePlugin):
    label = "Collect TVPaint Instances"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["webpublisher"]
    targets = ["tvpaint"]

    workfile_family = "workfile"
    workfile_variant = ""
    review_family = "review"
    review_variant = "Main"
    render_pass_family = "renderPass"
    render_layer_family = "renderLayer"
    render_layer_pass_name = "beauty"

    # Set by settings
    # Regex must constain 'layer' and 'variant' groups which are extracted from
    #   name when instances are created
    layer_name_regex = r"(?P<layer>L[0-9]{3}_\w+)_(?P<variant>.+)"

    def process(self, context):
        # Prepare compiled regex
        layer_name_regex = re.compile(self.layer_name_regex)

        layers_data = context.data["layersData"]

        host_name = "tvpaint"
        task_name = context.data.get("task")
        asset_doc = context.data["assetEntity"]
        project_doc = context.data["projectEntity"]
        project_name = project_doc["name"]

        new_instances = []

        # Workfile instance
        workfile_subset_name = get_subset_name_with_asset_doc(
            self.workfile_family,
            self.workfile_variant,
            task_name,
            asset_doc,
            project_name,
            host_name
        )
        workfile_instance = self._create_workfile_instance(
            context, workfile_subset_name
        )
        new_instances.append(workfile_instance)

        # Review instance
        review_subset_name = get_subset_name_with_asset_doc(
            self.review_family,
            self.review_variant,
            task_name,
            asset_doc,
            project_name,
            host_name
        )
        review_instance = self._create_review_instance(
            context, review_subset_name
        )
        new_instances.append(review_instance)

        layers_by_render_layer = {}
        for layer in layers_data:
            # Filter only visible layers
            if not layer["visible"]:
                continue

            result = layer_name_regex.search(layer["name"])
            render_layer = result.group("layer")
            variant = result.group("variant")

            if render_layer not in layers_by_render_layer:
                layers_by_render_layer[render_layer] = []
            layers_by_render_layer[render_layer].append(copy.deepcopy(layer))
            dynamic_data = {
                "render_pass": variant,
                "render_layer": render_layer,
                # Override family for subset name
                "family": "render"
            }

            subset_name = get_subset_name_with_asset_doc(
                self.render_pass_family,
                variant,
                task_name,
                asset_doc,
                project_name,
                host_name,
                dynamic_data=dynamic_data
            )

            instance = self._create_render_pass_instance(
                context, layer, subset_name
            )
            new_instances.append(instance)

        for render_layer, layers in layers_by_render_layer.items():
            variant = render_layer
            dynamic_data = {
                "render_pass": self.render_layer_pass_name,
                "render_layer": render_layer,
                # Override family for subset name
                "family": "render"
            }
            subset_name = get_subset_name_with_asset_doc(
                self.render_pass_family,
                variant,
                task_name,
                asset_doc,
                project_name,
                host_name,
                dynamic_data=dynamic_data
            )
            instance = self._create_render_layer_instance(
                context, subset_name, layers
            )
            new_instances.append(instance)

        # Set data same for all instances
        scene_fps = context.data["sceneFps"]
        frame_start = context.data.get("frameStart")
        frame_end = context.data.get("frameEnd")

        for instance in new_instances:
            if instance.data.get("fps") is None:
                instance.data["fps"] = scene_fps

            if (
                instance.data.get("frameStart") is None
                or instance.data.get("frameEnd") is None
            ):
                instance.data["frameStart"] = frame_start
                instance.data["frameEnd"] = frame_end

            if instance.data.get("asset") is None:
                instance.data["asset"] = asset_doc["name"]

            if instance.data.get("task") is None:
                instance.data["task"] = task_name

    def _create_workfile_instance(self, context, subset_name):
        workfile_path = context.data["workfilePath"]
        staging_dir = os.path.dirname(workfile_path)
        filename = os.path.basename(workfile_path)
        ext = os.path.splitext(filename)[-1]

        return context.create_instance(**{
            "name": subset_name,
            "label": subset_name,
            "subset": subset_name,
            "family": self.workfile_family,
            "families": [self.workfile_family],
            "stagingDir": staging_dir,
            "representations": [{
                "name": ext.lstrip("."),
                "ext": ext.lstrip("."),
                "files": filename,
                "stagingDir": staging_dir
            }]
        })

    def _create_review_instance(self, context, subset_name):
        context_staging_dir = context.data["contextStagingDir"]
        staging_dir = os.path.join(context_staging_dir, subset_name)
        layers_data = context.data["layersData"]
        # Filter hidden layers
        filtered_layers_data = [
            copy.deepcopy(layer)
            for layer in layers_data
            if layer["visible"]
        ]
        return context.create_instance(**{
            "name": subset_name,
            "label": subset_name,
            "subset": subset_name,
            "family": self.review_family,
            "layers": filtered_layers_data,
            "stagingDir": staging_dir
        })

    def _create_render_pass_instance(self, context, layer, subset_name):
        # Global instance data modifications
        # Fill families
        instance_label = "{} [{}-{}]".format(
            subset_name,
            context.data["sceneMarkIn"] + 1,
            context.data["sceneMarkOut"] + 1
        )

        return context.create_instance(**{
            "subset": subset_name,
            "label": instance_label,
            "family": self.render_pass_family,
            # Add `review` family for thumbnail integration
            "families": [self.render_pass_family, "review"],
            "fps": context.data["sceneFps"],
            "representations": [],
            "layers": [layer]
        })

    def _create_render_layer_instance(self, context, layers, subset_name):
        # Global instance data modifications
        # Fill families
        instance_label = "{} [{}-{}]".format(
            subset_name,
            context.data["sceneMarkIn"] + 1,
            context.data["sceneMarkOut"] + 1
        )

        return context.create_instance(**{
            "subset": subset_name,
            "label": instance_label,
            "family": self.render_pass_family,
            # Add `review` family for thumbnail integration
            "families": [self.render_pass_family, "review"],
            "fps": context.data["sceneFps"],
            "representations": [],
            "layers": layers
        })
