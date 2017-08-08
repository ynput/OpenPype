import pyblish.api
import colorbleed.api


class ValidateFrameRange(pyblish.api.InstancePlugin):
    """Valides the frame ranges.

    Checks the `startFrame`, `endFrame` and `handles` data.
    This does NOT ensure there's actual data present.

    This validates:
        - `startFrame` is lower than or equal to the `endFrame`.
        - must have both the `startFrame` and `endFrame` data.
        - The `handles` value is not lower than zero.

    """

    label = "Validate Frame Range"
    order = colorbleed.api.ValidateContentsOrder
    families = ["colorbleed.animation",
                "colorbleed.render"]

    def process(self, instance):

        start = instance.data.get("startFrame", None)
        end = instance.data.get("endFrame", None)
        handles = instance.data.get("handles", None)

        # Check if any of the values are present. If not we'll assume the
        # current instance does not require any time values.
        if all(value is None for value in [start, end, handles]):
            self.log.debug("No time values for this instance. "
                           "(Missing `startFrame`, `endFrame` or `handles`)")
            return

        # If only one of the two raise an error, it will require both.
        has_start = int(start is not None)
        has_end = int(end is not None)
        if has_start + has_end == 1:
            raise RuntimeError("Only a start frame or an end frame is provided"
                               " instead of both.")

        if has_start and has_end:
            self.log.info("Comparing start (%s) and end (%s)" % (start, end))
            if start > end:
                raise RuntimeError("The start frame is a higher value "
                                   "than the end frame: "
                                   "{0}>{1}".format(start, end))

        if handles is not None:
            if handles < 0.0:
                raise RuntimeError("Handles are set to a negative value")
