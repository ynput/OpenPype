import collections
from openpype_modules.ftrack.lib import BaseEvent


class TaskToVersionStatus(BaseEvent):
    """Changes status of task's latest AssetVersions on its status change."""

    settings_key = "status_task_to_version"

    # Attribute for caching session user id
    _cached_user_id = None

    def is_event_invalid(self, session, event):
        """Skip task status changes for session user changes.

        It is expected that there may be another event handler that set
        version status to task in that case skip all events caused by same
        user as session has to avoid infinite loop of status changes.
        """
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
        """Filter if event contain relevant data.

        Event cares only about changes of `statusid` on `entity_type` "Task".
        """

        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        filtered_entity_info = collections.defaultdict(list)
        for entity_info in entities_info:
            # Care only about tasks
            if entity_info.get("entity_type") != "Task":
                continue

            # Care only about changes of status
            changes = entity_info.get("changes") or {}
            statusid_changes = changes.get("statusid") or {}
            if (
                statusid_changes.get("new") is None
                or statusid_changes.get("old") is None
            ):
                continue

            # Get project id from entity info
            project_id = None
            for parent_item in reversed(entity_info["parents"]):
                if parent_item["entityType"] == "show":
                    project_id = parent_item["entityId"]
                    break

            if project_id:
                filtered_entity_info[project_id].append(entity_info)

        return filtered_entity_info

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

        for project_id, entities_info in filtered_entity_infos.items():
            self.process_by_project(session, event, project_id, entities_info)

    def process_by_project(self, session, event, project_id, entities_info):
        if not entities_info:
            return

        project_name = self.get_project_name_from_event(
            session, event, project_id
        )
        # Load settings
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )

        event_settings = (
            project_settings["ftrack"]["events"][self.settings_key]
        )
        _status_mapping = event_settings["mapping"]
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}.".format(
                project_name, self.__class__.__name__
            ))
            return

        if not _status_mapping:
            self.log.debug((
                "Project \"{}\" does not have set status mapping for {}."
            ).format(project_name, self.__class__.__name__))
            return

        status_mapping = {
            key.lower(): value
            for key, value in _status_mapping.items()
        }

        asset_types_filter = event_settings["asset_types_filter"]

        task_ids = [
            entity_info["entityId"]
            for entity_info in entities_info
        ]

        last_asset_versions_by_task_id = (
            self.find_last_asset_versions_for_task_ids(
                session, task_ids, asset_types_filter
            )
        )

        # Query Task entities for last asset versions
        joined_filtered_ids = self.join_query_keys(
            last_asset_versions_by_task_id.keys()
        )
        if not joined_filtered_ids:
            return

        task_entities = session.query(
            "select status_id, link from Task where id in ({})".format(
                joined_filtered_ids
            )
        ).all()
        if not task_entities:
            return

        status_ids = set()
        for task_entity in task_entities:
            status_ids.add(task_entity["status_id"])

        task_status_entities = session.query(
            "select id, name from Status where id in ({})".format(
                self.join_query_keys(status_ids)
            )
        ).all()
        task_status_name_by_id = {
            status_entity["id"]: status_entity["name"]
            for status_entity in task_status_entities
        }

        # Final process of changing statuses
        project_entity = session.get("Project", project_id)
        av_statuses_by_low_name, av_statuses_by_id = (
            self.get_asset_version_statuses(project_entity)
        )

        asset_ids = set()
        for asset_versions in last_asset_versions_by_task_id.values():
            for asset_version in asset_versions:
                asset_ids.add(asset_version["asset_id"])

        asset_entities = session.query(
            "select name from Asset where id in ({})".format(
                self.join_query_keys(asset_ids)
            )
        ).all()
        asset_names_by_id = {
            asset_entity["id"]: asset_entity["name"]
            for asset_entity in asset_entities
        }
        for task_entity in task_entities:
            task_id = task_entity["id"]
            status_id = task_entity["status_id"]
            task_path = self._get_ent_path(task_entity)

            task_status_name = task_status_name_by_id[status_id]
            task_status_name_low = task_status_name.lower()

            new_asset_version_status = None
            mapped_status_names = status_mapping.get(task_status_name_low)
            if mapped_status_names:
                for status_name in mapped_status_names:
                    _status = av_statuses_by_low_name.get(status_name.lower())
                    if _status:
                        new_asset_version_status = _status
                        break

            if not new_asset_version_status:
                new_asset_version_status = av_statuses_by_low_name.get(
                    task_status_name_low
                )
            # Skip if tasks status is not available to AssetVersion
            if not new_asset_version_status:
                self.log.debug((
                    "AssetVersion does not have matching status to \"{}\""
                ).format(task_status_name))
                continue

            last_asset_versions = last_asset_versions_by_task_id[task_id]
            for asset_version in last_asset_versions:
                version = asset_version["version"]
                self.log.debug((
                    "Trying to change status of last AssetVersion {}"
                    " for task \"{}\""
                ).format(version, task_path))

                asset_id = asset_version["asset_id"]
                asset_type_name = asset_names_by_id[asset_id]
                av_ent_path = task_path + " Asset {} AssetVersion {}".format(
                    asset_type_name,
                    version
                )

                # Skip if current AssetVersion's status is same
                status_id = asset_version["status_id"]
                current_status_name = av_statuses_by_id[status_id]["name"]
                if current_status_name.lower() == task_status_name_low:
                    self.log.debug((
                        "AssetVersion already has set status \"{}\". \"{}\""
                    ).format(current_status_name, av_ent_path))
                    continue

                new_status_id = new_asset_version_status["id"]
                new_status_name = new_asset_version_status["name"]
                # Skip if status is already same
                if asset_version["status_id"] == new_status_id:
                    continue

                # Change the status
                try:
                    asset_version["status_id"] = new_status_id
                    session.commit()
                    self.log.info("[ {} ] Status updated to [ {} ]".format(
                        av_ent_path, new_status_name
                    ))
                except Exception:
                    session.rollback()
                    self.log.warning(
                        "[ {} ]Status couldn't be set to \"{}\"".format(
                            av_ent_path, new_status_name
                        ),
                        exc_info=True
                    )

    def get_asset_version_statuses(self, project_entity):
        """Status entities for AssetVersion from project's schema.

        Load statuses from project's schema and store them by id and name.

        Args:
            project_entity (ftrack_api.Entity): Entity of ftrack's project.

        Returns:
            tuple: 2 items are returned first are statuses by name
                second are statuses by id.
        """
        project_schema = project_entity["project_schema"]
        # Get all available statuses for Task
        statuses = project_schema.get_statuses("AssetVersion")
        # map lowered status name with it's object
        av_statuses_by_low_name = {}
        av_statuses_by_id = {}
        for status in statuses:
            av_statuses_by_low_name[status["name"].lower()] = status
            av_statuses_by_id[status["id"]] = status

        return av_statuses_by_low_name, av_statuses_by_id

    def find_last_asset_versions_for_task_ids(
        self, session, task_ids, asset_types_filter
    ):
        """Find latest AssetVersion entities for task.

        Find first latest AssetVersion for task and all AssetVersions with
        same version for the task.

        Args:
            asset_versions (list): AssetVersion entities sorted by "version".
            task_ids (list): Task ids.
            asset_types_filter (list): Asset types short names that will be
                used to filter AssetVersions. Filtering is skipped if entered
                value is empty list.
        """

        # Allow event only on specific asset type names
        asset_query_part = ""
        if asset_types_filter:
            # Query all AssetTypes
            asset_types = session.query(
                "select id, short from AssetType"
            ).all()
            # Store AssetTypes by id
            asset_type_short_by_id = {
                asset_type["id"]: asset_type["short"]
                for asset_type in asset_types
            }

            # Lower asset types from settings
            # WARNING: not sure if is good idea to lower names as Ftrack may
            #   contain asset type with name "Scene" and "scene"!
            asset_types_filter_low = set(
                asset_types_name.lower()
                for asset_types_name in asset_types_filter
            )
            asset_type_ids = []
            for type_id, short in asset_type_short_by_id.items():
                # TODO log if asset type name is not found
                if short.lower() in asset_types_filter_low:
                    asset_type_ids.append(type_id)

            # TODO log that none of asset type names were found in ftrack
            if asset_type_ids:
                asset_query_part = " and asset.type_id in ({})".format(
                    self.join_query_keys(asset_type_ids)
                )

        # Query tasks' AssetVersions
        asset_versions = session.query((
            "select status_id, version, task_id, asset_id"
            " from AssetVersion where task_id in ({}){}"
            " order by version descending"
        ).format(self.join_query_keys(task_ids), asset_query_part)).all()

        last_asset_versions_by_task_id = collections.defaultdict(list)
        last_version_by_task_id = {}
        not_finished_task_ids = set(task_ids)
        for asset_version in asset_versions:
            task_id = asset_version["task_id"]
            # Check if task id is still in `not_finished_task_ids`
            if task_id not in not_finished_task_ids:
                continue

            version = asset_version["version"]

            # Find last version in `last_version_by_task_id`
            last_version = last_version_by_task_id.get(task_id)
            if last_version is None:
                # If task id does not have version set yet then it's first
                # AssetVersion for this task
                last_version_by_task_id[task_id] = version

            elif last_version > version:
                # Skip processing if version is lower than last version
                # and pop task id from `not_finished_task_ids`
                not_finished_task_ids.remove(task_id)
                continue

            # Add AssetVersion entity to output dictionary
            last_asset_versions_by_task_id[task_id].append(asset_version)

        return last_asset_versions_by_task_id


def register(session):
    TaskToVersionStatus(session).register()
