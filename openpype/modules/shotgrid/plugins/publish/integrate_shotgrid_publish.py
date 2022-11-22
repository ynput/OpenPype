import os
import pyblish.api


class IntegrateShotgridPublish(pyblish.api.InstancePlugin):
    """
    Create published Files from representations and add it to version. If
    representation is tagged add shotgrid review, it will add it in
    path to movie for a movie file or path to frame for an image sequence.
    """

    order = pyblish.api.IntegratorOrder + 0.499
    label = "Shotgrid Published Files"

    def process(self, instance):

        context = instance.context

        self.sg = context.data.get("shotgridSession")

        shotgrid_version = instance.data.get("shotgridVersion")

        for representation in instance.data.get("representations", []):

            local_path = representation.get("published_path")
            code = os.path.basename(local_path)

            if representation.get("tags", []):
                continue

            published_file = self._find_existing_publish(
                code, context, shotgrid_version
            )

            published_file_data = {
                "project": context.data.get("shotgridProject"),
                "code": code,
                "entity": context.data.get("shotgridEntity"),
                "task": context.data.get("shotgridTask"),
                "version": shotgrid_version,
                "path": {"local_path": local_path},
            }
            if not published_file:
                published_file = self._create_published(published_file_data)
                self.log.info(
                    "Create Shotgrid PublishedFile: {}".format(published_file)
                )
            else:
                self.sg.update(
                    published_file["type"],
                    published_file["id"],
                    published_file_data,
                )
                self.log.info(
                    "Update Shotgrid PublishedFile: {}".format(published_file)
                )

            if instance.data["family"] == "image":
                self.sg.upload_thumbnail(
                    published_file["type"], published_file["id"], local_path
                )
            instance.data["shotgridPublishedFile"] = published_file

    def _find_existing_publish(self, code, context, shotgrid_version):

        filters = [
            ["project", "is", context.data.get("shotgridProject")],
            ["task", "is", context.data.get("shotgridTask")],
            ["entity", "is", context.data.get("shotgridEntity")],
            ["version", "is", shotgrid_version],
            ["code", "is", code],
        ]
        return self.sg.find_one("PublishedFile", filters, [])

    def _create_published(self, published_file_data):

        return self.sg.create("PublishedFile", published_file_data)
