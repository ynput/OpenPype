import json
import copy
import pyblish.api
from avalon import io

from openpype.lib import get_subset_name_with_asset_doc


class CollectRenderScene(pyblish.api.ContextPlugin):
    """Collect instance which renders whole scene in PNG.

    Creates instance with family 'renderScene' which will have all layers
    to render which will be composite into one result. The instance is not
    collected from scene.

    Scene will be rendered with all visible layers similar way like review is.

    Instance is disabled if there are any created instances of 'renderLayer'
    or 'renderPass'. That is because it is expected that this instance is
    used as lazy publish of TVPaint file.

    Subset name is created similar way like 'renderLayer' family. It can use
    `renderPass` and `renderLayer` keys which can be set using settings and
    `variant` is filled using `renderPass` value.
    """
    label = "Collect Render Scene"
    order = pyblish.api.CollectorOrder - 0.39
    hosts = ["tvpaint"]

    # Value of 'render_pass' in subset name template
    render_pass = "beauty"

    # Settings attributes
    enabled = False
    # Value of 'render_layer' and 'variant' in subset name template
    render_layer = "Main"

    def process(self, context):
        # Check if there are created instances of renderPass and renderLayer
        # - that will define if renderScene instance is enabled after
        #   collection
        any_created_instance = False
        for instance in context:
            family = instance.data["family"]
            if family in ("renderPass", "renderLayer"):
                any_created_instance = True
                break

        # Global instance data modifications
        # Fill families
        family = "renderScene"
        # Add `review` family for thumbnail integration
        families = [family, "review"]

        # Collect asset doc to get asset id
        # - not sure if it's good idea to require asset id in
        #   get_subset_name?
        asset_name = context.data["workfile_context"]["asset"]
        asset_doc = io.find_one({
            "type": "asset",
            "name": asset_name
        })

        # Project name from workfile context
        project_name = context.data["workfile_context"]["project"]
        # Host name from environment variable
        host_name = context.data["hostName"]
        # Variant is using render pass name
        variant = self.render_layer
        dynamic_data = {
            "render_layer": self.render_layer,
            "render_pass": self.render_pass
        }
        task_name = io.Session["AVALON_TASK"]
        subset_name = get_subset_name_with_asset_doc(
            family,
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name,
            dynamic_data=dynamic_data
        )

        instance_data = {
            "family": family,
            "families": families,
            "fps": context.data["sceneFps"],
            "name": subset_name,
            "label": "{} [{}-{}]".format(
                subset_name,
                context.data["sceneMarkIn"] + 1,
                context.data["sceneMarkOut"] + 1
            ),
            "active": not any_created_instance,
            "publish": not any_created_instance,
            "representations": [],
            "layers": copy.deepcopy(context.data["layersData"])
        }

        instance = context.create_instance(**instance_data)

        self.log.debug("Created instance: {}\n{}".format(
            instance, json.dumps(instance.data, indent=4)
        ))
