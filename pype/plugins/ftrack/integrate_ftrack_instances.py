import pyblish.api
import os
import clique


class IntegrateFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data

    Add ftrack component list to instance.


    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = 'Integrate Ftrack Component'

    family_mapping = {'camera': 'cam',
                      'look': 'look',
                      'mayaAscii': 'scene',
                      'model': 'geo',
                      'rig': 'rig',
                      'setdress': 'setdress',
                      'pointcache': 'cache',
                      'review': 'mov',
                      'write': 'comp'}

    def process(self, instance):

        self.log.debug('instance {}'.format(instance))

        assumed_data = instance.data["assumedTemplateData"]
        assumed_version = assumed_data["version"]
        version_number = int(assumed_version)
        family = instance.data['family'].lower()
        asset_type = ''

        asset_type = self.family_mapping[family]

        componentList = []

        dst_list = instance.data['destination_list']

        ft_session = instance.context.data["ftrackSession"]
        location = ft_session.query(
            'Location where name is "ftrack.unmanaged"').one()
        self.log.debug('location {}'.format(location))

        for file in instance.data['destination_list']:
            self.log.debug('file {}'.format(file))

        for file in dst_list:
            filename, ext = os.path.splitext(file)
            self.log.debug('dest ext: ' + ext)

            componentList.append({"assettype_data": {
                "short": asset_type,
            },
                "asset_data": {
                "name": instance.data["subset"],
            },
                "assetversion_data": {
                "version": version_number,
            },
                "component_data": {
                "name": ext[1:],  # Default component name is "main".
            },
                "component_path": file,
                'component_location': location,
                "component_overwrite": False,
            }
            )

        self.log.debug('componentsList: {}'.format(str(componentList)))
        instance.data["ftrackComponentsList"] = componentList
