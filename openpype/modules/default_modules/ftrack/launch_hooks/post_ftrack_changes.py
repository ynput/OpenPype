import os

import ftrack_api
from openpype.api import get_project_settings
from openpype.lib import PostLaunchHook


class PostFtrackHook(PostLaunchHook):
    order = None

    def execute(self):
        project_name = self.data.get("project_name")
        asset_name = self.data.get("asset_name")
        task_name = self.data.get("task_name")

        missing_context_keys = set()
        if not project_name:
            missing_context_keys.add("project_name")
        if not asset_name:
            missing_context_keys.add("asset_name")
        if not task_name:
            missing_context_keys.add("task_name")

        if missing_context_keys:
            missing_keys_str = ", ".join([
                "\"{}\"".format(key) for key in missing_context_keys
            ])
            self.log.debug("Hook {} skipped. Missing data keys: {}".format(
                self.__class__.__name__, missing_keys_str
            ))
            return

        required_keys = ("FTRACK_SERVER", "FTRACK_API_USER", "FTRACK_API_KEY")
        for key in required_keys:
            if not os.environ.get(key):
                self.log.debug((
                    "Missing required environment \"{}\""
                    " for Ftrack after launch procedure."
                ).format(key))
                return

        try:
            session = ftrack_api.Session(auto_connect_event_hub=True)
            self.log.debug("Ftrack session created")
        except Exception:
            self.log.warning("Couldn't create Ftrack session")
            return

        try:
            entity = self.find_ftrack_task_entity(
                session, project_name, asset_name, task_name
            )
            if entity:
                self.ftrack_status_change(session, entity, project_name)

        except Exception:
            self.log.warning(
                "Couldn't finish Ftrack procedure.", exc_info=True
            )
            return

        finally:
            session.close()

    def find_ftrack_task_entity(
        self, session, project_name, asset_name, task_name
    ):
        project_entity = session.query(
            "Project where full_name is \"{}\"".format(project_name)
        ).first()
        if not project_entity:
            self.log.warning(
                "Couldn't find project \"{}\" in Ftrack.".format(project_name)
            )
            return

        potential_task_entities = session.query((
            "TypedContext where parent.name is \"{}\" and project_id is \"{}\""
        ).format(asset_name, project_entity["id"])).all()
        filtered_entities = []
        for _entity in potential_task_entities:
            if (
                _entity.entity_type.lower() == "task"
                and _entity["name"] == task_name
            ):
                filtered_entities.append(_entity)

        if not filtered_entities:
            self.log.warning((
                "Couldn't find task \"{}\" under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        if len(filtered_entities) > 1:
            self.log.warning((
                "Found more than one task \"{}\""
                " under parent \"{}\" in Ftrack."
            ).format(task_name, asset_name))
            return

        return filtered_entities[0]

    def ftrack_status_change(self, session, entity, project_name):
        project_settings = get_project_settings(project_name)
        status_update = project_settings["ftrack"]["events"]["status_update"]
        if not status_update["enabled"]:
            self.log.debug(
                "Status changes are disabled for project \"{}\"".format(
                    project_name
                )
            )
            return

        status_mapping = status_update["mapping"]
        if not status_mapping:
            self.log.warning(
                "Project \"{}\" does not have set status changes.".format(
                    project_name
                )
            )
            return

        actual_status = entity["status"]["name"].lower()
        already_tested = set()
        ent_path = "/".join(
            [ent["name"] for ent in entity["link"]]
        )
        while True:
            next_status_name = None
            for key, value in status_mapping.items():
                if key in already_tested:
                    continue
                if actual_status in value or "__any__" in value:
                    if key != "__ignore__":
                        next_status_name = key
                        already_tested.add(key)
                    break
                already_tested.add(key)

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
