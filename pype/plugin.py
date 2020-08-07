import tempfile
import os
import pyblish.api

from pype.api import config
import inspect

ValidatePipelineOrder = pyblish.api.ValidatorOrder + 0.05
ValidateContentsOrder = pyblish.api.ValidatorOrder + 0.1
ValidateSceneOrder = pyblish.api.ValidatorOrder + 0.2
ValidateMeshOrder = pyblish.api.ValidatorOrder + 0.3


def imprint_attributes(plugin):
    """
    Load presets by class and set them as attributes (if found)

    :param plugin: plugin instance
    :type plugin: instance
    """
    file = inspect.getfile(plugin.__class__)
    file = os.path.normpath(file)
    plugin_kind = file.split(os.path.sep)[-2:-1][0]
    plugin_host = file.split(os.path.sep)[-3:-2][0]
    plugin_name = type(plugin).__name__
    try:
        config_data = config.get_presets()['plugins'][plugin_host][plugin_kind][plugin_name]  # noqa: E501
    except KeyError:
        print("preset not found")
        return

    for option, value in config_data.items():
        if option == "enabled" and value is False:
            setattr(plugin, "active", False)
        else:
            setattr(plugin, option, value)
            print("setting {}: {} on {}".format(option, value, plugin_name))


class ContextPlugin(pyblish.api.ContextPlugin):
    def process(cls, *args, **kwargs):
        imprint_attributes(cls)
        super(ContextPlugin, cls).process(cls, *args, **kwargs)


class InstancePlugin(pyblish.api.InstancePlugin):
    def process(cls, *args, **kwargs):
        imprint_attributes(cls)
        super(InstancePlugin, cls).process(cls, *args, **kwargs)


class Extractor(InstancePlugin):
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
        staging_dir = instance.data.get('stagingDir', None)

        if not staging_dir:
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data['stagingDir'] = staging_dir

        return staging_dir


def contextplugin_should_run(plugin, context):
    """Return whether the ContextPlugin should run on the given context.

    This is a helper function to work around a bug pyblish-base#250
    Whenever a ContextPlugin sets specific families it will still trigger even
    when no instances are present that have those families.

    This actually checks it correctly and returns whether it should run.

    """
    required = set(plugin.families)

    # When no filter always run
    if "*" in required:
        return True

    for instance in context:

        # Ignore inactive instances
        if (not instance.data.get("publish", True) or
                not instance.data.get("active", True)):
            continue

        families = instance.data.get("families", [])
        if any(f in required for f in families):
            return True

        family = instance.data.get("family")
        if family and family in required:
            return True

    return False


class ValidationException(Exception):
    pass
