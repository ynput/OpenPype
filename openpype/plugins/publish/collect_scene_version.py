import os
import pyblish.api

from openpype.lib import get_version_from_path
from openpype.tests.lib import is_in_tests
from openpype.pipeline import KnownPublishError


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
        "max",
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
            and not is_in_tests()
            and context.data["hostName"] in self.skip_hosts_headless_publish
        ):
            self.log.debug("Skipping for headless publishing")
            return

        if not context.data.get('currentFile'):
            raise KnownPublishError("Cannot get current workfile path. "
                                    "Make sure your scene is saved.")

        filename = os.path.basename(context.data.get('currentFile'))

        if '<shell>' in filename:
            return

        self.log.debug(
            "Collecting scene version from filename: {}".format(filename)
        )

        version = get_version_from_path(filename)
        if version is None:
            raise KnownPublishError("Unable to retrieve version number from "
                                    "filename: {}".format(filename))

        context.data['version'] = int(version)
        self.log.debug(
            "Collected scene version: {}".format(context.data.get('version'))
        )
