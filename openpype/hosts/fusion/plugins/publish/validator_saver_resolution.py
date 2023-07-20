import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin,
)

from openpype.hosts.fusion.api.action import SelectInvalidAction
from openpype.hosts.fusion.api import (
    get_current_comp,
    comp_lock_and_undo_chunk,
)


class ValidateSaverResolution(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """Validate that the saver input resolution matches the projects"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Resolution"
    families = ["render"]
    hosts = ["fusion"]
    optional = True
    actions = [SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance, wrong_resolution=None):
        """Validate if the saver rescive the expected resolution"""
        if wrong_resolution is None:
            wrong_resolution = []

        saver = instance[0]
        firstFrame = saver.GetAttrs("TOOLNT_Region_Start")[1]
        comp = get_current_comp()

        # If the current saver hasn't bin rendered its input resolution
        # hasn't bin saved. To combat this, add an expression in
        # the comments field to read the resolution

        # False undo removes the undo-stack from the undo list
        with comp_lock_and_undo_chunk(comp, "Read resolution", False):
            # Save old comment
            oldComment = ""
            hasExpression = False
            if saver["Comments"][firstFrame] != "":
                if saver["Comments"].GetExpression() is not None:
                    hasExpression = True
                    oldComment = saver["Comments"].GetExpression()
                    saver["Comments"].SetExpression(None)
                else:
                    oldComment = saver["Comments"][firstFrame]
                    saver["Comments"][firstFrame] = ""

            # Get input width
            saver["Comments"].SetExpression("self.Input.OriginalWidth")
            width = int(saver["Comments"][firstFrame])

            # Get input height
            saver["Comments"].SetExpression("self.Input.OriginalHeight")
            height = int(saver["Comments"][firstFrame])

            # Reset old comment
            saver["Comments"].SetExpression(None)
            if hasExpression:
                saver["Comments"].SetExpression(oldComment)
            else:
                saver["Comments"][firstFrame] = oldComment

        # Time to compare!
        wrong_resolution.append("{}x{}".format(width, height))
        entityData = instance.data["assetEntity"]["data"]
        if entityData["resolutionWidth"] != width:
            return [saver]
        if entityData["resolutionHeight"] != height:
            return [saver]

        return []

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        wrong_resolution = []
        invalid = self.get_invalid(instance, wrong_resolution)
        if invalid:
            entityData = instance.data["assetEntity"]["data"]
            raise PublishValidationError(
                "The input's resolution does not match"
                " the asset's resolution of {}x{}.\n\n"
                "The input's resolution is {}".format(
                    entityData["resolutionWidth"],
                    entityData["resolutionHeight"],
                    wrong_resolution[0],
                ),
                title=self.label,
            )
