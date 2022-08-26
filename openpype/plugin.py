import functools
import warnings

import pyblish.api

ValidatePipelineOrder = pyblish.api.ValidatorOrder + 0.05
ValidateContentsOrder = pyblish.api.ValidatorOrder + 0.1
ValidateSceneOrder = pyblish.api.ValidatorOrder + 0.2
ValidateMeshOrder = pyblish.api.ValidatorOrder + 0.3


class PluginDeprecatedWarning(DeprecationWarning):
    pass


def _deprecation_warning(item_name, warning_message):
    warnings.simplefilter("always", PluginDeprecatedWarning)
    warnings.warn(
        (
            "Call to deprecated function '{}'"
            "\nFunction was moved or removed.{}"
        ).format(item_name, warning_message),
        category=PluginDeprecatedWarning,
        stacklevel=4
    )


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
            _deprecation_warning(decorated_func.__name__, warning_message)
            return decorated_func(*args, **kwargs)
        return wrapper

    if func is None:
        return _decorator
    return _decorator(func)


# Classes just inheriting from pyblish classes
# - seems to be unused in code (not 100% sure)
# - they should be removed but because it is not clear if they're used
#   we'll keep then and log deprecation warning
# Deprecated since 3.14.* will be removed in 3.16.*
class ContextPlugin(pyblish.api.ContextPlugin):
    def __init__(self, *args, **kwargs):
        _deprecation_warning(
            "openpype.plugin.ContextPlugin",
            " Please replace your usage with 'pyblish.api.ContextPlugin'."
        )
        super(ContextPlugin, self).__init__(*args, **kwargs)


# Deprecated since 3.14.* will be removed in 3.16.*
class InstancePlugin(pyblish.api.InstancePlugin):
    def __init__(self, *args, **kwargs):
        _deprecation_warning(
            "openpype.plugin.ContextPlugin",
            " Please replace your usage with 'pyblish.api.InstancePlugin'."
        )
        super(InstancePlugin, self).__init__(*args, **kwargs)


# NOTE: This class is used on so many places I gave up moving it
class Extractor(pyblish.api.InstancePlugin):
    """Extractor base class.

    The extractor base class implements a "staging_dir" function used to
    generate a temporary directory for an instance to extract to.

    This temporary directory is generated through `tempfile.mkdtemp()`

    """

    order = 2.0

    def staging_dir(self, instance):
        """Provide a temporary directory in which to store extracted files

        Upon calling this method the staging directory is stored inside
        the instance.data['stagingDir']
        """

        from openpype.pipeline.publish import get_instance_staging_dir

        return get_instance_staging_dir(instance)


@deprecated("openpype.pipeline.publish.context_plugin_should_run")
def contextplugin_should_run(plugin, context):
    """Return whether the ContextPlugin should run on the given context.

    This is a helper function to work around a bug pyblish-base#250
    Whenever a ContextPlugin sets specific families it will still trigger even
    when no instances are present that have those families.

    This actually checks it correctly and returns whether it should run.

    """

    from openpype.pipeline.publish import context_plugin_should_run

    return context_plugin_should_run(plugin, context)
