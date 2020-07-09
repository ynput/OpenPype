import os
import pyblish.api
import copy


class CollectRenderPath(pyblish.api.InstancePlugin):
    """Generate file and directory path where rendered images will be"""

    label = "Collect Render Path"
    order = pyblish.api.CollectorOrder + 0.495
    families = ["render.farm"]

    def process(self, instance):
        anatomy = instance.context.data["anatomy"]
        anatomy_data = copy.deepcopy(instance.data["anatomyData"])
        padding = anatomy.templates.get("frame_padding", 4)
        anatomy_data.update({
            "frame": f"%0{padding}d",
            "representation": "png"
        })

        anatomy_filled = anatomy.format(anatomy_data)

        render_dir = anatomy_filled["render_tmp"]["folder"]
        render_path = anatomy_filled["render_tmp"]["path"]

        # create dir if it doesnt exists
        os.makedirs(render_dir, exist_ok=True)

        instance.data["path"] = render_path

        self.log.info(f"Render output path set to: `{render_path}`")
