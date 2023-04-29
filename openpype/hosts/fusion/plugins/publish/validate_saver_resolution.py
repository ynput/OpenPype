import pyblish.api
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction
from openpype.hosts.fusion.api import get_current_comp


class ValidateSaverResolution(pyblish.api.InstancePlugin):
    """Validate that the saver input resolution matches the projects"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Saver Resolution"
    families = ["render"]
    hosts = ["fusion"]
    actions = [SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance, wrong_resolution=None):
        if wrong_resolution is None:
            wrong_resolution = []

        entityData = instance.data["assetEntity"]["data"]
        saver = instance[0]
        comp = get_current_comp()

        # If the current saver hasn't bin rendered its input resolution
        # hasn't bin saved. To combat this, add an expression in
        # the comments field to read the resolution

        # Create undo stack so we later can remove all changes
        comp.StartUndo("Read resolution")

        # Save old comment
        oldComment = ""
        hasExpression = False
        if saver["Comments"][entityData["frameStart"]] is not "":
            if saver["Comments"].GetExpression() is not None:
                hasExpression = True
                oldComment = saver["Comments"].GetExpression()
                saver["Comments"].SetExpression(None)
            else:
                oldComment = saver["Comments"][entityData["frameStart"]]
                saver["Comments"][entityData["frameStart"]] = ""

        # Get input width
        saver["Comments"].SetExpression("self.Input.OriginalWidth")
        width = int(saver["Comments"][entityData["frameStart"]])

        # Get input height
        saver["Comments"].SetExpression("self.Input.OriginalHeight")
        height = int(saver["Comments"][entityData["frameStart"]])

        # Reset old comment
        saver["Comments"].SetExpression(None)
        if hasExpression:
            saver["Comments"].SetExpression(oldComment)
        else:
            saver["Comments"][entityData["frameStart"]] = oldComment

        # False undo removes the undo-stack from the undo list
        comp.EndUndo(False)

        # Time to compare!
        wrong_resolution.append("{}x{}".format(width, height))
        if entityData["resolutionWidth"] != width:
            return [saver]
        if entityData["resolutionHeight"] != height:
            return [saver]

        return []

    def process(self, instance):
        wrong_resolution = []
        invalid = self.get_invalid(instance, wrong_resolution)
        if invalid:
            entityData = instance.data["assetEntity"]["data"]
            raise PublishValidationError(
                "The input's resolution does not match"
                " the project's resolution of {}x{}.\n\n"
                "The input's resolution is {}".format(
                    entityData["resolutionWidth"],
                    entityData["resolutionHeight"],
                    wrong_resolution[0],
                ),
                title=self.label,
            )
