import os
import pyblish.api
import openpype.api as pype


class CollectSceneVersion(pyblish.api.ContextPlugin):
    """Finds version in the filename or passes the one found in the context
        Arguments:
        version (int, optional): version number of the publish
    """

    order = pyblish.api.CollectorOrder
    label = 'Collect Version'

    def process(self, context):
        if "standalonepublisher" in context.data.get("host", []):
            return

        if "unreal" in pyblish.api.registered_hosts():
            return

        assert context.data.get('currentFile'), "Cannot get curren file"
        filename = os.path.basename(context.data.get('currentFile'))

        if '<shell>' in filename:
            return

        version = pype.get_version_from_path(filename)
        assert version, "Cannot determine version"

        rootVersion = int(version)
        context.data['version'] = rootVersion
        self.log.info("{}".format(type(rootVersion)))
        self.log.info('Scene Version: %s' % context.data.get('version'))
