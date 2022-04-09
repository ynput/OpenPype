# import gazu
import pyblish.api


class IntegrateKitsuVersion(pyblish.api.InstancePlugin):
    """Integrate Kitsu Review"""

    order = pyblish.api.IntegratorOrder
    label = "Kitsu Review"
    # families = ["kitsu"]

    def process(self, instance):
        pass

        # gazu.task.upload_preview_file(preview, file_path, normalize_movie=True, client=<gazu.client.KitsuClient object>)
        # gazu.task.add_preview(task, comment, preview_file_path, normalize_movie=True, client=<gazu.client.KitsuClient object>)