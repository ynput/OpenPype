import os

from pype.modules.ftrack import BaseAction
from pype.modules.ftrack.lib.io_nonsingleton import DbConnector


class PypeUpdateFromV2_2_0(BaseAction):
    """This action is to remove silo field from database and changes asset
    schema to newer version

    WARNING: it is NOT for situations when you want to switch from avalon-core
    to Pype's avalon-core!!!

    """
    #: Action identifier.
    identifier = "silos.doctor"
    #: Action label.
    label = "Pype Update"
    variant = "- v2.2.0 to v2.3.0 or higher"
    #: Action description.
    description = "Use when Pype was updated from v2.2.0 to v2.3.0 or higher"

    #: roles that are allowed to register this action
    role_list = ["Pypeclub", "Administrator"]
    icon = "{}/ftrack/action_icons/PypeUpdate.svg".format(
        os.environ.get("PYPE_STATICS_SERVER", "")
    )
    # connector to MongoDB (Avalon mongo)
    db_con = DbConnector()

    def discover(self, session, entities, event):
        """ Validation """
        if len(entities) != 1:
            return False

        if entities[0].entity_type.lower() != "project":
            return False

        return True

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        items = []
        item_splitter = {'type': 'label', 'value': '---'}
        title = "Updated Pype from v 2.2.0 to v2.3.0 or higher"

        items.append({
            "type": "label",
            "value": (
                "NOTE: This doctor action should be used ONLY when Pype"
                " was updated from v2.2.0 to v2.3.0 or higher.<br><br><br>"
            )
        })

        items.append({
            "type": "label",
            "value": (
                "Select if want to process <b>all synchronized projects</b>"
                " or <b>selection</b>."
            )
        })

        items.append({
            "type": "enumerator",
            "name": "__process_all__",
            "data": [{
                "label": "All synchronized projects",
                "value": True
            }, {
                "label": "Selection",
                "value": False
            }],
            "value": False
        })

        items.append({
            "type": "label",
            "value": (
                "<br/><br/><h2>Synchronized projects:</h2>"
                "<i>(ignore if <strong>\"ALL projects\"</strong> selected)</i>"
            )
        })

        self.log.debug("Getting all Ftrack projects")
        # Get all Ftrack projects
        all_ftrack_projects = [
            project["full_name"] for project in session.query("Project").all()
        ]

        self.log.debug("Getting Avalon projects that are also in the Ftrack")
        # Get Avalon projects that are in Ftrack
        self.db_con.install()
        possible_projects = [
            project["name"] for project in self.db_con.projects()
            if project["name"] in all_ftrack_projects
        ]

        for project in possible_projects:
            item_label = {
                "type": "label",
                "value": project
            }
            item = {
                "label": "- process",
                "name": project,
                "type": 'boolean',
                "value": False
            }
            items.append(item_splitter)
            items.append(item_label)
            items.append(item)

        if len(possible_projects) == 0:
            return {
                "success": False,
                "message": (
                    "Nothing to process."
                    " There are not projects synchronized to avalon."
                )
            }
        else:
            return {
                "items": items,
                "title": title
            }

    def launch(self, session, entities, event):
        if 'values' not in event['data']:
            return

        projects_selection = {
            True: [],
            False: []
        }
        process_all = None

        values = event['data']['values']
        for key, value in values.items():
            if key == "__process_all__":
                process_all = value
                continue

            projects_selection[value].append(key)

        # Skip if process_all value is not boolean
        # - may happen when user delete string line in combobox
        if not isinstance(process_all, bool):
            self.log.warning(
                "Nothing was processed. User didn't select if want to process"
                " selection or all projects!"
            )
            return {
                "success": False,
                "message": (
                    "Nothing was processed. You must select if want to process"
                    " \"selection\" or \"all projects\"!"
                )
            }

        projects_to_process = projects_selection[True]
        if process_all:
            projects_to_process.extend(projects_selection[False])

        self.db_con.install()
        for project in projects_to_process:
            self.log.debug("Processing project \"{}\"".format(project))
            self.db_con.Session["AVALON_PROJECT"] = project

            self.log.debug("- Unsetting silos on assets")
            self.db_con.update_many(
                {"type": "asset"},
                {"$unset": {"silo": ""}}
            )

            self.log.debug("- setting schema of assets to v.3")
            self.db_con.update_many(
                {"type": "asset"},
                {"$set": {"schema": "avalon-core:asset-3.0"}}
            )

        return True


def register(session, plugins_presets={}):
    """Register plugin. Called when used as an plugin."""

    PypeUpdateFromV2_2_0(session, plugins_presets).register()
