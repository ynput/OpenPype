import os
import pyblish.api



class CollectRenderPath(pyblish.api.InstancePlugin):
    """Generate file and directory path where rendered images will be"""

    label = "Collect Render Path"
    order = pyblish.api.CollectorOrder + 0.495

    def process(self, instance):
        current_file = instance.context.data["currentFile"]
        work_dir = os.path.dirname(current_file)
        work_file = os.path.basename(current_file)

        render_dir = os.path.join(
            work_dir, "render", "celaction"
        )
        render_path = os.path.join(
            render_dir, ".".join([instance.data["subset"], "%05d", "png"])
        )

        # create dir if it doesnt exists
        os.makedirs(render_dir, exist_ok=True)

        instance.data["path"] = render_path

        self.log.info(f"Render output path set to: `{render_path}`")
