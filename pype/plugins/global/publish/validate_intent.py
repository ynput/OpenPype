import pyblish.api
import os


class ValidateIntent(pyblish.api.ContextPlugin):
    """Validate intent of the publish.

    It is required to fill the intent of this publish. Chech the log
    for more details
    """

    order = pyblish.api.ValidatorOrder

    label = "Validate Intent"
    # TODO: this should be off by default and only activated viac config
    tasks = ["animation"]
    hosts = ["harmony"]
    if os.environ.get("AVALON_TASK") not in tasks:
        active = False

    def process(self, context):
        msg = (
            "Please make sure that you select the intent of this publish."
        )

        intent = context.data.get("intent")
        self.log.debug(intent)
        assert intent, msg

        intent_value = intent.get("value")
        assert intent is not "", msg
