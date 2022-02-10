import os
import pyblish.api
import openpype.api as pype


class CollectSceneVersion(pyblish.api.ContextPlugin):
    """Finds version in the filename or passes the one found in the context
        Arguments:
        version (int, optional): version number of the publish
    """

    order = pyblish.api.CollectorOrder
    label = 'Collect Scene Version'
    # configurable in Settings
    hosts = [
        "aftereffects",
        "blender",
        "celaction",
        "fusion",
        "harmony",
        "hiero",
        "houdini",
        "maya",
        "nuke",
        "photoshop",
        "resolve",
        "tvpaint"
    ]

    # in some cases of headless publishing (for example webpublisher using PS)
    # you want to ignore version from name and let integrate use next version
    skip_hosts_headless_publish = []

    def process(self, context):
        # tests should be close to regular publish as possible
        if (
            os.environ.get("HEADLESS_PUBLISH")
            and not os.environ.get("IS_TEST")
            and context.data["hostName"] in self.skip_hosts_headless_publish):
            self.log.debug("Skipping for headless publishing")
            return

        assert context.data.get('currentFile'), "Cannot get current file"
        filename = os.path.basename(context.data.get('currentFile'))

        if '<shell>' in filename:
            return

        version = pype.get_version_from_path(filename)
        assert version, "Cannot determine version"

        rootVersion = int(version)
        context.data['version'] = rootVersion
        self.log.info("{}".format(type(rootVersion)))
        self.log.info('Scene Version: %s' % context.data.get('version'))
