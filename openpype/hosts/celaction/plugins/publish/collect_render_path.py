import os
import pyblish.api
import copy


class CollectRenderPath(pyblish.api.InstancePlugin):
    """Generate file and directory path where rendered images will be"""

    label = "Collect Render Path"
    order = pyblish.api.CollectorOrder + 0.495
    families = ["render.farm"]

    # Presets
    output_extension = "png"
    anatomy_template_key_render_files = None
    anatomy_template_key_metadata = None

    def process(self, instance):
        anatomy = instance.context.data["anatomy"]
        anatomy_data = copy.deepcopy(instance.data["anatomyData"])
        padding = anatomy.templates.get("frame_padding", 4)
        anatomy_data.update({
            "frame": f"%0{padding}d",
            "family": "render",
            "representation": self.output_extension,
            "ext": self.output_extension
        })

        anatomy_filled = anatomy.format(anatomy_data)

        # get anatomy rendering keys
        r_anatomy_key = self.anatomy_template_key_render_files
        m_anatomy_key = self.anatomy_template_key_metadata

        # get folder and path for rendering images from celaction
        render_dir = anatomy_filled[r_anatomy_key]["folder"]
        render_path = anatomy_filled[r_anatomy_key]["path"]
        self.log.debug("__ render_path: `{}`".format(render_path))

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
        if anatomy_filled.get(m_anatomy_key):
            instance.data["publishRenderMetadataFolder"] = anatomy_filled[
                m_anatomy_key]["folder"]
            self.log.info("Metadata render path: `{}`".format(
                instance.data["publishRenderMetadataFolder"]
            ))

        self.log.info(f"Render output path set to: `{render_path}`")
