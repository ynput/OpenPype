import getpass
import os
import subprocess
import sys
import traceback
import json

import ftrack_api

from openpype.client import (
    get_asset_by_name,
    get_subset_by_name,
    get_version_by_name,
    get_representation_by_name
)
from openpype.pipeline import (
    get_representation_path,
    AvalonMongoDB,
    Anatomy,
)
from openpype_modules.ftrack.lib import BaseAction, statics_icon


class RVActionView(BaseAction):
    """ Launch RV action """
    identifier = "openrv.launch.action"
    label = "Open with RV"
    description = "rv Launcher"
    icon = statics_icon("ftrack", "action_icons", "RV.png")

    type = 'Application'

    allowed_types = ["img", "mov", "exr", "mp4"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # QUESTION load RV application data from AppplicationManager?
        rv_path = None

        rv_path = "PATH_TO_BIN/bin/rv.exe"
        self.rv_home = "PATH_TO+RV_HOME"
        os.environ["RV_HOME"] = os.path.normpath(self.rv_home)
        sys.path.append(os.path.join(self.rv_home, "lib"))

        # RV_HOME should be set if properly installed
        # if os.environ.get('RV_HOME'):
        #     rv_path = os.path.join(
        #         os.environ.get('RV_HOME'),
        #         'bin',
        #         'rv'
        #     )
        #     if not os.path.exists(rv_path):
        #         rv_path = None

        if not rv_path:
            self.log.info("RV path was not found.")
            self.ignore_me = True

        self.rv_path = rv_path

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        data = event['data']
        selection = data.get('selection', [])
        print(selection[0]["entityType"])
        if selection[0]["entityType"] != "list":
            return {'items': [{
                'label': self.label,
                'description': self.description,
                'actionIdentifier': self.identifier
            }]
            }

    def preregister(self):
        if self.rv_path is None:
            return (
                'RV is not installed or paths in presets are not set correctly'
            )
        return True

    def get_components_from_entity(self, session, entity, components):
        """Get components from various entity types.

        The components dictionary is modifid in place, so nothing is returned.

            Args:
                entity (Ftrack entity)
                components (dict)
        """

        if entity.entity_type.lower() == "assetversion":
            for component in entity["components"]:
                if component["file_type"][1:] not in self.allowed_types:
                    continue

                try:
                    components[entity["asset"]["parent"]["name"]].append(
                        component
                    )
                except KeyError:
                    components[entity["asset"]["parent"]["name"]] = [component]

            return

        if entity.entity_type.lower() == "task":
            query = "AssetVersion where task_id is '{0}'".format(entity["id"])
            for assetversion in session.query(query):
                self.get_components_from_entity(
                    session, assetversion, components
                )

            return

        if entity.entity_type.lower() == "shot":
            query = "AssetVersion where asset.parent.id is '{0}'".format(
                entity["id"]
            )
            for assetversion in session.query(query):
                self.get_components_from_entity(
                    session, assetversion, components
                )

            return

        raise NotImplementedError(
            "\"{}\" entity type is not implemented yet.".format(
                entity.entity_type
            )
        )

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

        # Commit to end job.
        session.commit()

        return {"items": items}

    def get_interface_items(self, session, entities):

        components = {}
        for entity in entities:
            self.get_components_from_entity(session, entity, components)

        # Sort by version
        for parent_name, entities in components.items():
            version_mapping = {}
            for entity in entities:
                try:
                    version_mapping[entity["version"]["version"]].append(
                        entity
                    )
                except KeyError:
                    version_mapping[entity["version"]["version"]] = [entity]

            # Sort same versions by date.
            for version, entities in version_mapping.items():
                version_mapping[version] = sorted(
                    entities, key=lambda x: x["version"]["date"], reverse=True
                )

            components[parent_name] = []
            for version in reversed(sorted(version_mapping.keys())):
                components[parent_name].extend(version_mapping[version])

        # Items to present to user.
        items = []
        label = "{} - v{} - {}"
        for parent_name, entities in components.items():
            data = []
            for entity in entities:
                data.append(
                    {
                        "label": label.format(
                            entity["version"]["asset"]["name"],
                            str(entity["version"]["version"]).zfill(3),
                            entity["file_type"][1:]
                        ),
                        "value": entity["id"]
                    }
                )

            items.append(
                {
                    "label": parent_name,
                    "type": "enumerator",
                    "name": parent_name,
                    "data": data,
                    "value": data[0]["value"]
                }
            )

        return items

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

        paths = []
        try:
            paths = self.get_file_paths(session, event)
        except Exception:
            self.log.error(traceback.format_exc())
            job["status"] = "failed"
        else:
            job["status"] = "done"

        # Commit to end job.
        session.commit()

        args = [os.path.normpath(self.rv_path)]

        fps = entities[0].get("custom_attributes", {}).get("fps", None)
        if fps is not None:
            args.extend(["-fps", str(fps)])

        args.extend(paths)
        # CORE EDIT SET UP THE PATHS
        self.log.info("setting up env vars")
        os.environ["RV_HOME"] = os.path.normpath(self.rv_home)
        sys.path.append(os.path.join(self.rv_home, "lib"))
        sys.path.append(self.rv_home)
        self.log.info("Running rv: {}".format(args))
        self.home = os.path.normpath(os.path.join("c:/", "Users", getpass.getuser()))
        os.environ["HOME"] = self.home
        env = os.environ.copy()
        env['PYTHONPATH'] = ''
        subprocess.Popen(args, env=env)

        return True

    def get_file_paths(self, session, event):
        """Get file paths from selected components."""

        link = session.get(
            "Component", list(event["data"]["values"].values())[0]
        )["version"]["asset"]["parent"]["link"][0]
        project = session.get(link["type"], link["id"])
        project_name = project["full_name"]
        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = project_name
        anatomy = Anatomy(project_name)

        location = ftrack_api.Session().pick_location()

        paths = []
        for parent_name in sorted(event["data"]["values"].keys()):
            component = session.get(
                "Component", event["data"]["values"][parent_name]
            )

            # Newer publishes have the source referenced in Ftrack.
            online_source = False
            for neighbour_component in component["version"]["components"]:
                if neighbour_component["name"] != "ftrackreview-mp4_src":
                    continue

                paths.append(
                    location.get_filesystem_path(neighbour_component)
                )
                online_source = True

            if online_source:
                continue

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

            paths.append(get_representation_path(
                repre_doc, root=anatomy.roots, dbcon=dbcon
            ))

        return paths


def register(session):
    """Register hooks."""

    RVActionView(session).register()
