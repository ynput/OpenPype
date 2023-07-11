import warnings
import functools
import pyblish.api


class ActionDeprecatedWarning(DeprecationWarning):
    pass


def deprecated(new_destination):
    """Mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    func = None
    if callable(new_destination):
        func = new_destination
        new_destination = None

    def _decorator(decorated_func):
        if new_destination is None:
            warning_message = (
                " Please check content of deprecated function to figure out"
                " possible replacement."
            )
        else:
            warning_message = " Please replace your usage with '{}'.".format(
                new_destination
            )

        @functools.wraps(decorated_func)
        def wrapper(*args, **kwargs):
            warnings.simplefilter("always", ActionDeprecatedWarning)
            warnings.warn(
                (
                    "Call to deprecated function '{}'"
                    "\nFunction was moved or removed.{}"
                ).format(decorated_func.__name__, warning_message),
                category=ActionDeprecatedWarning,
                stacklevel=4
            )
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


@deprecated("openpype.pipeline.publish.get_errored_instances_from_context")
def get_errored_instances_from_context(context, plugin=None):
    """
    Deprecated:
        Since 3.14.* will be removed in 3.16.* or later.
    """

    from openpype.pipeline.publish import get_errored_instances_from_context

    return get_errored_instances_from_context(context, plugin=plugin)


@deprecated("openpype.pipeline.publish.get_errored_plugins_from_context")
def get_errored_plugins_from_data(context):
    """
    Deprecated:
        Since 3.14.* will be removed in 3.16.* or later.
    """

    from openpype.pipeline.publish import get_errored_plugins_from_context

    return get_errored_plugins_from_context(context)


class RepairAction(pyblish.api.Action):
    """Repairs the action

    To process the repairing this requires a static `repair(instance)` method
    is available on the plugin.

    Deprecated:
        'RepairAction' and 'RepairContextAction' were moved to
        'openpype.pipeline.publish' please change you imports.
        There is no "reasonable" way hot mark these classes as deprecated
        to show warning of wrong import. Deprecated since 3.14.* will be
        removed in 3.16.*

    """
    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):

        if not hasattr(plugin, "repair"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_instances = get_errored_instances_from_context(context,
                                                               plugin=plugin)
        for instance in errored_instances:
            plugin.repair(instance)


class RepairContextAction(pyblish.api.Action):
    """Repairs the action

    To process the repairing this requires a static `repair(instance)` method
    is available on the plugin.

    Deprecated:
        'RepairAction' and 'RepairContextAction' were moved to
        'openpype.pipeline.publish' please change you imports.
        There is no "reasonable" way hot mark these classes as deprecated
        to show warning of wrong import. Deprecated since 3.14.* will be
        removed in 3.16.*

    """
    label = "Repair"
    on = "failed"  # This action is only available on a failed plug-in

    def process(self, context, plugin):

        if not hasattr(plugin, "repair"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the errored instances
        self.log.info("Finding failed instances..")
        errored_plugins = get_errored_plugins_from_data(context)

        # Apply pyblish.logic to get the instances for the plug-in
        if plugin in errored_plugins:
            self.log.info("Attempting fix ...")
            plugin.repair(context)
