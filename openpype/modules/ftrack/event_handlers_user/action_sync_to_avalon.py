import time
import sys
import json
import traceback

from openpype_modules.ftrack.lib import BaseAction, statics_icon
from openpype_modules.ftrack.lib.avalon_sync import SyncEntitiesFactory


class SyncToAvalonLocal(BaseAction):
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

    identifier = "sync.to.avalon.local"
    label = "OpenPype Admin"
    variant = "- Sync To Avalon (Local)"
    priority = 200
    icon = statics_icon("ftrack", "action_icons", "OpenPypeAdmin.svg")

    settings_key = "sync_to_avalon_local"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entities_factory = SyncEntitiesFactory(self.log, self.session)

    def discover(self, session, entities, event):
        """ Validate selection. """
        is_valid = False
        for ent in event["data"]["selection"]:
            # Ignore entities that are not tasks or projects
            if ent["entityType"].lower() in ["show", "task"]:
                is_valid = True
                break

        if is_valid:
            is_valid = self.valid_roles(session, entities, event)
        return is_valid

    def launch(self, session, in_entities, event):
        self.log.debug("{}: Creating job".format(self.label))

        user_entity = session.query(
            "User where id is {}".format(event["source"]["user"]["id"])
        ).one()
        job_entity = session.create("Job", {
            "user": user_entity,
            "status": "running",
            "data": json.dumps({
                "description": "Sync to avalon is running..."
            })
        })
        session.commit()

        project_entity = self.get_project_from_entity(in_entities[0])
        project_name = project_entity["full_name"]

        try:
            result = self.synchronization(event, project_name)

        except Exception:
            self.log.error(
                "Synchronization failed due to code error", exc_info=True
            )

            description = "Sync to avalon Crashed (Download traceback)"
            self.add_traceback_to_job(
                job_entity, session, sys.exc_info(), description
            )

            msg = "An error has happened during synchronization"
            title = "Synchronization report ({}):".format(project_name)
            items = []
            items.append({
                "type": "label",
                "value": "# {}".format(msg)
            })
            items.append({
                "type": "label",
                "value": (
                    "<p>Download report from job for more information.</p>"
                )
            })

            report = {}
            try:
                report = self.entities_factory.report()
            except Exception:
                pass

            _items = report.get("items") or []
            if _items:
                items.append(self.entities_factory.report_splitter)
                items.extend(_items)

            self.show_interface(items, title, event, submit_btn_label="Ok")

            return {"success": True, "message": msg}

        job_entity["status"] = "done"
        job_entity["data"] = json.dumps({
            "description": "Sync to avalon finished."
        })
        session.commit()

        return result

    def synchronization(self, event, project_name):
        time_start = time.time()

        self.show_message(event, "Synchronization - Preparing data", True)

        try:
            output = self.entities_factory.launch_setup(project_name)
            if output is not None:
                return output

            time_1 = time.time()

            self.entities_factory.set_cutom_attributes()
            time_2 = time.time()

            # This must happen before all filtering!!!
            self.entities_factory.prepare_avalon_entities(project_name)
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
                    project_name
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

        finally:
            try:
                self.entities_factory.dbcon.uninstall()
            except Exception:
                pass

            try:
                self.entities_factory.session.close()
            except Exception:
                pass


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    SyncToAvalonLocal(session).register()
