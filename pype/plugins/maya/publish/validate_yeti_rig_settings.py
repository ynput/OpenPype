import pyblish.api


class ValidateYetiRigSettings(pyblish.api.InstancePlugin):
    order = pyblish.api.ValidatorOrder
    label = "Validate Yeti Rig Settings"
    families = ["studio.yetiRig"]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Detected invalid Yeti Rig data. "
                               "Tip: Save the scene")

    @classmethod
    def get_invalid(cls, instance):

        rigsettings = instance.data.get("rigsettings", {})
        if not rigsettings:
            cls.log.error("MAJOR ERROR: No rig settings found!")
            return True

        # Get inputs
        inputs = rigsettings.get("inputs", [])
        for input in inputs:
            source_id = input["sourceID"]
            if source_id is None:
                cls.log.error("Discovered source with 'None' as ID, please "
                              "check if the input shape has an cbId")
                return True

            destination_id = input["destinationID"]
            if destination_id is None:
                cls.log.error("Discovered None as destination ID value")
                return True

        return False
