import pyblish.api
import ftrack


@pyblish.api.log
class ValidateFtrack(pyblish.api.InstancePlugin):

    """ Validate the existence of Asset, AssetVersion and Components.
    """

    order = pyblish.api.ValidatorOrder + 0.1
    optional = True
    label = 'Ftrack'

    def process(self, instance):

        context = instance.context

        # Skipping instance if ftrackData isn"t present.
        if not context.has_data("ftrackData"):
            msg = "No ftrackData present. "
            msg += "Skipping this instance: \"%s\"" % instance
            self.log.info(msg)
            return

        # Skipping instance if ftrackComponents isn"t present.
        if not instance.has_data("ftrackComponents"):
            msg = "No ftrackComponents present. "
            msg += "Skipping this instance: \"%s\"" % instance
            self.log.info(msg)
            return

        ftrack_data = context.data('ftrackData').copy()
        task = ftrack.Task(ftrack_data['Task']['id'])

        # checking asset
        create_asset = True
        asset = None
        if instance.has_data('ftrackAssetType'):
            asset_type = instance.data('ftrackAssetType')
        else:
            asset_type = ftrack_data['Task']['code']

        assets = task.getAssets(assetTypes=[asset_type])

        if len(assets) == 0:
            instance.set_data('ftrackAssetCreate', value=True)
            return

        if instance.has_data('ftrackAssetName'):

            # searching for existing asset
            asset_name = instance.data('ftrackAssetName')
            for a in assets:
                if asset_name.lower() == a.getName().lower():
                    asset = a
                    create_asset = False

                    msg = 'Found existing asset from ftrackAssetName'
                    self.log.info(msg)
        else:
            # if only one asset exists, then we'll use that asset
            msg = "Can't compute asset."
            if len(assets) == 1:
                print('FOUND ONE ASSET')
                for a in assets:
                    print a
                    asset = a
                    create_asset = False
                assert asset, msg
                self.log.info('Found existing asset by default.')
            elif len(assets) > 1:
                asset_name = ftrack_data['Task']['type']
                for a in assets:
                    msg += " Multiple assets on shot: \n\n%s" % a
                    if asset_name.lower() == a.getName().lower():
                        asset = a
                    create_asset = False
                assert asset, msg
                self.log.info('Found existing asset by default.')
            else:
                self.log.info('No asset found, new one will be created.')

        # adding asset to ftrack data
        if asset:
            asset_data = {'id': asset.getId(),
                          'name': asset.getName()}
            instance.set_data('ftrackAsset', value=asset_data)

        instance.set_data('ftrackAssetCreate', value=create_asset)

        # if we are creating a new asset,
        # then we don't need to validate the rest
        if create_asset:
            return

        # checking version
        assumed_data = instance.data["assumedTemplateData"]
        assumed_version = assumed_data["version"]

        version_number = int(assumed_version)
        create_version = True
        version = None

        # search for existing version
        for v in asset.getVersions():
            if int(v.getVersion()) == version_number:

                msg = "AssetVersion exists but is not visible in UI."
                assert v.get('ispublished'), msg

                version = v
                # ftrack_data['AssetVersion'] = {'id': v.getId(),
                #                                'number': version_number}
                asset_version = {'id': v.getId(), 'number': version_number}
                instance.set_data('ftrackAssetVersion', value=asset_version)

                create_version = False

                msg = 'Found existing version number: %s' % version_number
                self.log.info(msg)

        instance.set_data('ftrackAssetVersionCreate', value=create_version)

        # if we are creating a new asset version,
        # then we don't need to validate the rest
        if create_version:
            return

        # checking components
        online_components = version.getComponents()
        ftrack_components = instance.data('ftrackComponents').copy()

        for local_c in ftrack_components:
            for online_c in online_components:
                if local_c == online_c.getName():

                    # warning about existing components
                    msg = 'Component "%s" already exists. ' % local_c
                    msg += 'To replace it delete it in the browser first.'
                    if not ftrack_components[local_c].get("overwrite", False):
                        self.log.warning(msg)

                    # validating review components
                    if 'reviewable' in ftrack_components[local_c]:
                        msg = 'Reviewable component already exists in the\
                               version. To replace it\
                               delete it in the webUI first'
                        assert online_c.getName() not in (
                            'ftrackreview-mp4', 'ftrackreview-webm'), msg
