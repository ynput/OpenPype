import shutil
import pype
import pyblish.api


class VersionUpScene(pyblish.api.ContextPlugin):
    order = pyblish.api.IntegratorOrder + 0.5
    label = 'Version Up Scene'
    families = ['workfile']
    optional = True
    active = True

    def process(self, context):
        current_file = context.data.get('currentFile')
        v_up = pype.lib.version_up(current_file)
        self.log.debug('Current file is: {}'.format(current_file))
        self.log.debug('Version up: {}'.format(v_up))

        shutil.copy2(current_file, v_up)
        self.log.info('Scene saved into new version: {}'.format(v_up))
