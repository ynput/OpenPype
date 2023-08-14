import pyblish.api
from openpype.pipeline import publish


class CollectColorspaceData(pyblish.api.InstancePlugin,
                            publish.ColormanagedPyblishPluginMixin):
    """ Inject Colorspace data to available representations.

    Input data:
    - context.data[colorspace_config_path]:
        for anatomy formatting of possible template tokens in config path
    - context.data[colorspace_config_path]:
        for resolving project and host related config.ocio
    - context.data[colorspace_file_rules]:
        for resolving matched file rule from representation file name
        and adding it to representation

    Output data:
        representation[colorspaceData] = {
            "colorspace": "linear",
            "config": {
                "path": "/abs/path/to/config.ocio",
                "template": "{project[root]}/path/to/config.ocio"
            }
        }
    """
    label = "Collect Colorspace data"
    order = pyblish.api.CollectorOrder + 0.49

    def process(self, instance):

        representations = instance.data.get("representations")
        if not representations:
            self.log.info("No representations at instance : `{}`".format(
                instance))
            return

        # get colorspace settings
        context = instance.context

        # loop representations
        for representation in representations:
            # skip if colorspaceData is already at representation
            if representation.get("colorspaceData"):
                continue

            self.set_representation_colorspace(
                representation, context,
                colorspace=instance.data.get("colorspace")
            )
