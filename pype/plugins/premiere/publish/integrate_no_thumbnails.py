import pyblish.api
import os


class IntegrateCleanThumbs(pyblish.api.InstancePlugin):
    """
    Cleaning up thumbnail files after they have been integrated
    """

    order = pyblish.api.IntegratorOrder + 9
    label = 'Clean thumbnail files'
    families = ["clip"]
    optional = True
    active = True

    def process(self, instance):
        remove_file = [tt for t in instance.data['transfers']
                       for tt in t if 'jpg' in tt if 'temp' not in tt.lower()]
        if len(remove_file) is 1:
            os.remove(remove_file[0])
            self.log.info('Thumbnail image was erased')
