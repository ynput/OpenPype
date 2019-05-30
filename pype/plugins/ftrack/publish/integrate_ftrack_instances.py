import pyblish.api
import os
import json


class IntegrateFtrackInstance(pyblish.api.InstancePlugin):
    """Collect ftrack component data

    Add ftrack component list to instance.


    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = 'Integrate Ftrack Component'
    families = ["ftrack"]

    family_mapping = {'camera': 'cam',
                      'look': 'look',
                      'mayaAscii': 'scene',
                      'model': 'geo',
                      'rig': 'rig',
                      'setdress': 'setdress',
                      'pointcache': 'cache',
                      'write': 'img',
                      'render': 'render',
                      'nukescript': 'comp',
                      'review': 'mov',
                      'plates': 'img'
                      }

    def process(self, instance):
        self.log.debug('instance {}'.format(instance))
        assumed_data = instance.data["assumedTemplateData"]
        assumed_version = assumed_data["version"]
        version_number = int(assumed_version)
        if instance.data.get('version'):
            version_number = int(instance.data.get('version'))

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
            thumbnail = False

            if ext in ['.mov']:
                if not instance.data.get('startFrameReview'):
                    instance.data['startFrameReview'] = instance.data['startFrame']
                if not instance.data.get('endFrameReview'):
                    instance.data['endFrameReview'] = instance.data['endFrame']
                location = ft_session.query(
                    'Location where name is "ftrack.server"').one()
                component_data = {
                    # Default component name is "main".
                    "name": "ftrackreview-mp4",
                    "metadata": {'ftr_meta': json.dumps({
                                 'frameIn': int(instance.data['startFrameReview']),
                                 'frameOut': int(instance.data['startFrameReview']),
                                 'frameRate': 25})}
                }
            elif ext in [".jpg", ".jpeg"]:
                component_data = {
                    "name": "thumbnail"  # Default component name is "main".
                }
                thumbnail = True
                location = ft_session.query(
                    'Location where name is "ftrack.server"').one()
            else:
                component_data = {
                    "name": ext[1:]  # Default component name is "main".
                }

                location = ft_session.query(
                    'Location where name is "ftrack.unmanaged"').one()

            self.log.debug('location {}'.format(location))

            componentList.append({"assettype_data": {
                "short": asset_type,
            },
                "asset_data": {
                "name": instance.data["subset"],
            },
                "assetversion_data": {
                "version": version_number,
            },
                "component_data": component_data,
                "component_path": file,
                'component_location': location,
                "component_overwrite": False,
                "thumbnail": thumbnail
            }
            )

        self.log.debug('componentsList: {}'.format(str(componentList)))
        instance.data["ftrackComponentsList"] = componentList
