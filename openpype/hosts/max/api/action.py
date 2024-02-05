from pymxs import runtime as rt

import pyblish.api

from openpype.pipeline.publish import get_errored_instances_from_context


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid objects in Blender when a publish plug-in failed."""
    label = "Select Invalid"
    on = "failed"
    icon = "search"

    def process(self, context, plugin):
        errored_instances = get_errored_instances_from_context(context,
                                                               plugin=plugin)

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes...")
        invalid = list()
        for instance in errored_instances:
            invalid_nodes = plugin.get_invalid(instance)
            if invalid_nodes:
                if isinstance(invalid_nodes, (list, tuple)):
                    invalid.extend(invalid_nodes)
                else:
                    self.log.warning(
                        "Failed plug-in doesn't have any selectable objects."
                    )

        if not invalid:
            self.log.info("No invalid nodes found.")
            return
        self.log.debug(f"invalid{invalid}")
        invalid_names = [obj for obj, _ in invalid]
        self.log.info(
            f"Selecting invalid objects: {invalid_names}"
        )

        rt.Select(invalid_names)
