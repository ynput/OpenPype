# -*- coding: utf-8 -*-
import os
import gazu
import pyblish.api


class IntegrateKitsuVersion(pyblish.api.InstancePlugin):
    """Integrate Kitsu Review"""

    order = pyblish.api.IntegratorOrder + 0.01
    label = "Kitsu Review"
    # families = ["kitsu"]

    def process(self, instance):

        context = instance.context
        task = context.data["kitsu_task"]
        comment = context.data["kitsu_comment"]

        for representation in instance.data.get("representations", []):

            local_path = representation.get("published_path")
            self.log.info("*"*40)
            self.log.info(local_path)
            self.log.info(representation.get("tags", []))

            # code = os.path.basename(local_path)

            if representation.get("tags", []):
                continue
            
            # gazu.task.upload_preview_file(preview, file_path, normalize_movie=True)
            gazu.task.add_preview(task, comment, local_path, normalize_movie=True)