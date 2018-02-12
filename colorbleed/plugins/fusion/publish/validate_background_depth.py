import pyblish.api

from colorbleed import action


class ValidateBackgroundDepth(pyblish.api.ContextPlugin):
    """Validate if all Background tool are set to float32 bit"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Background Depth 32 bit"
    actions = [action.RepairContextAction]
    hosts = ["fusion"]
    families = ["*"]
    optional = True

    comp = None

    @classmethod
    def get_invalid(cls, context):
        cls.comp = context.data.get("currentComp")
        assert cls.comp, "Must have Comp object"

        backgrounds = cls.comp.GetToolList(False, "Background").values()
        if not backgrounds:
            return []

        return [i for i in backgrounds if i.GetInput("Depth") != 4.0]

    def process(self, context):
        invalid = self.get_invalid(context)
        if invalid:
            raise RuntimeError("Found %i nodes which are not set to float32"
                               % len(invalid))

    @classmethod
    def repair(cls):
        # todo: improve this method, context should be available(?)
        backgrounds = cls.comp.GetToolList(False, "Background").values()
        invalid = [i for i in backgrounds if i.GetInput("Depth") != 4.0]
        for i in invalid:
            i.SetInput("Depth", 4.0, cls.comp.TIME_UNDEFINED)
