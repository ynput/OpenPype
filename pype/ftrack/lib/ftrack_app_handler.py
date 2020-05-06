import os
import sys
import platform
import avalon.lib
import acre
from pype import lib as pypelib
from pypeapp import config
from .ftrack_action_handler import BaseAction

from pypeapp import Anatomy


class AppAction(BaseAction):
    """Application Action class.

    Args:
        session (ftrack_api.Session): Session where action will be registered.
        label (str): A descriptive string identifing your action.
        varaint (str, optional): To group actions together, give them the same
            label and specify a unique variant per action.
        identifier (str): An unique identifier for app.
        description (str): A verbose descriptive text for you action.
        icon (str): Url path to icon which will be shown in Ftrack web.
    """

    type = "Application"
    preactions = ["start.timer"]

    def __init__(
        self, session, label, name, executable, variant=None,
        icon=None, description=None, preactions=[], plugins_presets={}
    ):
        self.label = label
        self.identifier = name
        self.executable = executable
        self.variant = variant
        self.icon = icon
        self.description = description
        self.preactions.extend(preactions)

        super().__init__(session, plugins_presets)
        if label is None:
            raise ValueError("Action missing label.")
        if name is None:
            raise ValueError("Action missing identifier.")
        if executable is None:
            raise ValueError("Action missing executable.")

    def register(self):
        """Registers the action, subscribing the discover and launch topics."""

        discovery_subscription = (
            "topic=ftrack.action.discover and source.user.username={0}"
        ).format(self.session.api_user)

        self.session.event_hub.subscribe(
            discovery_subscription,
            self._discover,
            priority=self.priority
        )

        launch_subscription = (
            "topic=ftrack.action.launch"
            " and data.actionIdentifier={0}"
            " and source.user.username={1}"
        ).format(
            self.identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            launch_subscription,
            self._launch
        )

    def discover(self, session, entities, event):
        """Return true if we can handle the selected entities.

        Args:
            session (ftrack_api.Session): Helps to query necessary data.
            entities (list): Object of selected entities.
            event (ftrack_api.Event): Ftrack event causing discover callback.
        """

        if (
            len(entities) != 1 or
            entities[0].entity_type.lower() != "task"
        ):
            return False

        entity = entities[0]
        if entity["parent"].entity_type.lower() == "project":
            return False

        ft_project = self.get_project_from_entity(entity)
        database = pypelib.get_avalon_database()
        project_name = ft_project["full_name"]
        avalon_project = database[project_name].find_one({
            "type": "project"
        })

        if not avalon_project:
            return False

        project_apps = avalon_project["config"].get("apps", [])
        apps = [app["name"] for app in project_apps]
        if self.identifier in apps:
            return True
        return False

    def _launch(self, event):
        entities = self._translate_event(event)

        preactions_launched = self._handle_preactions(
            self.session, event
        )
        if preactions_launched is False:
            return

        response = self.launch(self.session, entities, event)

        return self._handle_result(response)

    def launch(self, session, entities, event):
        """Callback method for the custom action.

        return either a bool (True if successful or False if the action failed)
        or a dictionary with they keys `message` and `success`, the message
        should be a string and will be displayed as feedback to the user,
        success should be a bool, True if successful or False if the action
        failed.

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and
        the entity id. If the entity is a hierarchical you will always get
        the entity type TypedContext, once retrieved through a get operation
        you will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        """

        entity = entities[0]
        ft_project = self.get_project_from_entity(entity)
        project_name = ft_project["full_name"]

        database = pypelib.get_avalon_database()

        # Get current environments
        env_list = [
            "AVALON_PROJECT",
            "AVALON_SILO",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP",
            "AVALON_APP_NAME"
        ]
        env_origin = {}
        for env in env_list:
            env_origin[env] = os.environ.get(env, None)

        # set environments for Avalon
        os.environ["AVALON_PROJECT"] = project_name
        os.environ["AVALON_SILO"] = entity["ancestors"][0]["name"]
        os.environ["AVALON_ASSET"] = entity["parent"]["name"]
        os.environ["AVALON_TASK"] = entity["name"]
        os.environ["AVALON_APP"] = self.identifier.split("_")[0]
        os.environ["AVALON_APP_NAME"] = self.identifier

        anatomy = Anatomy(project_name)

        asset_doc = database[project_name].find_one({
            "type": "asset",
            "name": entity["parent"]["name"]
        })
        parents = asset_doc["data"]["parents"]

        hierarchy = ""
        if parents:
            hierarchy = os.path.join(*parents)

        os.environ["AVALON_HIERARCHY"] = hierarchy

        application = avalon.lib.get_application(os.environ["AVALON_APP_NAME"])

        data = {
            "root": os.environ.get("PYPE_STUDIO_PROJECTS_MOUNT"),
            "project": {
                "name": ft_project["full_name"],
                "code": ft_project["name"]
            },
            "task": entity["name"],
            "asset": entity["parent"]["name"],
            "app": application["application_dir"],
            "hierarchy": hierarchy
        }

        av_project = database[project_name].find_one({"type": 'project'})
        templates = None
        if av_project:
            work_template = av_project.get('config', {}).get('template', {}).get(
                'work', None
            )
        work_template = None
        try:
            work_template = work_template.format(**data)
        except Exception:
            try:
                anatomy = anatomy.format(data)
                work_template = anatomy["work"]["folder"]

            except Exception as exc:
                msg = "{} Error in anatomy.format: {}".format(
                    __name__, str(exc)
                )
                self.log.error(msg, exc_info=True)
                return {
                    'success': False,
                    'message': msg
                }

        workdir = os.path.normpath(work_template)
        os.environ["AVALON_WORKDIR"] = workdir
        try:
            os.makedirs(workdir)
        except FileExistsError:
            pass

        # collect all parents from the task
        parents = []
        for item in entity['link']:
            parents.append(session.get(item['type'], item['id']))

        # collect all the 'environment' attributes from parents
        tools_attr = [os.environ["AVALON_APP"], os.environ["AVALON_APP_NAME"]]
        for parent in reversed(parents):
            # check if the attribute is empty, if not use it
            if parent['custom_attributes']['tools_env']:
                tools_attr.extend(parent['custom_attributes']['tools_env'])
                break

        tools_env = acre.get_tools(tools_attr)
        env = acre.compute(tools_env)
        env = acre.merge(env, current_env=dict(os.environ))
        env = acre.append(dict(os.environ), env)

        # Get path to execute
        st_temp_path = os.environ['PYPE_CONFIG']
        os_plat = platform.system().lower()

        # Path to folder with launchers
        path = os.path.join(st_temp_path, 'launchers', os_plat)
        # Full path to executable launcher
        execfile = None

        if application.get("launch_hook"):
            hook = application.get("launch_hook")
            self.log.info("launching hook: {}".format(hook))
            ret_val = pypelib.execute_hook(
                application.get("launch_hook"), env=env)
            if not ret_val:
                return {
                    'success': False,
                    'message': "Hook didn't finish successfully {0}"
                    .format(self.label)
                }

        if sys.platform == "win32":

            for ext in os.environ["PATHEXT"].split(os.pathsep):
                fpath = os.path.join(path.strip('"'), self.executable + ext)
                if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                    execfile = fpath
                    break
                pass

            # Run SW if was found executable
            if execfile is not None:
                # Store subprocess to varaible. This is due to Blender launch
                # bug. Please make sure Blender >=2.81 can be launched before
                # remove `_popen` variable.
                _popen = avalon.lib.launch(
                    executable=execfile, args=[], environment=env
                )
            else:
                return {
                    'success': False,
                    'message': "We didn't found launcher for {0}"
                    .format(self.label)
                }

        if sys.platform.startswith('linux'):
            execfile = os.path.join(path.strip('"'), self.executable)
            if os.path.isfile(execfile):
                try:
                    fp = open(execfile)
                except PermissionError as p:
                    self.log.exception('Access denied on {0} - {1}'.format(
                        execfile, p))
                    return {
                        'success': False,
                        'message': "Access denied on launcher - {}".format(
                            execfile)
                    }
                fp.close()
                # check executable permission
                if not os.access(execfile, os.X_OK):
                    self.log.error('No executable permission on {}'.format(
                        execfile))
                    return {
                        'success': False,
                        'message': "No executable permission - {}".format(
                            execfile)
                        }

            else:
                self.log.error('Launcher doesn\'t exist - {}'.format(
                    execfile))
                return {
                    'success': False,
                    'message': "Launcher doesn't exist - {}".format(execfile)
                }

            # Run SW if was found executable
            if execfile is not None:
                # Store subprocess to varaible. This is due to Blender launch
                # bug. Please make sure Blender >=2.81 can be launched before
                # remove `_popen` variable.
                _popen = avalon.lib.launch(
                    '/usr/bin/env', args=['bash', execfile], environment=env
                )
            else:
                return {
                    'success': False,
                    'message': "We didn't found launcher for {0}"
                    .format(self.label)
                    }

        # Change status of task to In progress
        presets = config.get_presets()["ftrack"]["ftrack_config"]

        if 'status_update' in presets:
            statuses = presets['status_update']

            actual_status = entity['status']['name'].lower()
            already_tested = []
            ent_path = "/".join(
                [ent["name"] for ent in entity['link']]
            )
            while True:
                next_status_name = None
                for key, value in statuses.items():
                    if key in already_tested:
                        continue
                    if actual_status in value or '_any_' in value:
                        if key != '_ignore_':
                            next_status_name = key
                            already_tested.append(key)
                        break
                    already_tested.append(key)

                if next_status_name is None:
                    break

                try:
                    query = 'Status where name is "{}"'.format(
                        next_status_name
                    )
                    status = session.query(query).one()

                    entity['status'] = status
                    session.commit()
                    self.log.debug("Changing status to \"{}\" <{}>".format(
                        next_status_name, ent_path
                    ))
                    break

                except Exception:
                    session.rollback()
                    msg = (
                        'Status "{}" in presets wasn\'t found'
                        ' on Ftrack entity type "{}"'
                    ).format(next_status_name, entity.entity_type)
                    self.log.warning(msg)

        # Set origin avalon environments
        for key, value in env_origin.items():
            if value == None:
                value = ""
            os.environ[key] = value

        return {
            'success': True,
            'message': "Launching {0}".format(self.label)
        }
