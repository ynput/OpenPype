import collections
from pype.modules.ftrack import BaseEvent


class TaskToVersionStatus(BaseEvent):
    """Changes status of task's latest AssetVersions on its status change."""

    # Attribute for caching session user id
    _cached_user_id = None

    # Presets usage
    asset_types_of_focus = []

    def register(self, *args, **kwargs):
        # Skip registration if attribute `asset_types_of_focus` is not set
        modified_asset_types_of_focus = list()
        if self.asset_types_of_focus:
            if isinstance(self.asset_types_of_focus, str):
                self.asset_types_of_focus = [self.asset_types_of_focus]

            for asset_type_name in self.asset_types_of_focus:
                modified_asset_types_of_focus.append(
                    asset_type_name.lower()
                )

        if not modified_asset_types_of_focus:
            raise Exception((
                "Event handler \"{}\" does not"
                " have set presets for attribute \"{}\""
            ).format(self.__class__.__name__, "asset_types_of_focus"))

        self.asset_types_of_focus = modified_asset_types_of_focus
        return super(TaskToVersionStatus, self).register(*args, **kwargs)

    def is_event_invalid(self, session, event):
        # Cache user id of currently running session
        if self._cached_user_id is None:
            session_user_entity = session.query(
                "User where username is \"{}\"".format(session.api_user)
            ).first()
            if not session_user_entity:
                self.log.warning(
                    "Couldn't query Ftrack user with username \"{}\"".format(
                        session.api_user
                    )
                )
                return False
            self._cached_user_id = session_user_entity["id"]

        # Skip processing if current session user was the user who created
        # the event
        user_info = event["source"].get("user") or {}
        user_id = user_info.get("id")

        # Mark as invalid if user is unknown
        if user_id is None:
            return True
        return user_id == self._cached_user_id

    def filter_event_entities(self, event):
        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        filtered_entities = []
        for entity_info in entities_info:
            # Care only about tasks
            if entity_info.get("entityType") != "task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes") or {}
            statusid_changes = changes.get("statusid") or {}
            if (
                statusid_changes.get("new") is None
                or statusid_changes.get("old") is None
            ):
                continue

            filtered_entities.append(entity_info)

        return filtered_entities

    def _get_ent_path(self, entity):
        return "/".join(
            [ent["name"] for ent in entity["link"]]
        )

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''
        if self.is_event_invalid(session, event):
            return

        filtered_entity_infos = self.filter_event_entities(event)
        if not filtered_entity_infos:
            return

        task_ids = [
            entity_info["entityId"]
            for entity_info in filtered_entity_infos
        ]
        joined_ids = ",".join(
            ["\"{}\"".format(entity_id) for entity_id in task_ids]
        )

        # Query tasks' AssetVersions
        asset_versions = session.query((
            "AssetVersion where task_id in ({}) order by version descending"
        ).format(joined_ids)).all()

        last_asset_version_by_task_id = (
            self.last_asset_version_by_task_id(asset_versions, task_ids)
        )
        if not last_asset_version_by_task_id:
            return

        # Query Task entities for last asset versions
        joined_filtered_ids = ",".join([
            "\"{}\"".format(entity_id)
            for entity_id in last_asset_version_by_task_id.keys()
        ])
        task_entities = session.query(
            "Task where id in ({})".format(joined_filtered_ids)
        ).all()
        if not task_entities:
            return

        # Final process of changing statuses
        av_statuses_by_low_name = self.asset_version_statuses(task_entities[0])
        for task_entity in task_entities:
            task_id = task_entity["id"]
            task_path = self._get_ent_path(task_entity)
            task_status_name = task_entity["status"]["name"]
            task_status_name_low = task_status_name.lower()

            last_asset_versions = last_asset_version_by_task_id[task_id]
            for last_asset_version in last_asset_versions:
                self.log.debug((
                    "Trying to change status of last AssetVersion {}"
                    " for task \"{}\""
                ).format(last_asset_version["version"], task_path))

                new_asset_version_status = av_statuses_by_low_name.get(
                    task_status_name_low
                )
                # Skip if tasks status is not available to AssetVersion
                if not new_asset_version_status:
                    self.log.debug((
                        "AssetVersion does not have matching status to \"{}\""
                    ).format(task_status_name))
                    continue

                av_ent_path = task_path + " Asset {} AssetVersion {}".format(
                    last_asset_version["asset"]["name"],
                    last_asset_version["version"]
                )

                # Skip if current AssetVersion's status is same
                current_status_name = last_asset_version["status"]["name"]
                if current_status_name.lower() == task_status_name_low:
                    self.log.debug((
                        "AssetVersion already has set status \"{}\". \"{}\""
                    ).format(current_status_name, av_ent_path))
                    continue

                # Change the status
                try:
                    last_asset_version["status"] = new_asset_version_status
                    session.commit()
                    self.log.info("[ {} ] Status updated to [ {} ]".format(
                        av_ent_path, new_asset_version_status["name"]
                    ))
                except Exception:
                    session.rollback()
                    self.log.warning(
                        "[ {} ]Status couldn't be set to \"{}\"".format(
                            av_ent_path, new_asset_version_status["name"]
                        ),
                        exc_info=True
                    )

    def asset_version_statuses(self, entity):
        project_entity = self.get_project_from_entity(entity)
        project_schema = project_entity["project_schema"]
        # Get all available statuses for Task
        statuses = project_schema.get_statuses("AssetVersion")
        # map lowered status name with it's object
        av_statuses_by_low_name = {
            status["name"].lower(): status for status in statuses
        }
        return av_statuses_by_low_name

    def last_asset_version_by_task_id(self, asset_versions, task_ids):
        last_asset_version_by_task_id = collections.defaultdict(list)
        last_version_by_task_id = {}
        poping_entity_ids = set(task_ids)
        for asset_version in asset_versions:
            asset_type_name_low = (
                asset_version["asset"]["type"]["name"].lower()
            )
            if asset_type_name_low not in self.asset_types_of_focus:
                continue

            task_id = asset_version["task_id"]
            last_version = last_version_by_task_id.get(task_id)
            if last_version is None:
                last_version_by_task_id[task_id] = asset_version["version"]

            elif last_version != asset_version["version"]:
                poping_entity_ids.remove(task_id)

            if not poping_entity_ids:
                break

            if task_id in poping_entity_ids:
                last_asset_version_by_task_id[task_id].append(asset_version)
        return last_asset_version_by_task_id


def register(session, plugins_presets):
    TaskToVersionStatus(session, plugins_presets).register()
