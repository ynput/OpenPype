import ftrack_api
from pype.ftrack import BaseEvent, lib


class SyncToAvalon(BaseEvent):

    priority = 100

    ignore_entityType = [
        'assetversion', 'job', 'user', 'reviewsessionobject', 'timer',
        'socialfeed', 'socialnotification', 'timelog'
    ]

    def launch(self, session, event):
        ca_mongoid = lib.get_ca_mongoid()
        # If mongo_id textfield has changed: RETURN!
        # - infinite loop
        for ent in event['data']['entities']:
            if ent.get('keys') is not None:
                if ca_mongoid in ent['keys']:
                    return

        entities = self._get_entities(session, event, self.ignore_entityType)
        ft_project = None
        # get project
        for entity in entities:
            try:
                base_proj = entity['link'][0]
            except Exception:
                continue
            ft_project = session.get(base_proj['type'], base_proj['id'])
            break

        for ent_info in event['data']['entities']:
            # filter project
            if ent_info.get("entityType") != "show":
                continue

            if ent_info.get("action") != "update":
                continue

            changes = ent_info.get("changes") or {}
            if 'avalon_auto_sync' not in changes:
                continue

            auto_sync = changes['avalon_auto_sync']["new"]
            if auto_sync == "1":
                # Trigger sync to avalon action if auto sync was turned on
                self.log.debug((
                    "Auto sync was turned on for project <{}>."
                    " Triggering syncToAvalon action."
                ).format(ft_project["full_name"]))
                selection = [{
                    "entityId": ft_project["id"],
                    "entityType": "show"
                }]
                # Stop event so sync hierarchical won't be affected
                # - other event should not be affected since auto-sync
                #   is in all cases single data event
                event.stop()
                # Trigger action
                self.trigger_action(
                    action_name="sync.to.avalon.server",
                    event=event,
                    selection=selection
                )
            # Exit for both cases
            return True

        # check if project is set to auto-sync
        if (
            ft_project is None or
            'avalon_auto_sync' not in ft_project['custom_attributes'] or
            ft_project['custom_attributes']['avalon_auto_sync'] is False
        ):
            return

        # check if project have Custom Attribute 'avalon_mongo_id'
        if ca_mongoid not in ft_project['custom_attributes']:
            message = (
                "Custom attribute '{}' for 'Project' is not created"
                " or don't have set permissions for API"
            ).format(ca_mongoid)
            self.log.warning(message)
            self.show_message(event, message, False)
            return

        # get avalon project if possible
        import_entities = []

        custom_attributes = lib.get_avalon_attr(session)

        avalon_project = lib.get_avalon_project(ft_project)
        if avalon_project is None:
            import_entities.append(ft_project)

        for entity in entities:
            if entity.entity_type.lower() in ['task']:
                entity = entity['parent']

            if 'custom_attributes' not in entity:
                continue
            if ca_mongoid not in entity['custom_attributes']:

                message = (
                    "Custom attribute '{}' for '{}' is not created"
                    " or don't have set permissions for API"
                ).format(ca_mongoid, entity.entity_type)

                self.log.warning(message)
                self.show_message(event, message, False)
                return

            if entity not in import_entities:
                import_entities.append(entity)

        if len(import_entities) < 1:
            return

        try:
            for entity in import_entities:
                result = lib.import_to_avalon(
                    session=session,
                    entity=entity,
                    ft_project=ft_project,
                    av_project=avalon_project,
                    custom_attributes=custom_attributes
                )
                if 'errors' in result and len(result['errors']) > 0:
                    session.commit()
                    lib.show_errors(self, event, result['errors'])

                    return

                if avalon_project is None:
                    if 'project' in result:
                        avalon_project = result['project']

        except Exception as e:
            # reset session to clear it
            session.rollback()

            message = str(e)
            title = 'Hey You! Unknown Error has been raised! (*look below*)'
            ftrack_message = (
                'SyncToAvalon event ended with unexpected error'
                ' please check log file or contact Administrator'
                ' for more information.'
            )
            items = [
                {'type': 'label', 'value': '# Fatal Error'},
                {'type': 'label', 'value': '<p>{}</p>'.format(ftrack_message)}
            ]
            self.show_interface(items, title, event=event)
            self.log.error(
                'Fatal error during sync: {}'.format(message), exc_info=True
            )

        return


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''
    SyncToAvalon(session, plugins_presets).register()
