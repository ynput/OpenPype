import os
import subprocess
import traceback
import json

from pype.api import config
from pype.modules.ftrack.lib import BaseAction, statics_icon
import ftrack_api
from avalon import io, api


class RVAction(BaseAction):
    """ Launch RV action """
    ignore_me = "rv" not in config.get_presets()
    identifier = "rv.launch.action"
    label = "rv"
    description = "rv Launcher"
    icon = statics_icon("ftrack", "action_icons", "RV.png")

    type = 'Application'

    def __init__(self, session, plugins_presets):
        """ Constructor

            :param session: ftrack Session
            :type session: :class:`ftrack_api.Session`
        """
        super().__init__(session, plugins_presets)
        self.rv_path = None
        self.config_data = None

        # RV_HOME should be set if properly installed
        if os.environ.get('RV_HOME'):
            self.rv_path = os.path.join(
                os.environ.get('RV_HOME'),
                'bin',
                'rv'
            )
        else:
            # if not, fallback to config file location
            if "rv" in config.get_presets():
                self.config_data = config.get_presets()['rv']['config']
                self.set_rv_path()

        if self.rv_path is None:
            return

        self.allowed_types = self.config_data.get(
            'file_ext', ["img", "mov", "exr"]
        )

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        return True

    def set_rv_path(self):
        self.rv_path = self.config_data.get("rv_path")

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

        self.log.info("Running rv: {}".format(args))

        subprocess.Popen(args)

        return True

    def get_file_paths(self, session, event):
        """Get file paths from selected components."""

        link = session.get(
            "Component", list(event["data"]["values"].values())[0]
        )["version"]["asset"]["parent"]["link"][0]
        project = session.get(link["type"], link["id"])
        os.environ["AVALON_PROJECT"] = project["name"]
        api.Session["AVALON_PROJECT"] = project["name"]
        io.install()

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

            asset = io.find_one({"type": "asset", "name": parent_name})
            subset = io.find_one(
                {
                    "type": "subset",
                    "name": component["version"]["asset"]["name"],
                    "parent": asset["_id"]
                }
            )
            version = io.find_one(
                {
                    "type": "version",
                    "name": component["version"]["version"],
                    "parent": subset["_id"]
                }
            )
            representation = io.find_one(
                {
                    "type": "representation",
                    "parent": version["_id"],
                    "name": component["file_type"][1:]
                }
            )
            if representation is None:
                representation = io.find_one(
                    {
                        "type": "representation",
                        "parent": version["_id"],
                        "name": "preview"
                    }
                )
            paths.append(api.get_representation_path(representation))

        return paths


def register(session, plugins_presets={}):
    """Register hooks."""

    RVAction(session, plugins_presets).register()
