import pyblish.api
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
                      'mayaascii': 'scene',
                      'model': 'geo',
                      'rig': 'rig',
                      'setdress': 'setdress',
                      'pointcache': 'cache',
                      'render': 'render',
                      'render2d': 'render',
                      'nukescript': 'comp',
                      'write': 'render',
                      'review': 'mov',
                      'plate': 'img',
                      'audio': 'audio',
                      'workfile': 'scene',
                      'animation': 'cache',
                      'image': 'img',
                      'reference': 'reference'
                      }

    def process(self, instance):
        self.ftrack_locations = {}
        self.log.debug('instance {}'.format(instance))

        if instance.data.get('version'):
            version_number = int(instance.data.get('version'))
        else:
            raise ValueError("Instance version not set")

        family = instance.data['family'].lower()

        asset_type = instance.data.get("ftrackFamily")
        if not asset_type and family in self.family_mapping:
            asset_type = self.family_mapping[family]

        # Ignore this instance if neither "ftrackFamily" or a family mapping is
        # found.
        if not asset_type:
            return

        componentList = []
        ft_session = instance.context.data["ftrackSession"]

        for comp in instance.data['representations']:
            self.log.debug('component {}'.format(comp))

            if comp.get('thumbnail') or ("thumbnail" in comp.get('tags', [])):
                location = self.get_ftrack_location(
                    'ftrack.server', ft_session
                )
                component_data = {
                    "name": "thumbnail"  # Default component name is "main".
                }
                comp['thumbnail'] = True
            elif comp.get('ftrackreview') or ("ftrackreview" in comp.get('tags', [])):
                '''
                Ftrack bug requirement:
                    - Start frame must be 0
                    - End frame must be {duration}
                EXAMPLE: When mov has 55 frames:
                    - Start frame should be 0
                    - End frame should be 55 (do not ask why please!)
                '''
                start_frame = 0
                end_frame = 1
                if 'frameEndFtrack' in comp and 'frameStartFtrack' in comp:
                    end_frame += (
                        comp['frameEndFtrack'] - comp['frameStartFtrack']
                    )
                else:
                    end_frame += (
                        instance.data["frameEnd"] - instance.data["frameStart"]
                    )

                fps = comp.get('fps')
                if fps is None:
                    fps = instance.data.get(
                        "fps", instance.context.data['fps']
                    )

                comp['fps'] = fps

                location = self.get_ftrack_location(
                    'ftrack.server', ft_session
                )
                component_data = {
                    # Default component name is "main".
                    "name": "ftrackreview-mp4",
                    "metadata": {'ftr_meta': json.dumps({
                                 'frameIn': int(start_frame),
                                 'frameOut': int(end_frame),
                                 'frameRate': float(comp['fps'])})}
                }
                comp['thumbnail'] = False
            else:
                component_data = {
                    "name": comp['name']
                }
                location = self.get_ftrack_location(
                    'ftrack.unmanaged', ft_session
                )
                comp['thumbnail'] = False

            self.log.debug('location {}'.format(location))

            component_item = {
                "assettype_data": {
                    "short": asset_type,
                },
                "asset_data": {
                    "name": instance.data["subset"],
                },
                "assetversion_data": {
                    "version": version_number,
                    "comment": instance.context.data.get("comment", "")
                },
                "component_data": component_data,
                "component_path": comp['published_path'],
                'component_location': location,
                "component_overwrite": False,
                "thumbnail": comp['thumbnail']
            }

            # Add custom attributes for AssetVersion
            assetversion_cust_attrs = {}
            intent_val = instance.context.data.get("intent")
            if intent_val and isinstance(intent_val, dict):
                intent_val = intent_val.get("value")

            if intent_val:
                assetversion_cust_attrs["intent"] = intent_val

            component_item["assetversion_data"]["custom_attributes"] = (
                assetversion_cust_attrs
            )

            componentList.append(component_item)
            # Create copy with ftrack.unmanaged location if thumb or prev
            if comp.get('thumbnail') or comp.get('preview') \
                    or ("preview" in comp.get('tags', [])) \
                    or ("thumbnail" in comp.get('tags', [])):
                unmanaged_loc = self.get_ftrack_location(
                    'ftrack.unmanaged', ft_session
                )

                component_data_src = component_data.copy()
                name = component_data['name'] + '_src'
                component_data_src['name'] = name

                component_item_src = {
                    "assettype_data": {
                        "short": asset_type,
                    },
                    "asset_data": {
                        "name": instance.data["subset"],
                    },
                    "assetversion_data": {
                        "version": version_number,
                    },
                    "component_data": component_data_src,
                    "component_path": comp['published_path'],
                    'component_location': unmanaged_loc,
                    "component_overwrite": False,
                    "thumbnail": False
                }

                componentList.append(component_item_src)

        self.log.debug('componentsList: {}'.format(str(componentList)))
        instance.data["ftrackComponentsList"] = componentList

    def get_ftrack_location(self, name, session):
        if name in self.ftrack_locations:
            return self.ftrack_locations[name]

        location = session.query(
            'Location where name is "{}"'.format(name)
        ).one()
        self.ftrack_locations[name] = location
        return location
