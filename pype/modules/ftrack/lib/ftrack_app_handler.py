from pype import lib as pypelib
from pype.api import config
from .ftrack_action_handler import BaseAction


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
            len(entities) != 1
            or entities[0].entity_type.lower() != "task"
        ):
            return False

        entity = entities[0]
        if entity["parent"].entity_type.lower() == "project":
            return False

        avalon_project_apps = event["data"].get("avalon_project_apps", None)
        avalon_project_doc = event["data"].get("avalon_project_doc", None)
        if avalon_project_apps is None:
            if avalon_project_doc is None:
                ft_project = self.get_project_from_entity(entity)
                database = pypelib.get_avalon_database()
                project_name = ft_project["full_name"]
                avalon_project_doc = database[project_name].find_one({
                    "type": "project"
                }) or False
                event["data"]["avalon_project_doc"] = avalon_project_doc

            if not avalon_project_doc:
                return False

            project_apps_config = avalon_project_doc["config"].get("apps", [])
            avalon_project_apps = [
                app["name"] for app in project_apps_config
            ] or False
            event["data"]["avalon_project_apps"] = avalon_project_apps

        if not avalon_project_apps:
            return False

        return self.identifier in avalon_project_apps

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

        task_name = entity["name"]
        asset_name = entity["parent"]["name"]
        project_name = entity["project"]["full_name"]
        try:
            pypelib.launch_application(
                project_name, asset_name, task_name, self.identifier
            )

        except pypelib.ApplicationLaunchFailed as exc:
            self.log.error(str(exc))
            return {
                "success": False,
                "message": str(exc)
            }

        except Exception:
            msg = "Unexpected failure of application launch {}".format(
                self.label
            )
            self.log.error(msg, exc_info=True)
            return {
                "success": False,
                "message": msg
            }

        # Change status of task to In progress
        presets = config.get_presets()["ftrack"]["ftrack_config"]

        if "status_update" in presets:
            statuses = presets["status_update"]

            actual_status = entity["status"]["name"].lower()
            already_tested = []
            ent_path = "/".join(
                [ent["name"] for ent in entity["link"]]
            )
            while True:
                next_status_name = None
                for key, value in statuses.items():
                    if key in already_tested:
                        continue
                    if actual_status in value or "_any_" in value:
                        if key != "_ignore_":
                            next_status_name = key
                            already_tested.append(key)
                        break
                    already_tested.append(key)

                if next_status_name is None:
                    break

                try:
                    query = "Status where name is \"{}\"".format(
                        next_status_name
                    )
                    status = session.query(query).one()

                    entity["status"] = status
                    session.commit()
                    self.log.debug("Changing status to \"{}\" <{}>".format(
                        next_status_name, ent_path
                    ))
                    break

                except Exception:
                    session.rollback()
                    msg = (
                        "Status \"{}\" in presets wasn't found"
                        " on Ftrack entity type \"{}\""
                    ).format(next_status_name, entity.entity_type)
                    self.log.warning(msg)

        return {
            "success": True,
            "message": "Launching {0}".format(self.label)
        }
