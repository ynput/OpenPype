import tempfile
import os
import pyblish.api
import avalon.api
from pprint import pprint

from pypeapp import config
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
    print("-" * 50)
    print("imprinting")
    file = inspect.getfile(plugin.__class__)
    file = os.path.normpath(file)
    plugin_kind = file.split(os.path.sep)[-2:-1][0]
    plugin_host = file.split(os.path.sep)[-3:-2][0]
    plugin_name = type(plugin).__name__
    print(file)
    print(plugin_kind)
    print(plugin_host)
    print(plugin_name)

    pprint(config.get_presets()['plugins'])
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
    print("-" * 50)


def add_init_presets(source_class):
    orig_init = source_class.__init__

    def __init__(self, *args, **kwargs):
        imprint_attributes(self)
        print("overriding init")
        orig_init(self, *args, **kwargs)

    source_class.__init__ = __init__
    return source_class


def add_process_presets(source_class):
    orig_process = source_class.__init__

    def process(self, *args, **kwargs):
        imprint_attributes(self)
        orig_process(self, *args, **kwargs)

    source_class.__init__ = process
    return source_class


@add_process_presets
class ContextPlugin(pyblish.api.ContextPlugin):
    pass


@add_process_presets
class InstancePlugin(pyblish.api.InstancePlugin):
    pass



class PypeLoader(avalon.api.Loader):
    pass


@add_init_presets
class PypeCreator(avalon.api.Creator):
    pass


avalon.api.Creator = PypeCreator



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
