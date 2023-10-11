import pyblish.api
import ayon_api

from openpype import AYON_SERVER_ENABLED
from openpype.client.operations import OperationsSession


class IntegrateVersionAttributes(pyblish.api.ContextPlugin):
    """Integrate version attributes from predefined key.

    Any integration after 'IntegrateAsset' can fill 'versionAttributes' with
    attribute key & value to be updated on created version.

    The integration must make sure the attribute is available for the version
    entity otherwise an error would be raised.

    Example of 'versionAttributes':
        {
            "ftrack_id": "0123456789-101112-131415",
            "syncsketch_id": "987654321-012345-678910"
        }
    """

    label = "Integrate Version Attributes"
    order = pyblish.api.IntegratorOrder + 0.5

    def process(self, context):
        available_attributes = ayon_api.get_attributes_for_type("version")
        skipped_attributes = set()
        project_name = context.data["projectName"]
        op_session = OperationsSession()
        for instance in context:
            label = self.get_instance_label(instance)
            version_entity = instance.data.get("versionEntity")
            if not version_entity:
                continue
            attributes = instance.data.get("versionAttributes")
            if not attributes:
                self.log.debug((
                    "Skipping instance {} because it does not specify"
                    " version attributes to set."
                ).format(label))
                continue

            filtered_attributes = {}
            for attr, value in attributes.items():
                if attr not in available_attributes:
                    skipped_attributes.add(attr)
                else:
                    filtered_attributes[attr] = value

            if not filtered_attributes:
                self.log.debug((
                    "Skipping instance {} because all version attributes were"
                    " filtered out."
                ).format(label))
                continue

            self.log.debug("Updating attributes on version {} to {}".format(
                version_entity["_id"], str(filtered_attributes)
            ))
            op_session.update_entity(
                project_name,
                "version",
                version_entity["_id"],
                {"attrib": filtered_attributes}
            )

        if skipped_attributes:
            self.log.warning((
                "Skipped version attributes integration because they're"
                " not available on the server: {}"
            ).format(str(skipped_attributes)))

        if len(op_session):
            op_session.commit()
            self.log.info("Updated version attributes")
        else:
            self.log.debug("There are no version attributes to update")

    @staticmethod
    def get_instance_label(instance):
        return (
            instance.data.get("label")
            or instance.data.get("name")
            or instance.data.get("subset")
            or str(instance)
        )


# Discover the plugin only in AYON mode
if not AYON_SERVER_ENABLED:
    del IntegrateVersionAttributes
