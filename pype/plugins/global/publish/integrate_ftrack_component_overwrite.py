import pyblish.api


class IntegrateFtrackComponentOverwrite(pyblish.api.InstancePlugin):
    """
    Set `component_overwrite` to True on all instances `ftrackComponentsList`
    """

    order = pyblish.api.IntegratorOrder + 0.49
    label = 'Overwrite ftrack created versions'
    families = ["clip"]
    optional = True
    active = False

    def process(self, instance):
        component_list = instance.data['ftrackComponentsList']

        for cl in component_list:
            cl['component_overwrite'] = True
            self.log.debug('Component {} overwriting'.format(
                cl['component_data']['name']))
