import pyblish.api
import os

class IntegrateFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data

    Add empty ftrack components to instance.


    """

    order = pyblish.api.IntegratorOrder + 0.31
    label = 'Integrate Ftrack Instance'

    def process(self, instance):

        transfers = instance.data["transfers"]

        for src, dest in transfers:
            self.log.info("Copying file .. {} -> {}".format(src, dest))

            filename, ext = os.path.splitext(src)
            self.log.debug('source filename: ' + filename)
            self.log.debug('source ext: ' + ext)

            components = instance.data['ftrackComponents']

            components[str(ext)[1:]] = {'path': dest}

            self.log.debug('components: {}'.format(str(components)))
