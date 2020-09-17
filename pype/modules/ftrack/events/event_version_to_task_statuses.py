from pype.modules.ftrack import BaseEvent
from pype.api import config


class VersionToTaskStatus(BaseEvent):

    # Presets usage
    default_status_mapping = {}

    def launch(self, session, event):
        '''Propagates status from version to task when changed'''

        # start of event procedure ----------------------------------
        for entity in event['data'].get('entities', []):
            # Filter AssetVersions
            if entity["entityType"] != "assetversion":
                continue

            # Skip if statusid not in keys (in changes)
            keys = entity.get("keys")
            if not keys or "statusid" not in keys:
                continue

            # Get new version task name
            version_status_id = (
                entity
                .get("changes", {})
                .get("statusid", {})
                .get("new", {})
            )

            # Just check that `new` is set to any value
            if not version_status_id:
                continue

            try:
                version_status = session.get("Status", version_status_id)
            except Exception:
                self.log.warning(
                    "Troubles with query status id [ {} ]".format(
                        version_status_id
                    ),
                    exc_info=True
                )

            if not version_status:
                continue

            version_status_orig = version_status["name"]

            # Load status mapping from presets
            status_mapping = (
                config.get_presets()
                .get("ftrack", {})
                .get("ftrack_config", {})
                .get("status_version_to_task")
            ) or self.default_status_mapping

            # Skip if mapping is empty
            if not status_mapping:
                continue

            # Lower version status name and check if has mapping
            version_status = version_status_orig.lower()
            new_status_names = []
            mapped = status_mapping.get(version_status)
            if mapped:
                new_status_names.extend(list(mapped))

            new_status_names.append(version_status)

            self.log.debug(
                "Processing AssetVersion status change: [ {} ]".format(
                    version_status_orig
                )
            )

            # Lower all names from presets
            new_status_names = [name.lower() for name in new_status_names]

            # Get entities necessary for processing
            version = session.get("AssetVersion", entity["entityId"])
            task = version.get("task")
            if not task:
                continue

            if version["asset"]["type"]["short"].lower() == "scene":
                continue

            project_schema = task["project"]["project_schema"]
            # Get all available statuses for Task
            statuses = project_schema.get_statuses("Task", task["type_id"])
            # map lowered status name with it's object
            stat_names_low = {
                status["name"].lower(): status for status in statuses
            }

            new_status = None
            for status_name in new_status_names:
                if status_name not in stat_names_low:
                    continue

                # store object of found status
                new_status = stat_names_low[status_name]
                self.log.debug("Status to set: [ {} ]".format(
                    new_status["name"]
                ))
                break

            # Skip if status names were not found for paticulat entity
            if not new_status:
                self.log.warning(
                    "Any of statuses from presets can be set: {}".format(
                        str(new_status_names)
                    )
                )
                continue

            # Get full path to task for logging
            ent_path = "/".join([ent["name"] for ent in task["link"]])

            # Setting task status
            try:
                task["status"] = new_status
                session.commit()
                self.log.debug("[ {} ] Status updated to [ {} ]".format(
                    ent_path, new_status['name']
                ))
            except Exception:
                session.rollback()
                self.log.warning(
                    "[ {} ]Status couldn't be set".format(ent_path),
                    exc_info=True
                )


def register(session, plugins_presets):
    '''Register plugin. Called when used as an plugin.'''

    VersionToTaskStatus(session, plugins_presets).register()
