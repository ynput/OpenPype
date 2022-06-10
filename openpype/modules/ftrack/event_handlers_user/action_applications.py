import os

from openpype_modules.ftrack.lib import BaseAction
from openpype.lib.applications import (
    ApplicationManager,
    ApplicationLaunchFailed,
    ApplictionExecutableNotFound,
    CUSTOM_LAUNCH_APP_GROUPS
)
from openpype.pipeline import AvalonMongoDB


class AppplicationsAction(BaseAction):
    """Applications Action class."""

    type = "Application"
    label = "Application action"

    identifier = "openpype_app"
    _launch_identifier_with_id = None

    icon_url = os.environ.get("OPENPYPE_STATICS_SERVER")

    def __init__(self, *args, **kwargs):
        super(AppplicationsAction, self).__init__(*args, **kwargs)

        self.application_manager = ApplicationManager()
        self.dbcon = AvalonMongoDB()

    @property
    def discover_identifier(self):
        if self._discover_identifier is None:
            self._discover_identifier = "{}.{}".format(
                self.identifier, self.process_identifier()
            )
        return self._discover_identifier

    @property
    def launch_identifier(self):
        if self._launch_identifier is None:
            self._launch_identifier = "{}.*".format(self.identifier)
        return self._launch_identifier

    @property
    def launch_identifier_with_id(self):
        if self._launch_identifier_with_id is None:
            self._launch_identifier_with_id = "{}.{}".format(
                self.identifier, self.process_identifier()
            )
        return self._launch_identifier_with_id

    def construct_requirements_validations(self):
        # Override validation as this action does not need them
        return

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
            self.launch_identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            launch_subscription,
            self._launch
        )

    def _discover(self, event):
        entities = self._translate_event(event)
        items = self.discover(self.session, entities, event)
        if items:
            return {"items": items}

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
                project_name = ft_project["full_name"]
                if not self.dbcon.is_installed():
                    self.dbcon.install()
                self.dbcon.Session["AVALON_PROJECT"] = project_name
                avalon_project_doc = self.dbcon.find_one({
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

        items = []
        for app_name in avalon_project_apps:
            app = self.application_manager.applications.get(app_name)
            if not app or not app.enabled:
                continue

            if app.group.name in CUSTOM_LAUNCH_APP_GROUPS:
                continue

            app_icon = app.icon
            if app_icon and self.icon_url:
                try:
                    app_icon = app_icon.format(self.icon_url)
                except Exception:
                    self.log.warning((
                        "Couldn't fill icon path. Icon template: \"{}\""
                        " --- Icon url: \"{}\""
                    ).format(app_icon, self.icon_url))
                    app_icon = None

            items.append({
                "label": app.group.label,
                "variant": app.label,
                "description": None,
                "actionIdentifier": "{}.{}".format(
                    self.launch_identifier_with_id, app_name
                ),
                "icon": app_icon
            })

        return items

    def _launch(self, event):
        event_identifier = event["data"]["actionIdentifier"]
        # Check if identifier is same
        # - show message that acion may not be triggered on this machine
        if event_identifier.startswith(self.launch_identifier_with_id):
            return BaseAction._launch(self, event)

        return {
            "success": False,
            "message": (
                "There are running more OpenPype processes"
                " where Application can be launched."
            )
        }

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
        identifier = event["data"]["actionIdentifier"]
        id_identifier_len = len(self.launch_identifier_with_id) + 1
        app_name = identifier[id_identifier_len:]

        entity = entities[0]

        task_name = entity["name"]
        asset_name = entity["parent"]["name"]
        project_name = entity["project"]["full_name"]
        self.log.info((
            "Ftrack launch app: \"{}\" on Project/Asset/Task: {}/{}/{}"
        ).format(app_name, project_name, asset_name, task_name))
        try:
            self.application_manager.launch(
                app_name,
                project_name=project_name,
                asset_name=asset_name,
                task_name=task_name
            )

        except ApplictionExecutableNotFound as exc:
            self.log.warning(exc.exc_msg)
            return {
                "success": False,
                "message": exc.msg
            }

        except ApplicationLaunchFailed as exc:
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

        return {
            "success": True,
            "message": "Launching {0}".format(self.label)
        }


def register(session):
    """Register action. Called when used as an event plugin."""
    AppplicationsAction(session).register()
