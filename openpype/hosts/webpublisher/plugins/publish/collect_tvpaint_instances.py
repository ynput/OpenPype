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


class CollectTVPaintInstances(pyblish.api.ContextPlugin):
    label = "Collect TVPaint Instances"
    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["webpublisher"]
    targets = ["tvpaint_worker"]

    workfile_family = "workfile"
    workfile_variant = ""
    review_family = "review"
    review_variant = "Main"
    render_pass_family = "renderPass"
    render_layer_family = "renderLayer"
    render_layer_pass_name = "beauty"

    # Set by settings
    # Regex must contain 'layer' and 'variant' groups which are extracted from
    #   name when instances are created
    layer_name_regex = r"(?P<layer>L[0-9]{3}_\w+)_(?P<pass>.+)"

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

        # Get render layers and passes from TVPaint layers
        #   - it's based on regex extraction
        layers_by_layer_and_pass = {}
        for layer in layers_data:
            # Filter only visible layers
            if not layer["visible"]:
                continue

            result = layer_name_regex.search(layer["name"])
            # Layer name not matching layer name regex
            #   should raise an exception?
            if result is None:
                continue
            render_layer = result.group("layer")
            render_pass = result.group("pass")

            render_pass_maping = layers_by_layer_and_pass.get(
                render_layer
            )
            if render_pass_maping is None:
                render_pass_maping = {}
                layers_by_layer_and_pass[render_layer] = render_pass_maping

            if render_pass not in render_pass_maping:
                render_pass_maping[render_pass] = []
            render_pass_maping[render_pass].append(copy.deepcopy(layer))

        layers_by_render_layer = {}
        for render_layer, render_passes in layers_by_layer_and_pass.items():
            render_layer_layers = []
            layers_by_render_layer[render_layer] = render_layer_layers
            for render_pass, layers in render_passes.items():
                render_layer_layers.extend(copy.deepcopy(layers))
                dynamic_data = {
                    "render_pass": render_pass,
                    "render_layer": render_layer,
                    # Override family for subset name
                    "family": "render"
                }

                subset_name = get_subset_name_with_asset_doc(
                    self.render_pass_family,
                    render_pass,
                    task_name,
                    asset_doc,
                    project_name,
                    host_name,
                    dynamic_data=dynamic_data
                )

                instance = self._create_render_pass_instance(
                    context, layers, subset_name
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
                self.render_layer_family,
                variant,
                task_name,
                asset_doc,
                project_name,
                host_name,
                dynamic_data=dynamic_data
            )
            instance = self._create_render_layer_instance(
                context, layers, subset_name
            )
            new_instances.append(instance)

        # Set data same for all instances
        frame_start = context.data.get("frameStart")
        frame_end = context.data.get("frameEnd")

        for instance in new_instances:
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

            if "representations" not in instance.data:
                instance.data["representations"] = []

            if "source" not in instance.data:
                instance.data["source"] = "webpublisher"

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
            "families": [],
            "stagingDir": staging_dir,
            "representations": [{
                "name": ext.lstrip("."),
                "ext": ext.lstrip("."),
                "files": filename,
                "stagingDir": staging_dir
            }]
        })

    def _create_review_instance(self, context, subset_name):
        staging_dir = self._create_staging_dir(context, subset_name)
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
            "families": [],
            "layers": filtered_layers_data,
            "stagingDir": staging_dir
        })

    def _create_render_pass_instance(self, context, layers, subset_name):
        staging_dir = self._create_staging_dir(context, subset_name)
        # Global instance data modifications
        # Fill families
        return context.create_instance(**{
            "name": subset_name,
            "subset": subset_name,
            "label": subset_name,
            "family": "render",
            # Add `review` family for thumbnail integration
            "families": [self.render_pass_family, "review"],
            "representations": [],
            "layers": layers,
            "stagingDir": staging_dir
        })

    def _create_render_layer_instance(self, context, layers, subset_name):
        staging_dir = self._create_staging_dir(context, subset_name)
        # Global instance data modifications
        # Fill families
        return context.create_instance(**{
            "name": subset_name,
            "subset": subset_name,
            "label": subset_name,
            "family": "render",
            # Add `review` family for thumbnail integration
            "families": [self.render_layer_family, "review"],
            "representations": [],
            "layers": layers,
            "stagingDir": staging_dir
        })

    def _create_staging_dir(self, context, subset_name):
        context_staging_dir = context.data["contextStagingDir"]
        staging_dir = os.path.join(context_staging_dir, subset_name)
        if not os.path.exists(staging_dir):
            os.makedirs(staging_dir)
        return staging_dir
