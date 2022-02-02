import os
import pyblish.api


class IntegrateShotgridVersion(pyblish.api.InstancePlugin):
    """ Integrate Shotgrid Version """

    order = pyblish.api.IntegratorOrder+0.497
    label = "Shotgrid Version"

    sg = None

    def process(self, instance):

        context = instance.context
        self.sg = context.data.get("shotgridSession")

        # TODO: Use path template solver to build version code from settings
        anatomy = instance.data.get("anatomyData", {})
        code = "_".join(
            [
                anatomy['project']['code'],
                anatomy['parent'],
                anatomy['asset'],
                anatomy['task']['name'],
                "v{:03}".format(int(anatomy['version']))
            ]
        )

        version = self._find_existing_version(code, context)

        if not version:
            version = self._create_version(code, context)
            self.log.info("Create Shotgrid version: {}".format(version))
        else:
            self.log.info("Use existing Shotgrid version: {}".format(version))

        data_to_update = {}
        status = context.data.get("intent", {}).get("value")
        if status:
            data_to_update["sg_status_list"] = status

        for representation in instance.data.get("representations", []):
            local_path = representation.get("published_path")
            code = os.path.basename(local_path)

            if "shotgridreview" in representation.get("tags", []):

                if representation["ext"] in ["mov", "avi"]:
                    self.log.info(
                        "Upload review: {} for version shotgrid {}".format(
                            local_path, version.get("id"))
                    )
                    self.sg.upload(
                        "Version",
                        version.get("id"),
                        local_path,
                        field_name="sg_uploaded_movie"
                    )

                    data_to_update["sg_path_to_movie"] = local_path

                elif representation["ext"] in ["jpg", "png", "exr", "tga"]:
                    path_to_frame = local_path.replace("0000", "#")
                    data_to_update["sg_path_to_frames"] = path_to_frame

        self.log.info("Update Shotgrid version with {}".format(data_to_update))
        self.sg.update("Version", version['id'], data_to_update)

        instance.data["shotgridVersion"] = version

    def _find_existing_version(self, code, context):

        filters = [
            ["project", "is", context.data.get("shotgridProject")],
            ["sg_task", "is", context.data.get("shotgridTask")],
            ["entity", "is", context.data.get("shotgridEntity")],
            ["code", "is", code]
        ]
        return self.sg.find_one("Version", filters, [])

    def _create_version(self, code, context):

        version_data = {
            "project": context.data.get("shotgridProject"),
            "sg_task": context.data.get("shotgridTask"),
            "entity": context.data.get("shotgridEntity"),
            "code": code,
        }

        return self.sg.create("Version", version_data)
