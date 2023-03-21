import logging
import contextlib
import pyblish.api
from openpype.hosts.fusion.api import comp_lock_and_undo_chunk


log = logging.getLogger(__name__)


@contextlib.contextmanager
def enabled_savers(comp, savers):
    """Enable only the `savers` in Comp during the context.

    Any Saver tool in the passed composition that is not in the savers list
    will be set to passthrough during the context.

    Args:
        comp (object): Fusion composition object.
        savers (list): List of Saver tool objects.

    """
    passthrough_key = "TOOLB_PassThrough"
    original_states = {}
    enabled_save_names = {saver.Name for saver in savers}
    try:
        all_savers = comp.GetToolList(False, "Saver").values()
        for saver in all_savers:
            original_state = saver.GetAttrs()[passthrough_key]
            original_states[saver] = original_state

            # The passthrough state we want to set (passthrough != enabled)
            state = saver.Name not in enabled_save_names
            if state != original_state:
                saver.SetAttrs({passthrough_key: state})
        yield
    finally:
        for saver, original_state in original_states.items():
            saver.SetAttrs({"TOOLB_PassThrough": original_state})


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

        savers_to_render = [
            # Get the saver tool from the instance
            instance[0] for instance in context if
            # Only active instances
            instance.data.get("publish", True) and
            # Only render.local instances
            "render.local" in instance.data["families"]
        ]

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
            saver_names = ", ".join(saver.Name for saver in savers_to_render)
            self.log.info(f"Rendering tools: {saver_names}")

            with comp_lock_and_undo_chunk(current_comp):
                with enabled_savers(current_comp, savers_to_render):
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
