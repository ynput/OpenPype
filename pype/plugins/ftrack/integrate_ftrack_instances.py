import pyblish.api
import os

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
                      'review': 'mov'}


    def process(self, instance):

        self.log.debug('instance {}'.format(instance))

        asset_name = instance.data["subset"]
        assumed_data = instance.data["assumedTemplateData"]
        assumed_version = assumed_data["version"]
        version_number = int(assumed_version)
        family = instance.data['family'].lower()
        asset_type = ''

        asset_type = self.family_mapping[family]

        componentList = []

        transfers = instance.data["transfers"]

        ft_session = instance.context.data["ftrackSession"]
        location = ft_session.query('Location where name is "ftrack.unmanaged"').one()
        self.log.debug('location {}'.format(location))

        for src, dest in transfers:
            filename, ext = os.path.splitext(src)
            self.log.debug('source filename: ' + filename)
            self.log.debug('source ext: ' + ext)

            componentList.append({"assettype_data": {
                                      "short": asset_type,
                                      },
                                      "assetversion_data": {
                                        "version": version_number,
                                      },
                                      "component_data": {
                                        "name": ext[1:],  # Default component name is "main".
                                      },
                                        "component_path": dest,
                                        'component_location': location,
                                        "component_overwrite": False,
                                      }
                                      )

        self.log.debug('componentsList: {}'.format(str(componentList)))
        instance.data["ftrackComponentsList"] = componentList
