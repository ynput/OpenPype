import os
import time
import traceback

from pype.modules.ftrack import BaseAction
from pype.modules.ftrack.lib.avalon_sync import SyncEntitiesFactory
from pype.api import config


class SyncToAvalonServer(BaseAction):
    """
    Synchronizing data action - from Ftrack to Avalon DB

    Stores all information about entity.
    - Name(string) - Most important information = identifier of entity
    - Parent(ObjectId) - Avalon Project Id, if entity is not project itself
    - Data(dictionary):
        - VisualParent(ObjectId) - Avalon Id of parent asset
        - Parents(array of string) - All parent names except project
        - Tasks(array of string) - Tasks on asset
        - FtrackId(string)
        - entityType(string) - entity's type on Ftrack
        * All Custom attributes in group 'Avalon'
            - custom attributes that start with 'avalon_' are skipped

    * These information are stored for entities in whole project.

    Avalon ID of asset is stored to Ftrack
        - Custom attribute 'avalon_mongo_id'.
    - action IS NOT creating this Custom attribute if doesn't exist
        - run 'Create Custom Attributes' action
        - or do it manually (Not recommended)
    """
    #: Action identifier.
    identifier = "sync.to.avalon.server"
    #: Action label.
    label = "Pype Admin"
    variant = "- Sync To Avalon (Server)"
    #: Action description.
    description = "Send data from Ftrack to Avalon"
    #: Action icon.
    icon = "{}/ftrack/action_icons/PypeAdmin.svg".format(
        os.environ.get(
            "PYPE_STATICS_SERVER",
            "http://localhost:{}".format(
                config.get_presets().get("services", {}).get(
                    "rest_api", {}
                ).get("default_port", 8021)
            )
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entities_factory = SyncEntitiesFactory(self.log, self.session)

    def register(self):
        self.session.event_hub.subscribe(
            "topic=ftrack.action.discover",
            self._discover,
            priority=self.priority
        )

        launch_subscription = (
            "topic=ftrack.action.launch and data.actionIdentifier={0}"
        ).format(self.identifier)
        self.session.event_hub.subscribe(launch_subscription, self._launch)

    def discover(self, session, entities, event):
        """ Validation """
        # Check if selection is valid
        valid_selection = False
        for ent in event["data"]["selection"]:
            # Ignore entities that are not tasks or projects
            if ent["entityType"].lower() in ["show", "task"]:
                valid_selection = True
                break

        if not valid_selection:
            return False

        # Get user and check his roles
        user_id = event.get("source", {}).get("user", {}).get("id")
        if not user_id:
            return False

        user = session.query("User where id is \"{}\"".format(user_id)).first()
        if not user:
            return False

        role_list = ["Pypeclub", "Administrator", "Project Manager"]
        for role in user["user_security_roles"]:
            if role["security_role"]["name"] in role_list:
                return True
        return False

    def launch(self, session, in_entities, event):
        time_start = time.time()

        self.show_message(event, "Synchronization - Preparing data", True)
        # Get ftrack project
        if in_entities[0].entity_type.lower() == "project":
            ft_project_name = in_entities[0]["full_name"]
        else:
            ft_project_name = in_entities[0]["project"]["full_name"]

        try:
            output = self.entities_factory.launch_setup(ft_project_name)
            if output is not None:
                return output

            time_1 = time.time()

            self.entities_factory.set_cutom_attributes()
            time_2 = time.time()

            # This must happen before all filtering!!!
            self.entities_factory.prepare_avalon_entities(ft_project_name)
            time_3 = time.time()

            self.entities_factory.filter_by_ignore_sync()
            time_4 = time.time()

            self.entities_factory.duplicity_regex_check()
            time_5 = time.time()

            self.entities_factory.prepare_ftrack_ent_data()
            time_6 = time.time()

            self.entities_factory.synchronize()
            time_7 = time.time()

            self.log.debug(
                "*** Synchronization finished ***"
            )
            self.log.debug(
                "preparation <{}>".format(time_1 - time_start)
            )
            self.log.debug(
                "set_cutom_attributes <{}>".format(time_2 - time_1)
            )
            self.log.debug(
                "prepare_avalon_entities <{}>".format(time_3 - time_2)
            )
            self.log.debug(
                "filter_by_ignore_sync <{}>".format(time_4 - time_3)
            )
            self.log.debug(
                "duplicity_regex_check <{}>".format(time_5 - time_4)
            )
            self.log.debug(
                "prepare_ftrack_ent_data <{}>".format(time_6 - time_5)
            )
            self.log.debug(
                "synchronize <{}>".format(time_7 - time_6)
            )
            self.log.debug(
                "* Total time: {}".format(time_7 - time_start)
            )

            report = self.entities_factory.report()
            if report and report.get("items"):
                default_title = "Synchronization report ({}):".format(
                    ft_project_name
                )
                self.show_interface(
                    items=report["items"],
                    title=report.get("title", default_title),
                    event=event
                )
            return {
                "success": True,
                "message": "Synchronization Finished"
            }

        except Exception:
            self.log.error(
                "Synchronization failed due to code error", exc_info=True
            )
            msg = "An error has happened during synchronization"
            title = "Synchronization report ({}):".format(ft_project_name)
            items = []
            items.append({
                "type": "label",
                "value": "# {}".format(msg)
            })
            items.append({
                "type": "label",
                "value": "## Traceback of the error"
            })
            items.append({
                "type": "label",
                "value": "<p>{}</p>".format(
                    str(traceback.format_exc()).replace(
                        "\n", "<br>").replace(
                        " ", "&nbsp;"
                    )
                )
            })

            report = {"items": []}
            try:
                report = self.entities_factory.report()
            except Exception:
                pass

            _items = report.get("items", [])
            if _items:
                items.append(self.entities_factory.report_splitter)
                items.extend(_items)

            self.show_interface(items, title, event)

            return {"success": True, "message": msg}

        finally:
            try:
                self.entities_factory.dbcon.uninstall()
            except Exception:
                pass

            try:
                self.entities_factory.session.close()
            except Exception:
                pass


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''
    SyncToAvalonServer(session, plugins_presets).register()
