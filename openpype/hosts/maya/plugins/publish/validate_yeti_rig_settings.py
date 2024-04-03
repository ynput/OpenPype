import pyblish.api

from openpype.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateYetiRigSettings(pyblish.api.InstancePlugin,
                              OptionalPyblishPluginMixin):
    """Validate Yeti Rig Settings have collected input connections.

    The input connections are collected for the nodes in the `input_SET`.
    When no input connections are found a warning is logged but it is allowed
    to pass validation.

    """

    order = pyblish.api.ValidatorOrder
    label = "Yeti Rig Settings"
    families = ["yetiRig"]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                ("Detected invalid Yeti Rig data. (See log) "
                 "Tip: Save the scene"))

    @classmethod
    def get_invalid(cls, instance):

        rigsettings = instance.data.get("rigsettings", None)
        if rigsettings is None:
            cls.log.error("MAJOR ERROR: No rig settings found!")
            return True

        # Get inputs
        inputs = rigsettings.get("inputs", [])
        if not inputs:
            # Empty rig settings dictionary
            cls.log.warning("No rig inputs found. This can happen when "
                            "the rig has no inputs from outside the rig.")
            return False

        for input in inputs:
            source_id = input["sourceID"]
            if source_id is None:
                cls.log.error("Discovered source with 'None' as ID, please "
                              "check if the input shape has a cbId")
                return True

            destination_id = input["destinationID"]
            if destination_id is None:
                cls.log.error("Discovered None as destination ID value")
                return True

        return False
