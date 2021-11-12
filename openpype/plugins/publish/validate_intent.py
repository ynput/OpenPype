import os
import pyblish.api

from openpype.lib import filter_profiles


class ValidateIntent(pyblish.api.ContextPlugin):
    """Validate intent of the publish.

    It is required to fill the intent of this publish. Chech the log
    for more details
    """

    order = pyblish.api.ValidatorOrder

    label = "Validate Intent"
    enabled = False

    # Can be modified by settings
    profiles = [{
        "hosts": [],
        "task_types": [],
        "tasks": [],
        "validate": False
    }]

    def process(self, context):
        # Skip if there are no profiles
        validate = True
        if self.profiles:
            # Collect data from context
            task_name = context.data.get("task")
            task_type = context.data.get("taskType")
            host_name = context.data.get("hostName")

            filter_data = {
                "hosts": host_name,
                "task_types": task_type,
                "tasks": task_name
            }
            matching_profile = filter_profiles(
                self.profiles, filter_data, logger=self.log
            )
            if matching_profile:
                validate = matching_profile["validate"]

        if not validate:
            self.log.debug((
                "Validation of intent was skipped."
                " Matching profile for current context disabled validation."
            ))
            return

        msg = (
            "Please make sure that you select the intent of this publish."
        )

        intent = context.data.get("intent") or {}
        self.log.debug(str(intent))
        intent_value = intent.get("value")
        if not intent_value:
            raise AssertionError(msg)
