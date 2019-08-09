from pype.vendor import ftrack_api
from pype.ftrack import BaseAction


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
        self.start_ftrack_timer(entity)
        try:
            self.start_clockify_timer(entity)
        except Exception:
            self.log.warning(
                'Failed starting Clockify timer for task: ' + entity['name']
            )
        return

    def start_ftrack_timer(self, task):
        user_query = 'User where username is "{}"'.format(self.session.api_user)
        user = self.session.query(user_query).one()
        self.log.info('Starting Ftrack timer for task: ' + task['name'])
        user.start_timer(task, force=True)
        self.session.commit()

    def start_clockify_timer(self, task):
        # Validate Clockify settings if Clockify is required
        clockify_timer = os.environ.get('CLOCKIFY_WORKSPACE', None)
        if clockify_timer is None:
            return

        from pype.clockify import ClockifyAPI
        clockapi = ClockifyAPI()
        if clockapi.verify_api() is False:
            return
        task_type = task['type']['name']
        project_name = task['project']['full_name']

        def get_parents(entity):
            output = []
            if entity.entity_type.lower() == 'project':
                return output
            output.extend(get_parents(entity['parent']))
            output.append(entity['name'])

            return output

        desc_items = get_parents(task['parent'])
        desc_items.append(task['name'])
        description = '/'.join(desc_items)

        project_id = clockapi.get_project_id(project_name)
        tag_ids = []
        tag_ids.append(clockapi.get_tag_id(task_type))
        clockapi.start_time_entry(
            description, project_id, tag_ids=tag_ids
        )
        self.log.info('Starting Clockify timer for task: ' + task['name'])


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    StartTimer(session, plugins_presets).register()
