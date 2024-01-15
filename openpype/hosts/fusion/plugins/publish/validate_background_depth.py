import pyblish.api

from openpype.pipeline import (
    publish,
    OptionalPyblishPluginMixin,
    PublishValidationError,
)

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateBackgroundDepth(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """Validate if all Background tool are set to float32 bit"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Background Depth 32 bit"
    hosts = ["fusion"]
    families = ["render", "image"]
    optional = True

    actions = [SelectInvalidAction, publish.RepairAction]

    @classmethod
    def get_invalid(cls, instance):
        context = instance.context
        comp = context.data.get("currentComp")
        assert comp, "Must have Comp object"

        backgrounds = comp.GetToolList(False, "Background").values()
        if not backgrounds:
            return []

        return [i for i in backgrounds if i.GetInput("Depth") != 4.0]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Found {} Backgrounds tools which"
                " are not set to float32".format(len(invalid)),
                title=self.label,
            )

    @classmethod
    def repair(cls, instance):
        comp = instance.context.data.get("currentComp")
        invalid = cls.get_invalid(instance)
        for i in invalid:
            i.SetInput("Depth", 4.0, comp.TIME_UNDEFINED)
