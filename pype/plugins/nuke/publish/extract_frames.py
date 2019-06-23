import pyblish


class ExtractFramesToIntegrate(pyblish.api.InstancePlugin):
    """Extract rendered frames for integrator
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract rendered frames"
    hosts = ["nuke"]
    families = ["render"]

    def process(self, instance\
        return

        # staging_dir = instance.data.get('stagingDir', None)
        # output_dir = instance.data.get('outputDir', None)
        #
        # if not staging_dir:
        #     staging_dir = output_dir
        #     instance.data['stagingDir'] = staging_dir
        #     # instance.data['transfer'] = False
