from openpype.lib import PreLaunchHook

from openpype.pipeline.colorspace import get_imageio_config
from openpype.pipeline.template_data import get_template_data


class PreLaunchHostSetOCIO(PreLaunchHook):
    """Set OCIO environment for the host"""

    order = 0
    app_groups = ["substancepainter"]

    def execute(self):
        """Hook entry method."""

        anatomy_data = get_template_data(
            project_doc=self.data["project_doc"],
            asset_doc=self.data["asset_doc"],
            task_name=self.data["task_name"],
            host_name=self.host_name,
            system_settings=self.data["system_settings"]
        )

        ocio_config = get_imageio_config(
            project_name=self.data["project_doc"]["name"],
            host_name=self.host_name,
            project_settings=self.data["project_settings"],
            anatomy_data=anatomy_data,
            anatomy=self.data["anatomy"]
        )

        if ocio_config:
            ocio_path = ocio_config["path"]
            self.log.info(f"Setting OCIO config path: {ocio_path}")
            self.launch_context.env["OCIO"] = ocio_path
        else:
            self.log.debug("OCIO not set or enabled")
