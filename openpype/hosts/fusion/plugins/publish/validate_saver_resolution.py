import pyblish.api
from openpype.pipeline import (
    PublishValidationError,
    OptionalPyblishPluginMixin,
)

from openpype.hosts.fusion.api.action import SelectInvalidAction
from openpype.hosts.fusion.api import comp_lock_and_undo_chunk


class ValidateSaverResolution(
    pyblish.api.InstancePlugin, OptionalPyblishPluginMixin
):
    """Validate that the saver input resolution matches the asset resolution"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Asset Resolution"
    families = ["render", "image"]
    hosts = ["fusion"]
    optional = True
    actions = [SelectInvalidAction]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        resolution = self.get_resolution(instance)
        expected_resolution = self.get_expected_resolution(instance)
        if resolution != expected_resolution:
            raise PublishValidationError(
                "The input's resolution does not match "
                "the asset's resolution {}x{}.\n\n"
                "The input's resolution is {}x{}.".format(
                    expected_resolution[0], expected_resolution[1],
                    resolution[0], resolution[1]
                )
            )

    @classmethod
    def get_invalid(cls, instance):
        saver = instance.data["tool"]
        try:
            resolution = cls.get_resolution(instance)
        except PublishValidationError:
            resolution = None
        expected_resolution = cls.get_expected_resolution(instance)
        if resolution != expected_resolution:
            return [saver]

    @classmethod
    def get_resolution(cls, instance):
        saver = instance.data["tool"]
        first_frame = instance.data["frameStartHandle"]
        return cls.get_tool_resolution(saver, frame=first_frame)

    @classmethod
    def get_expected_resolution(cls, instance):
        data = instance.data["assetEntity"]["data"]
        return data["resolutionWidth"], data["resolutionHeight"]

    @classmethod
    def get_tool_resolution(cls, tool, frame):
        """Return the 2D input resolution to a Fusion tool

        If the current tool hasn't been rendered its input resolution
        hasn't been saved. To combat this, add an expression in
        the comments field to read the resolution

        Args
            tool (Fusion Tool): The tool to query input resolution
            frame (int): The frame to query the resolution on.

        Returns:
            tuple: width, height as 2-tuple of integers

        """
        comp = tool.Composition

        # False undo removes the undo-stack from the undo list
        with comp_lock_and_undo_chunk(comp, "Read resolution", False):
            # Save old comment
            old_comment = ""
            has_expression = False

            if tool["Comments"][frame] not in ["", None]:
                if tool["Comments"].GetExpression() is not None:
                    has_expression = True
                    old_comment = tool["Comments"].GetExpression()
                    tool["Comments"].SetExpression(None)
                else:
                    old_comment = tool["Comments"][frame]
                    tool["Comments"][frame] = ""
            # Get input width
            tool["Comments"].SetExpression("self.Input.OriginalWidth")
            if tool["Comments"][frame] is None:
                raise PublishValidationError(
                    "Cannot get resolution info for frame '{}'.\n\n "
                    "Please check that saver has connected input.".format(
                        frame
                    )
                )

            width = int(tool["Comments"][frame])

            # Get input height
            tool["Comments"].SetExpression("self.Input.OriginalHeight")
            height = int(tool["Comments"][frame])

            # Reset old comment
            tool["Comments"].SetExpression(None)
            if has_expression:
                tool["Comments"].SetExpression(old_comment)
            else:
                tool["Comments"][frame] = old_comment

            return width, height
