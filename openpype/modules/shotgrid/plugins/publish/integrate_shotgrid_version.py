import pyblish.api

from openpype.pipeline.publish import get_publish_repre_path


class IntegrateShotgridVersion(pyblish.api.InstancePlugin):
    """Integrate Shotgrid Version"""

    order = pyblish.api.IntegratorOrder + 0.497
    label = "Shotgrid Version"
    ### Starts Alkemy-X Override ###
    fields_to_add = {
        "frameStart": "sg_first_frame",
        "frameEnd": "sg_last_frame",
        "comment": "sg_submission_notes",
        "family": "sg_version_type",
    }
    ### Ends Alkemy-X Override ###

    sg = None

    def process(self, instance):
        context = instance.context
        self.sg = context.data.get("shotgridSession")

        # TODO: Use path template solver to build version code from settings
        anatomy = instance.data.get("anatomyData", {})
        ### Starts Alkemy-X Override ###
        code = "{}_{}_{}".format(
            anatomy["asset"],
            instance.data["subset"],
            "v{:03}".format(int(anatomy["version"])),
        )
        ### Ends Alkemy-X Override ###

        version = self._find_existing_version(code, context)

        if not version:
            version = self._create_version(code, context)
            self.log.info("Create Shotgrid version: {}".format(version))
        else:
            self.log.info("Use existing Shotgrid version: {}".format(version))

        data_to_update = {}
        intent = context.data.get("intent")
        if intent:
            data_to_update["sg_status_list"] = intent["value"]

        ### Starts Alkemy-X Override ###
        # Add a few extra fields from OP to SG version
        for op_field, sg_field in self.fields_to_add.items():
            field_value = instance.data.get(op_field) or context.data.get(
                op_field
            )
            if field_value:
                self.log.info(
                    "Adding field '{}' to SG as '{}':'{}'".format(
                        op_field, sg_field, field_value
                    )
                )
                data_to_update[sg_field] = field_value

        # Add version objectId to "sg_op_instance_id" so we can keep a link
        # between both
        version_entity = instance.data.get("versionEntity", {}).get("_id")
        if not version_entity:
            self.log.warning(
                "Instance doesn't have a 'versionEntity' to extract the id."
            )
            version_entity = "-"
        data_to_update["sg_op_instance_id"] = str(version_entity)

        ### Ends Alkemy-X Override ###

        for representation in instance.data.get("representations", []):
            local_path = get_publish_repre_path(
                instance, representation, False
            )
            ### Starts Alkemy-X Override ###
            # Remove if condition that was only publishing SG versions if tag
            # 'shotgridreview' is present. For now we have decided to publish
            # everything getting to this plugin
            # if "shotgridreview" in representation.get("tags", []):
            ### Ends Alkemy-X Override ###
            if representation["ext"] in ["mov", "avi"]:
                self.log.info(
                    "Upload review: {} for version shotgrid {}".format(
                        local_path, version.get("id")
                    )
                )
                self.sg.upload(
                    "Version",
                    version.get("id"),
                    local_path,
                    field_name="sg_uploaded_movie",
                )

                data_to_update["sg_path_to_movie"] = local_path

            elif representation["ext"] in ["jpg", "png", "exr", "tga"]:
                path_to_frame = local_path.replace("0000", "#")
                data_to_update["sg_path_to_frames"] = path_to_frame

        self.log.info("Update Shotgrid version with {}".format(data_to_update))
        self.sg.update("Version", version["id"], data_to_update)

        instance.data["shotgridVersion"] = version

    def _find_existing_version(self, code, context):
        filters = [
            ["project", "is", context.data.get("shotgridProject")],
            ["sg_task", "is", context.data.get("shotgridTask")],
            ["entity", "is", context.data.get("shotgridEntity")],
            ["code", "is", code],
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
