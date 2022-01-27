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

    def process(self, context):
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
