import pyblish.api
from openpype.pipeline import PublishXmlValidationError
from openpype.hosts.tvpaint.api import save_file


class ValidateWorkfileMetadataRepair(pyblish.api.Action):
    """Store current context into workfile metadata."""

    label = "Use current context"
    icon = "wrench"
    on = "failed"

    def process(self, context, _plugin):
        """Save current workfile which should trigger storing of metadata."""
        current_file = context.data["currentFile"]
        # Save file should trigger
        save_file(current_file)


class ValidateWorkfileMetadata(pyblish.api.ContextPlugin):
    """Validate if wokrfile contain required metadata for publising."""

    label = "Validate Workfile Metadata"
    order = pyblish.api.ValidatorOrder

    families = ["workfile"]

    actions = [ValidateWorkfileMetadataRepair]

    required_keys = {"project", "asset", "task"}

    def process(self, context):
        workfile_context = context.data["workfile_context"]
        if not workfile_context:
            raise AssertionError(
                "Current workfile is missing whole metadata about context."
            )

        missing_keys = []
        for key in self.required_keys:
            value = workfile_context.get(key)
            if not value:
                missing_keys.append(key)

        if missing_keys:
            raise PublishXmlValidationError(
                self,
                "Current workfile is missing metadata about {}.".format(
                    ", ".join(missing_keys)
                ),
                formatting_data={
                    "missing_metadata": ", ".join(missing_keys)
                }
            )
