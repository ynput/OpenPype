import os
import pyblish.api
import copy


class CollectRenderPath(pyblish.api.InstancePlugin):
    """Generate file and directory path where rendered images will be"""

    label = "Collect Render Path"
    order = pyblish.api.CollectorOrder + 0.495
    families = ["render.farm"]

    # Presets
    anatomy_render_key = None
    publish_render_metadata = None

    def process(self, instance):
        anatomy = instance.context.data["anatomy"]
        anatomy_data = copy.deepcopy(instance.data["anatomyData"])
        anatomy_data["family"] = "render"
        padding = anatomy.templates.get("frame_padding", 4)
        anatomy_data.update({
            "frame": f"%0{padding}d",
            "representation": "png"
        })

        anatomy_filled = anatomy.format(anatomy_data)

        # get anatomy rendering keys
        anatomy_render_key = self.anatomy_render_key or "render"
        publish_render_metadata = self.publish_render_metadata or "render"

        # get folder and path for rendering images from celaction
        render_dir = anatomy_filled[anatomy_render_key]["folder"]
        render_path = anatomy_filled[anatomy_render_key]["path"]

        # create dir if it doesnt exists
        try:
            if not os.path.isdir(render_dir):
                os.makedirs(render_dir, exist_ok=True)
        except OSError:
            # directory is not available
            self.log.warning("Path is unreachable: `{}`".format(render_dir))

        # add rendering path to instance data
        instance.data["path"] = render_path

        # get anatomy for published renders folder path
        if anatomy_filled.get(publish_render_metadata):
            instance.data["publishRenderMetadataFolder"] = anatomy_filled[
                publish_render_metadata]["folder"]
            self.log.info("Metadata render path: `{}`".format(
                instance.data["publishRenderMetadataFolder"]
            ))

        self.log.info(f"Render output path set to: `{render_path}`")
