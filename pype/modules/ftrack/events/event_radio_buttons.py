import ftrack_api
from pype.modules.ftrack.lib import BaseEvent


class RadioButtons(BaseEvent):

    ignore_me = True

    def launch(self, session, event):
        '''Provides a readio button behaviour to any bolean attribute in
           radio_button group.'''

        # start of event procedure ----------------------------------
        for entity in event['data'].get('entities', []):

            if entity['entityType'] == 'assetversion':

                query = 'CustomAttributeGroup where name is "radio_button"'
                group = session.query(query).one()
                radio_buttons = []
                for g in group['custom_attribute_configurations']:
                    radio_buttons.append(g['key'])

                for key in entity['keys']:
                    if (key in radio_buttons and entity['changes'] is not None):
                        if entity['changes'][key]['new'] == '1':
                            version = session.get('AssetVersion',
                                                  entity['entityId'])
                            asset = session.get('Asset', entity['parentId'])
                            for v in asset['versions']:
                                if version is not v:
                                    v['custom_attributes'][key] = 0

            session.commit()


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    RadioButtons(session, plugins_presets).register()
