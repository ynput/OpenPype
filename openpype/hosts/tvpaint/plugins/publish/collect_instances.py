import os
import json
import copy
import pyblish.api
from avalon import io


class CollectInstances(pyblish.api.ContextPlugin):
    label = "Collect Instances"
    order = pyblish.api.CollectorOrder - 1
    hosts = ["tvpaint"]

    def process(self, context):
        workfile_instances = context.data["workfileInstances"]

        self.log.debug("Collected ({}) instances:\n{}".format(
            len(workfile_instances),
            json.dumps(workfile_instances, indent=4)
        ))

        # Backwards compatibility for workfiles that already have review
        #   instance in metadata.
        review_instance_exist = False
        for instance_data in workfile_instances:
            if instance_data["family"] == "review":
                review_instance_exist = True
                break

        # Fake review instance if review was not found in metadata families
        if not review_instance_exist:
            workfile_instances.append(
                self._create_review_instance_data(context)
            )

        for instance_data in workfile_instances:
            instance_data["fps"] = context.data["sceneFps"]

            # Store workfile instance data to instance data
            instance_data["originData"] = copy.deepcopy(instance_data)
            # Global instance data modifications
            # Fill families
            family = instance_data["family"]
            # Add `review` family for thumbnail integration
            instance_data["families"] = [family, "review"]

            # Instance name
            subset_name = instance_data["subset"]
            name = instance_data.get("name", subset_name)
            instance_data["name"] = name
            instance_data["label"] = "{} [{}-{}]".format(
                name,
                context.data["sceneMarkIn"] + 1,
                context.data["sceneMarkOut"] + 1
            )

            active = instance_data.get("active", True)
            instance_data["active"] = active
            instance_data["publish"] = active
            # Add representations key
            instance_data["representations"] = []

            # Different instance creation based on family
            instance = None
            if family == "review":
                # Change subset name
                task_name = io.Session["AVALON_TASK"]
                new_subset_name = "{}{}".format(family, task_name.capitalize())
                instance_data["subset"] = new_subset_name

                instance = context.create_instance(**instance_data)

                instance.data["layers"] = copy.deepcopy(
                    context.data["layersData"]
                )
                # Add ftrack family
                instance.data["families"].append("ftrack")

            elif family == "renderLayer":
                instance = self.create_render_layer_instance(
                    context, instance_data
                )
            elif family == "renderPass":
                instance = self.create_render_pass_instance(
                    context, instance_data
                )
            else:
                raise AssertionError(
                    "Instance with unknown family \"{}\": {}".format(
                        family, instance_data
                    )
                )

            if instance is None:
                continue

            any_visible = False
            for layer in instance.data["layers"]:
                if layer["visible"]:
                    any_visible = True
                    break

            instance.data["publish"] = any_visible

            self.log.debug("Created instance: {}\n{}".format(
                instance, json.dumps(instance.data, indent=4)
            ))

    def _create_review_instance_data(self, context):
        """Fake review instance data."""

        return {
            "family": "review",
            "asset": context.data["asset"],
            # Dummy subset name
            "subset": "reviewMain"
        }

    def create_render_layer_instance(self, context, instance_data):
        name = instance_data["name"]
        # Change label
        subset_name = instance_data["subset"]
        instance_data["label"] = "{}_Beauty".format(name)

        # Change subset name
        # Final family of an instance will be `render`
        new_family = "render"
        task_name = io.Session["AVALON_TASK"]
        new_subset_name = "{}{}_{}_Beauty".format(
            new_family, task_name.capitalize(), name
        )
        instance_data["subset"] = new_subset_name
        self.log.debug("Changed subset name \"{}\"->\"{}\"".format(
            subset_name, new_subset_name
        ))

        # Get all layers for the layer
        layers_data = context.data["layersData"]
        group_id = instance_data["group_id"]
        group_layers = []
        for layer in layers_data:
            if layer["group_id"] == group_id:
                group_layers.append(layer)

        if not group_layers:
            # Should be handled here?
            self.log.warning((
                f"Group with id {group_id} does not contain any layers."
                f" Instance \"{name}\" not created."
            ))
            return None

        instance_data["layers"] = group_layers

        # Add ftrack family
        instance_data["families"].append("ftrack")

        return context.create_instance(**instance_data)

    def create_render_pass_instance(self, context, instance_data):
        pass_name = instance_data["pass"]
        self.log.info(
            "Creating render pass instance. \"{}\"".format(pass_name)
        )
        # Change label
        render_layer = instance_data["render_layer"]
        instance_data["label"] = "{}_{}".format(render_layer, pass_name)

        # Change subset name
        # Final family of an instance will be `render`
        new_family = "render"
        old_subset_name = instance_data["subset"]
        task_name = io.Session["AVALON_TASK"]
        new_subset_name = "{}{}_{}_{}".format(
            new_family, task_name.capitalize(), render_layer, pass_name
        )
        instance_data["subset"] = new_subset_name
        self.log.debug("Changed subset name \"{}\"->\"{}\"".format(
            old_subset_name, new_subset_name
        ))

        layers_data = context.data["layersData"]
        layers_by_name = {
            layer["name"]: layer
            for layer in layers_data
        }

        if "layer_names" in instance_data:
            layer_names = instance_data["layer_names"]
        else:
            # Backwards compatibility
            # - not 100% working as it was found out that layer ids can't be
            #   used as unified identifier across multiple workstations
            layers_by_id = {
                layer["id"]: layer
                for layer in layers_data
            }
            layer_ids = instance_data["layer_ids"]
            layer_names = []
            for layer_id in layer_ids:
                layer = layers_by_id.get(layer_id)
                if layer:
                    layer_names.append(layer["name"])

            if not layer_names:
                raise ValueError((
                    "Metadata contain old way of storing layers information."
                    " It is not possible to identify layers to publish with"
                    " these data. Please remove Render Pass instances with"
                    " Subset manager and use Creator tool to recreate them."
                ))

        render_pass_layers = []
        for layer_name in layer_names:
            layer = layers_by_name.get(layer_name)
            # NOTE This is kind of validation before validators?
            if not layer:
                self.log.warning(
                    f"Layer with name {layer_name} was not found."
                )
                continue

            render_pass_layers.append(layer)

        if not render_pass_layers:
            name = instance_data["name"]
            self.log.warning(
                f"None of the layers from the RenderPass \"{name}\""
                " exist anymore. Instance not created."
            )
            return None

        instance_data["layers"] = render_pass_layers
        return context.create_instance(**instance_data)

    def add_workfile_instance(self, context):
        current_file = context.data["currentFile"]

        self.log.info(
            "Workfile path used for workfile family: {}".format(current_file)
        )

        dirpath, filename = os.path.split(current_file)
        basename, ext = os.path.splitext(filename)
        instance = context.create_instance(name=basename)

        task_name = io.Session["AVALON_TASK"]
        subset_name = "workfile" + task_name.capitalize()

        # Create Workfile instance
        instance.data.update({
            "subset": subset_name,
            "asset": context.data["asset"],
            "label": subset_name,
            "publish": True,
            "family": "workfile",
            "families": ["workfile"],
            "frameStart": context.data["frameStart"],
            "frameEnd": context.data["frameEnd"],
            "handleStart": context.data["handleStart"],
            "handleEnd": context.data["handleEnd"],
            "representations": [{
                "name": ext.lstrip("."),
                "ext": ext.lstrip("."),
                "files": filename,
                "stagingDir": dirpath
            }]
        })
        self.log.info("Collected workfile instance: {}".format(
            json.dumps(instance.data, indent=4)
        ))
