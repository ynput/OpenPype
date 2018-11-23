import pyblish.api


@pyblish.api.log
class CollectFtrackAsset(pyblish.api.ContextPlugin):

    """ Adds ftrack asset information to the instance
    """

    order = pyblish.api.CollectorOrder + 0.45
    label = 'Asset Attributes'

    def process(self, context):

        for instance in context:

            self.log.info('instance {}'.format(instance))
            # skipping instance if ftrackData isn't present
            if not context.has_data('ftrackData'):
                self.log.info('No ftrackData present. Skipping this instance')
                continue

            # skipping instance if ftrackComponents isn't present
            if not instance.has_data('ftrackComponents'):
                self.log.info('No ftrackComponents present\
                               Skipping this instance')
                continue

            ftrack_data = context.data['ftrackData'].copy()

            if not instance.data.get("ftrackAssetName"):
                asset_name = instance.data["subset"]
                instance.data['ftrackAssetName'] = asset_name

            # task type filtering
            task_type = ftrack_data['Task']['type'].lower()
            asset_type = ''
            family = instance.data['family'].lower()

            self.log.debug('task type {}'.format(task_type))

            if family == 'camera':
                asset_type = 'cam'
            elif family == 'look':
                asset_type = 'look'
            elif family == 'mayaAscii':
                asset_type = 'scene'
            elif family == 'model':
                asset_type = 'geo'
            elif family == 'rig':
                asset_type = 'rig'
            elif family == 'setdress':
                asset_type = 'setdress'
            elif family == 'pointcache':
                asset_type = 'cache'
            elif family == 'previz':
                asset_type = 'mov'


            if asset_type:
                instance.data['ftrackAssetType'] = asset_type
                self.log.debug('asset type: {}'.format(asset_type))

            self.log.debug('asset name: {}'.format(asset_name))
