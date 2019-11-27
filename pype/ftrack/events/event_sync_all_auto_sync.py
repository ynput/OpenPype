from pype.ftrack import BaseEvent


class SyncAllAutoSyncProjects(BaseEvent):
    ignore_me = True
    def register(self):
        '''Registers the event, subscribing the discover and launch topics.'''
        self.session.event_hub.subscribe(
            'topic=pype.storer.started',
            self.launch
        )

    def launch(self, event):
        session = self.session
        projects = session.query("Project").all()
        if not projects:
            return False

        selections = []
        for project in projects:
            if project["status"] != "active":
                continue

            auto_sync = project["custom_attributes"].get("avalon_auto_sync")
            if not auto_sync:
                continue

            selections.append({
                "entityId": project["id"],
                "entityType": "show"
            })

        if not selections:
            return

        user = session.query(
            "User where username is \"{}\"".format(session.api_user)
        ).one()
        user_data = {
            "username": user["username"],
            "id": user["id"]
        }
        action_name = "sync.to.avalon.server"

        for selection in selections:
            self.trigger_action(
                action_name,
                selection=[selection],
                user_data=user_data
            )

        return True


def register(session, plugins_presets={}):
    """Register plugin. Called when used as an plugin."""
    SyncAllAutoSyncProjects(session, plugins_presets).register()
