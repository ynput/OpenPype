import pyblish.api


class IntegrateWorkfileVersion(pyblish.api.InstancePlugin):
    """
    Will desynchronize versioning from actual version of work file

    """

    order = pyblish.api.IntegratorOrder - 0.15
    label = 'Do not synchronize workfile version'
    families = ["clip"]
    optional = True
    active = False

    def process(self, instance):
        if instance.data['version']:
            del(instance.data['version'])
            self.log.info('Instance version was removed')
