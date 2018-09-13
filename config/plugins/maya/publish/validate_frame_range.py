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
                "colorbleed.pointcache",
                "colorbleed.camera",
                "colorbleed.renderlayer"]

    def process(self, instance):

        start = instance.data.get("startFrame", None)
        end = instance.data.get("endFrame", None)
        handles = instance.data.get("handles", None)

        # Check if any of the values are present
        if any(value is None for value in [start, end]):
            raise ValueError("No time values for this instance. "
                             "(Missing `startFrame` or `endFrame`)")

        self.log.info("Comparing start (%s) and end (%s)" % (start, end))
        if start > end:
            raise RuntimeError("The start frame is a higher value "
                               "than the end frame: "
                               "{0}>{1}".format(start, end))

        if handles is not None:
            if handles < 0.0:
                raise RuntimeError("Handles are set to a negative value")
