from pype.modules.ftrack.lib import BaseEvent
from pype.modules.ftrack.lib.avalon_sync import CustAttrIdKey
from pype.modules.ftrack.events.event_sync_to_avalon import SyncToAvalonEvent


class DelAvalonIdFromNew(BaseEvent):
    '''
    This event removes AvalonId from custom attributes of new entities
    Result:
    - 'Copy->Pasted' entities won't have same AvalonID as source entity

    Priority of this event must be less than SyncToAvalon event
    '''
    priority = SyncToAvalonEvent.priority - 1
    ignore_me = True

    def launch(self, session, event):
        created = []
        entities = event['data']['entities']
        for entity in entities:
            try:
                entity_id = entity['entityId']

                if entity.get('action', None) == 'add':
                    id_dict = entity['changes']['id']

                    if id_dict['new'] is not None and id_dict['old'] is None:
                        created.append(id_dict['new'])

                elif (
                    entity.get('action', None) == 'update' and
                    CustAttrIdKey in entity['keys'] and
                    entity_id in created
                ):
                    ftrack_entity = session.get(
                        self._get_entity_type(entity),
                        entity_id
                    )

                    cust_attr = ftrack_entity['custom_attributes'][
                        CustAttrIdKey
                    ]

                    if cust_attr != '':
                        ftrack_entity['custom_attributes'][CustAttrIdKey] = ''
                        session.commit()

            except Exception:
                session.rollback()
                continue


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''
    DelAvalonIdFromNew(session, plugins_presets).register()
