import pyblish.api

from openpype.pipeline.publish import PublishValidationError


class ValidateFileSequences(pyblish.api.ContextPlugin):
    """Validates whether any file sequences were collected."""

    order = pyblish.api.ValidatorOrder
    # Keep "filesequence" for backwards compatibility of older jobs
    targets = ["filesequence", "farm"]
    label = "Validate File Sequences"

    def process(self, context):
        if not context:
            raise PublishValidationError("Nothing collected.")
