import os
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.fusion.api import comp_lock_and_undo_chunk


class FusionRenderLocal(pyblish.api.InstancePlugin):
    """Render the current Fusion composition locally."""

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Render Local"
    hosts = ["fusion"]
    families = ["render.local"]

    def process(self, instance):
        context = instance.context

        # Start render
        self.render_once(context)

        # Log render status
        self.log.info(
            "Rendered '{nm}' for asset '{ast}' under the task '{tsk}'".format(
                nm=instance.data["name"],
                ast=instance.data["asset"],
                tsk=instance.data["task"],
            )
        )

    def render_once(self, context):
        """Render context comp only once, even with more render instances"""

        # This plug-in assumes all render nodes get rendered at the same time
        # to speed up the rendering. The check below makes sure that we only
        # execute the rendering once and not for each instance.
        key = f"__hasRun{self.__class__.__name__}"
        if key not in context.data:
            # We initialize as false to indicate it wasn't successful yet
            # so we can keep track of whether Fusion succeeded
            context.data[key] = False

            current_comp = context.data["currentComp"]
            frame_start = context.data["frameStartHandle"]
            frame_end = context.data["frameEndHandle"]

            self.log.info("Starting Fusion render")
            self.log.info(f"Start frame: {frame_start}")
            self.log.info(f"End frame: {frame_end}")

            with comp_lock_and_undo_chunk(current_comp):
                result = current_comp.Render(
                    {
                        "Start": frame_start,
                        "End": frame_end,
                        "Wait": True,
                    }
                )

            context.data[key] = bool(result)

        if context.data[key] is False:
            raise RuntimeError("Comp render failed")
