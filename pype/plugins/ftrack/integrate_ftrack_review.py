import pyblish.api
import os
import clique
import json


class IntegrateFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data

    Add ftrack component list to instance.


    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = 'Integrate Ftrack Component'
    families = ['review', 'ftrack']

    family_mapping = {'camera': 'cam',
                      'look': 'look',
                      'mayaAscii': 'scene',
                      'model': 'geo',
                      'rig': 'rig',
                      'setdress': 'setdress',
                      'pointcache': 'cache',
                      'review': 'mov',
                      'write': 'img',
                      'render': 'render'}

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


        for file in instance.data['destination_list']:
            self.log.debug('file {}'.format(file))

        for file in dst_list:
            filename, ext = os.path.splitext(file)
            self.log.debug('dest ext: ' + ext)

            component_name = "ftrackreview-mp4"
            location = ft_session.query(
                'Location where name is "ftrack.server"').one()
            metadata = {'ftr_meta': json.dumps({
                            'frameIn': int(instance.data["startFrame"]),
                            'frameOut': int(instance.data["startFrame"]),
                            'frameRate': 25})}


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
                "name": component_name,  # Default component name is "main".
                "metadata": metadata
            },
                "component_path": file,
                'component_location': location,
                "component_overwrite": False
            }
            )



        self.log.debug('componentsList: {}'.format(str(componentList)))
        instance.data["ftrackComponentsList"] = componentList
