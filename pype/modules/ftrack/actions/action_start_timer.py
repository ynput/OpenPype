from pype.modules.ftrack.lib import BaseAction


class StartTimer(BaseAction):
    '''Starts timer.'''

    identifier = 'start.timer'
    label = 'Start timer'
    description = 'Starts timer'

    def discover(self, session, entities, event):
        return False

    def _handle_result(*arg):
        return

    def launch(self, session, entities, event):
        entity = entities[0]
        if entity.entity_type.lower() != 'task':
            return

        user = self.session.query(
            "User where username is \"{}\"".format(self.session.api_user)
        ).one()

        user.start_timer(entity, force=True)
        self.session.commit()

        self.log.info(
            "Starting Ftrack timer for task: {}".format(entity['name'])
        )

        return


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    StartTimer(session, plugins_presets).register()
