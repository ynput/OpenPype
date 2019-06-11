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
                      'plate': 'img'
                      }

    def process(self, instance):
        self.log.debug('instance {}'.format(instance))

        if instance.data.get('version'):
            version_number = int(instance.data.get('version'))

        family = instance.data['family'].lower()

        asset_type = ''
        asset_type = self.family_mapping[family]

        componentList = []
        ft_session = instance.context.data["ftrackSession"]

        for comp in instance.data['representations']:
            self.log.debug('component {}'.format(comp))

            if comp.get('thumbnail'):
                location = ft_session.query(
                    'Location where name is "ftrack.server"').one()
                component_data = {
                    "name": "thumbnail"  # Default component name is "main".
                }
            elif comp.get('preview'):
                if not comp.get('startFrameReview'):
                    comp['startFrameReview'] = comp['startFrame']
                if not comp.get('endFrameReview'):
                    comp['endFrameReview'] = comp['endFrame']
                location = ft_session.query(
                    'Location where name is "ftrack.server"').one()
                component_data = {
                    # Default component name is "main".
                    "name": "ftrackreview-mp4",
                    "metadata": {'ftr_meta': json.dumps({
                                 'frameIn': int(comp['startFrameReview']),
                                 'frameOut': int(comp['endFrameReview']),
                                 'frameRate': comp['frameRate']})}
                }
                comp['thumbnail'] = False
            else:
                component_data = {
                    "name": comp['name']
                }
                location = ft_session.query(
                    'Location where name is "ftrack.unmanaged"').one()
                comp['thumbnail'] = False

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
                "component_path": comp['published_path'],
                'component_location': location,
                "component_overwrite": False,
                "thumbnail": comp['thumbnail']
            }
            )

        self.log.debug('componentsList: {}'.format(str(componentList)))
        instance.data["ftrackComponentsList"] = componentList
