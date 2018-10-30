# import ftrack_api as local session
import ftrack_api
from utils import print_entity_head
#
session = ftrack_api.Session()

# ----------------------------------


def file_version_statuses(event):
    '''Set new version status to data if version matches given types'''

    # start of event procedure ----------------------------------
    for entity in event['data'].get('entities', []):

        # Filter to new assetversions
        if (entity['entityType'] == 'assetversion'
                and entity['action'] == 'add'):

            print "\n\nevent script: {}".format(__file__)
            print_entity_head.print_entity_head(entity, session)

            version = session.get('AssetVersion', entity['entityId'])
            asset_type = version['asset']['type']['name']
            file_status = session.query(
                'Status where name is "{}"'.format('data')).one()

            # Setting task status
            try:
                if asset_type.lower() in ['cam', 'cache', 'rig', 'scene']:
                    version['status'] = file_status
            except Exception as e:
                print '!!! status couldnt be set [ {} ]'.format(e)
            else:
                print '>>> updated to [ {} ]'.format(file_status['name'])

        session.commit()
    # end of event procedure ----------------------------------
