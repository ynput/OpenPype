import re
import subprocess

from openpype_modules.ftrack.lib import BaseEvent
from openpype_modules.ftrack.lib.avalon_sync import CUST_ATTR_ID_KEY
from openpype.pipeline import AvalonMongoDB

from bson.objectid import ObjectId

from openpype.api import Anatomy, get_project_settings


class UserAssigmentEvent(BaseEvent):
    """
    This script will intercept user assigment / de-assigment event and
    run shell script, providing as much context as possible.

    It expects configuration file ``presets/ftrack/user_assigment_event.json``.
    In it, you define paths to scripts to be run for user assigment event and
    for user-deassigment::
        {
            "add": [
                "/path/to/script1",
                "/path/to/script2"
            ],
            "remove": [
                "/path/to/script3",
                "/path/to/script4"
            ]
        }

    Those scripts are executed in shell. Three arguments will be passed to
    to them:
        1) user name of user (de)assigned
        2) path to workfiles of task user was (de)assigned to
        3) path to publish files of task user was (de)assigned to
    """

    db_con = AvalonMongoDB()

    def error(self, *err):
        for e in err:
            self.log.error(e)

    def _run_script(self, script, args):
        """
        Run shell script with arguments as subprocess

        :param script: script path
        :type script: str
        :param args: list of arguments passed to script
        :type args: list
        :returns: return code
        :rtype: int
        """
        p = subprocess.call([script, args], shell=True)
        return p

    def _get_task_and_user(self, session, action, changes):
        """
        Get Task and User entities from Ftrack session

        :param session: ftrack session
        :type session: ftrack_api.session
        :param action: event action
        :type action: str
        :param changes: what was changed by event
        :type changes: dict
        :returns: User and Task entities
        :rtype: tuple
        """
        if not changes:
            return None, None

        if action == 'add':
            task_id = changes.get('context_id', {}).get('new')
            user_id = changes.get('resource_id', {}).get('new')

        elif action == 'remove':
            task_id = changes.get('context_id', {}).get('old')
            user_id = changes.get('resource_id', {}).get('old')

        if not task_id:
            return None, None

        if not user_id:
            return None, None

        task = session.query('Task where id is "{}"'.format(task_id)).first()
        user = session.query('User where id is "{}"'.format(user_id)).first()

        return task, user

    def _get_asset(self, task):
        """
        Get asset from task entity

        :param task: Task entity
        :type task: dict
        :returns: Asset entity
        :rtype: dict
        """
        parent = task['parent']
        self.db_con.install()
        self.db_con.Session['AVALON_PROJECT'] = task['project']['full_name']

        avalon_entity = None
        parent_id = parent['custom_attributes'].get(CUST_ATTR_ID_KEY)
        if parent_id:
            parent_id = ObjectId(parent_id)
            avalon_entity = self.db_con.find_one({
                '_id': parent_id,
                'type': 'asset'
            })

        if not avalon_entity:
            avalon_entity = self.db_con.find_one({
                'type': 'asset',
                'name': parent['name']
            })

        if not avalon_entity:
            self.db_con.uninstall()
            msg = 'Entity "{}" not found in avalon database'.format(
                parent['name']
            )
            self.error(msg)
            return {
                'success': False,
                'message': msg
            }
        self.db_con.uninstall()
        return avalon_entity

    def _get_hierarchy(self, asset):
        """
        Get hierarchy from Asset entity

        :param asset: Asset entity
        :type asset: dict
        :returns: hierarchy string
        :rtype: str
        """
        return asset['data']['hierarchy']

    def _get_template_data(self, task):
        """
        Get data to fill template from task

        .. seealso:: :mod:`openpype.api.Anatomy`

        :param task: Task entity
        :type task: dict
        :returns: data for anatomy template
        :rtype: dict
        """
        project_name = task['project']['full_name']
        project_code = task['project']['name']

        # fill in template data
        asset = self._get_asset(task)
        t_data = {
            'project': {
                'name': project_name,
                'code': project_code
            },
            'asset': asset['name'],
            'task': task['name'],
            'hierarchy': self._get_hierarchy(asset)
        }

        return t_data

    def launch(self, session, event):
        if not event.get("data"):
            return

        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        # load shell scripts presets
        tmp_by_project_name = {}
        for entity_info in entities_info:
            if entity_info.get('entity_type') != 'Appointment':
                continue

            task_entity, user_entity = self._get_task_and_user(
                session,
                entity_info.get('action'),
                entity_info.get('changes')
            )

            if not task_entity or not user_entity:
                self.log.error("Task or User was not found.")
                continue

            # format directories to pass to shell script
            project_name = task_entity["project"]["full_name"]
            project_data = tmp_by_project_name.get(project_name) or {}
            if "scripts_by_action" not in project_data:
                project_settings = get_project_settings(project_name)
                _settings = (
                    project_settings["ftrack"]["events"]["user_assignment"]
                )
                project_data["scripts_by_action"] = _settings.get("scripts")
                tmp_by_project_name[project_name] = project_data

            scripts_by_action = project_data["scripts_by_action"]
            if not scripts_by_action:
                continue

            if "anatomy" not in project_data:
                project_data["anatomy"] = Anatomy(project_name)
                tmp_by_project_name[project_name] = project_data

            anatomy = project_data["anatomy"]
            data = self._get_template_data(task_entity)
            anatomy_filled = anatomy.format(data)
            # formatting work dir is easiest part as we can use whole path
            work_dir = anatomy_filled["work"]["folder"]
            # we also need publish but not whole
            anatomy_filled.strict = False
            publish = anatomy_filled["publish"]["folder"]

            # now find path to {asset}
            m = re.search(
                "(^.+?{})".format(data["asset"]),
                publish
            )

            if not m:
                msg = 'Cannot get part of publish path {}'.format(publish)
                self.log.error(msg)
                return {
                    'success': False,
                    'message': msg
                }
            publish_dir = m.group(1)

            username = user_entity["username"]
            event_entity_action = entity_info["action"]
            for script in scripts_by_action.get(event_entity_action):
                self.log.info((
                    "[{}] : running script for user {}"
                ).format(event_entity_action, username))
                self._run_script(script, [username, work_dir, publish_dir])

        return True


def register(session):
    """
    Register plugin. Called when used as an plugin.
    """

    UserAssigmentEvent(session).register()
