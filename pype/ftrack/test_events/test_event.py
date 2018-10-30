# import ftrack_api as local session
import ftrack_api
#
session = ftrack_api.Session()

# ----------------------------------


def test_event(event):
    '''just a testing event'''
    # start of event procedure ----------------------------------
    for entity in event['data'].get('entities', []):
        print(100*"_")
        print(entity['changes'])

    # end of event procedure ----------------------------------
