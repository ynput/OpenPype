import os
import logging
import contextlib
import collections
import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.fusion.api import comp_lock_and_undo_chunk
from openpype.hosts.fusion.api.lib import get_frame_path, maintained_comp_range

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
    enabled_saver_names = {saver.Name for saver in savers}

    all_savers = comp.GetToolList(False, "Saver").values()
    savers_by_name = {saver.Name: saver for saver in all_savers}

    try:
        for saver in all_savers:
            original_state = saver.GetAttrs()[passthrough_key]
            original_states[saver.Name] = original_state

            # The passthrough state we want to set (passthrough != enabled)
            state = saver.Name not in enabled_saver_names
            if state != original_state:
                saver.SetAttrs({passthrough_key: state})
        yield
    finally:
        for saver_name, original_state in original_states.items():
            saver = savers_by_name[saver_name]
            saver.SetAttrs({"TOOLB_PassThrough": original_state})


class FusionRenderLocal(
    pyblish.api.InstancePlugin,
    publish.ColormanagedPyblishPluginMixin
):
    """Render the current Fusion composition locally."""

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Render Local"
    hosts = ["fusion"]
    families = ["render.local"]

    is_rendered_key = "_fusionrenderlocal_has_rendered"

    def process(self, instance):

        # Start render
        result = self.render(instance)
        if result is False:
            raise RuntimeError(f"Comp render failed for {instance}")

        self._add_representation(instance)

        # Log render status
        self.log.info(
            "Rendered '{nm}' for asset '{ast}' under the task '{tsk}'".format(
                nm=instance.data["name"],
                ast=instance.data["asset"],
                tsk=instance.data["task"],
            )
        )

    def render(self, instance):
        """Render instance.

        We try to render the minimal amount of times by combining the instances
        that have a matching frame range in one Fusion render. Then for the
        batch of instances we store whether the render succeeded or failed.

        """

        if self.is_rendered_key in instance.data:
            # This instance was already processed in batch with another
            # instance, so we just return the render result directly
            self.log.debug(f"Instance {instance} was already rendered")
            return instance.data[self.is_rendered_key]

        instances_by_frame_range = self.get_render_instances_by_frame_range(
            instance.context
        )

        # Render matching batch of instances that share the same frame range
        frame_range = self.get_instance_render_frame_range(instance)
        render_instances = instances_by_frame_range[frame_range]

        # We initialize render state false to indicate it wasn't successful
        # yet to keep track of whether Fusion succeeded. This is for cases
        # where an error below this might cause the comp render result not
        # to be stored for the instances of this batch
        for render_instance in render_instances:
            render_instance.data[self.is_rendered_key] = False

        savers_to_render = [inst.data["tool"] for inst in render_instances]
        current_comp = instance.context.data["currentComp"]
        frame_start, frame_end = frame_range

        self.log.info(
            f"Starting Fusion render frame range {frame_start}-{frame_end}"
        )
        saver_names = ", ".join(saver.Name for saver in savers_to_render)
        self.log.info(f"Rendering tools: {saver_names}")

        with comp_lock_and_undo_chunk(current_comp):
            with maintained_comp_range(current_comp):
                with enabled_savers(current_comp, savers_to_render):
                    result = current_comp.Render(
                        {
                            "Start": frame_start,
                            "End": frame_end,
                            "Wait": True,
                        }
                    )

        # Store the render state for all the rendered instances
        for render_instance in render_instances:
            render_instance.data[self.is_rendered_key] = bool(result)

        return result

    def _add_representation(self, instance):
        """Add representation to instance"""

        expected_files = instance.data["expectedFiles"]

        start = instance.data["frameStart"] - instance.data["handleStart"]

        path = expected_files[0]
        _, padding, ext = get_frame_path(path)

        staging_dir = os.path.dirname(path)

        files = [os.path.basename(f) for f in expected_files]
        if len(expected_files) == 1:
            files = files[0]

        repre = {
            "name": ext[1:],
            "ext": ext[1:],
            "frameStart": f"%0{padding}d" % start,
            "files": files,
            "stagingDir": staging_dir,
        }

        self.set_representation_colorspace(
            representation=repre,
            context=instance.context,
        )

        # review representation
        if instance.data.get("review", False):
            repre["tags"] = ["review"]

        # add the repre to the instance
        if "representations" not in instance.data:
            instance.data["representations"] = []
        instance.data["representations"].append(repre)

        return instance

    def get_render_instances_by_frame_range(self, context):
        """Return enabled render.local instances grouped by their frame range.

        Arguments:
            context (pyblish.Context): The pyblish context

        Returns:
            dict: (start, end): instances mapping

        """

        instances_to_render = [
            instance for instance in context if
            # Only active instances
            instance.data.get("publish", True) and
            # Only render.local instances
            "render.local" in instance.data.get("families", [])
        ]

        # Instances by frame ranges
        instances_by_frame_range = collections.defaultdict(list)
        for instance in instances_to_render:
            start, end = self.get_instance_render_frame_range(instance)
            instances_by_frame_range[(start, end)].append(instance)

        return dict(instances_by_frame_range)

    def get_instance_render_frame_range(self, instance):
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]
        return start, end
