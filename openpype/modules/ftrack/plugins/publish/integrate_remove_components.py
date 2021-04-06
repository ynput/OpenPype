import pyblish.api
import os


class IntegrateCleanComponentData(pyblish.api.InstancePlugin):
    """
    Cleaning up thumbnail an mov files after they have been integrated
    """

    order = pyblish.api.IntegratorOrder + 0.5
    label = 'Clean component data'
    families = ["ftrack"]
    optional = True
    active = False

    def process(self, instance):

        for comp in instance.data['representations']:
            self.log.debug('component {}'.format(comp))

            if "%" in comp['published_path'] or "#" in comp['published_path']:
                continue

            if comp.get('thumbnail') or ("thumbnail" in comp.get('tags', [])):
                os.remove(comp['published_path'])
                self.log.info('Thumbnail image was erased')

            elif comp.get('preview') or ("preview" in comp.get('tags', [])):
                os.remove(comp['published_path'])
                self.log.info('Preview mov file was erased')
