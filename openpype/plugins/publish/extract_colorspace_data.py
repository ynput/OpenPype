import pyblish.api
from openpype.pipeline import publish


class ExtractColorspaceData(publish.ExtractorColormanaged):
    """ Inject Colorspace data to available representations.

    Input data:
    - context.data[colorspace_config_path]:
        for anatomy formating of possible template tokkens in config path
    - context.data[colorspace_config_path]:
        for resolving project and host related config.ocio
    - context.data[colorspace_file_rules]:
        for resolving matched file rule from representation file name
        and adding it to representation

    Output data:
        representation[colorspaceData] = {
            "colorspace": "linear",
            "configPath": {
                "path": "/abs/path/to/config.ocio",
                "template": "{project[root]}/path/to/config.ocio"
            }
        }
    """
    label = "Extract Colorspace data"
    order = pyblish.api.ExtractorOrder + 0.49

    def process(self, instance):
        representations = instance.data.get("representations")
        if not representations:
            self.log.info("No representations at instance : `{}`".format(
                instance))
            return

        # get colorspace settings
        context = instance.context
        config_data, file_rules = self.get_colorspace_settings(context)

        # loop representations
        for representation in representations:
            # skip if colorspaceData is already at representation
            if representation.get("colorspaceData"):
                continue

            self.set_representation_colorspace(
                representation, context,
                config_data, file_rules
            )
