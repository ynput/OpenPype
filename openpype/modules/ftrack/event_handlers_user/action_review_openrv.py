import os
import traceback
import json
from collections import defaultdict

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_version_by_name,
    get_representation_by_name, get_project
)
from openpype.lib import ApplicationManager
from openpype.pipeline import AvalonMongoDB

from openpype_modules.ftrack.lib import BaseAction, statics_icon


class RVActionReview(BaseAction):
    """ Launch RV action """
    identifier = "openrv.review.action"
    label = "Review with RV"
    description = "OpenRV Launcher"
    icon = statics_icon("ftrack", "action_icons", "RV.png")

    type = "Application"

    allowed_types = ["img", "mov", "exr", "mp4", "jpg", "png"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rv_path = None
        self.rv_app = "openrv/1-0"
        self.application_manager = ApplicationManager()

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        data = event['data']
        selection = data.get('selection', [])
        print(selection[0]["entityType"])
        if selection[0]["entityType"] == "list":
            return {
                'items': [{
                    'label': self.label,
                    'description': self.description,
                    'actionIdentifier': self.identifier
                }]
            }

    def preregister(self):
        return True

    def get_components_from_list_entity(self, entity):
        """Get components from list entity types.

        The components dictionary is modifid in place, so nothing is returned.

            Args:
                entity (Ftrack entity)
                components (dict)
        """
        items_components = []
        if entity.entity_type.lower() == "assetversionlist":

            for item in entity["items"]:
                print("item in assetversionlist", item)
                components = dict()

                if item.entity_type.lower() == "assetversion":
                    for component in item["components"]:
                        if component["file_type"][
                           1:] not in self.allowed_types:
                            continue
                        try:
                            components[item["asset"]["parent"]["name"]].append(
                                component)
                        except KeyError:
                            components[item["asset"]["parent"]["name"]] = [
                                component]

                    items_components.append(components)

        return items_components

    def interface(self, session, entities, event):
        if event['data'].get('values', {}):
            return

        user = session.query(
            "User where username is '{0}'".format(
                os.environ["FTRACK_API_USER"]
            )
        ).one()
        job = session.create(
            "Job",
            {
                "user": user,
                "status": "running",
                "data": json.dumps({
                    "description": "RV: Collecting components."
                })
            }
        )
        # Commit to feedback to user.
        session.commit()
        items = []

        try:
            items = self.get_interface_items(session, entities)
        except Exception:
            self.log.error(traceback.format_exc())
            job["status"] = "failed"
        else:
            job["status"] = "done"

        job["status"] = "done"

        # Commit to end job.
        session.commit()

        return {"items": items}

    def get_interface_items(self, session, entities):

        all_item_for_ui = []
        for entity in entities:
            print("ENTITY", entity)

            item_components = self.get_components_from_list_entity(entity)
            for components in item_components:
                print("Working on", components)
                # Sort by version
                for parent_name, entities in components.items():
                    version_mapping = defaultdict(list)
                    for entity in entities:
                        entity_version = entity["version"]["version"]
                        version_mapping[entity_version].append(entity)

                    # Sort same versions by date.
                    for version, entities in version_mapping.items():
                        version_mapping[version] = sorted(
                            entities,
                            key=lambda x: x["version"]["date"],
                            reverse=True
                        )

                    components[parent_name] = []
                    for version in reversed(sorted(version_mapping.keys())):
                        components[parent_name].extend(
                            version_mapping[version]
                        )

                # Items to present to user.
                label = "{} - v{} - {}"
                loadables = ["exr"]
                for parent_name, entities in components.items():
                    data = []
                    for entity in entities:
                        entity_filetype = entity["file_type"][1:]
                        if entity_filetype in loadables:
                            data.append(
                                {
                                    "label": label.format(
                                        entity["version"]["asset"]["name"],
                                        str(entity["version"]["version"]).zfill(3),  # noqa
                                        entity["file_type"][1:]
                                    ),
                                    "value": entity["id"]
                                }
                            )

                    all_item_for_ui.append(
                        {
                            "label": parent_name,
                            "type": "enumerator",
                            "name": parent_name,
                            "data": data,
                            "value": data[0]["value"]
                        }
                    )
        return all_item_for_ui

    def launch(self, session, entities, event):
        """Callback method for RV action."""
        # Launching application
        if "values" not in event["data"]:
            return

        user = session.query(
            "User where username is '{0}'".format(
                os.environ["FTRACK_API_USER"]
            )
        ).one()
        job = session.create(
            "Job",
            {
                "user": user,
                "status": "running",
                "data": json.dumps({
                    "description": "RV: Collecting file paths."
                })
            }
        )
        # Commit to feedback to user.
        session.commit()

        component_representation = []

        try:
            component_representation = self.get_representations(
                session, event, entities
            )
        except Exception:
            self.log.error(traceback.format_exc())
            job["status"] = "failed"
        else:
            job["status"] = "done"

        # Commit to end job.
        session.commit()

        # launch app here
        avalon_project_apps = event["data"].get("avalon_project_apps", None)
        avalon_project_doc = event["data"].get("avalon_project_doc", None)

        if avalon_project_apps is None:
            if avalon_project_doc is None:
                ft_project = self.get_project_from_entity(entities[0])
                project_name = ft_project["full_name"]
                avalon_project_doc = get_project(project_name) or False
                event["data"]["avalon_project_doc"] = avalon_project_doc

            if not avalon_project_doc:
                return False

            project_apps_config = avalon_project_doc["config"].get("apps", [])
            avalon_project_apps = (
                [app["name"] for app in project_apps_config] or False
            )
            event["data"]["avalon_project_apps"] = avalon_project_apps

        # set app
        for a in avalon_project_apps:
            if "openrv" in a:
                self.rv_app = a

        # checks for what are we loading
        task_name = "prepDaily"
        asset_name = "DaliesPrep"

        self.application_manager.launch(
            self.rv_app,
            project_name=project_name,
            asset_name=asset_name,
            task_name=task_name,
            extra=component_representation
        )
        return True

    def get_representations(self, session, event, entities):
        """Get representations from selected components."""

        ft_project = self.get_project_from_entity(entities[0])
        project_name = ft_project["full_name"]

        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name

        representations = []

        for parent_name in sorted(event["data"]["values"].keys()):
            componenet_check = event["data"]["values"][parent_name]
            if type(componenet_check) is list:
                component_data = event["data"]["values"][parent_name][0]
            else:
                component_data = event["data"]["values"][parent_name]

            component = session.get("Component", component_data)
            subset_name = component["version"]["asset"]["name"]
            version_name = component["version"]["version"]
            representation_name = component["file_type"][1:]

            asset_doc = get_asset_by_name(
                project_name, parent_name, fields=["_id"]
            )
            subset_doc = get_subset_by_name(
                project_name,
                subset_name=subset_name,
                asset_id=asset_doc["_id"]
            )
            version_doc = get_version_by_name(
                project_name,
                version=version_name,
                subset_id=subset_doc["_id"]
            )
            repre_doc = get_representation_by_name(
                project_name,
                version_id=version_doc["_id"],
                representation_name=representation_name
            )
            if not repre_doc:
                repre_doc = get_representation_by_name(
                    project_name,
                    version_id=version_doc["_id"],
                    representation_name="preview"
                )
            representations.append(str(repre_doc["_id"]))

        return representations


def register(session):
    """Register hooks."""
    RVActionReview(session).register()
