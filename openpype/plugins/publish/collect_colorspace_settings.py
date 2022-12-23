from pyblish import api
from openpype.pipeline import (
    get_imageio_config,
    get_imageio_file_rules
)


class CollectColorspaceSettings(api.ContextPlugin):
    """Collect Colorspace Settings and store in the context."""

    order = api.CollectorOrder
    label = "Collect Colorspace Settings"

    def process(self, context):
        project_name = context.data["projectName"]
        host = context.data["hostName"]

        context.data["colorspace_config_path"] = get_imageio_config(
            project_name, host)
        context.data["colorspace_file_rules"] = get_imageio_file_rules(
            project_name, host)
