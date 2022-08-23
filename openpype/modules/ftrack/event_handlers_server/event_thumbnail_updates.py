import collections
from openpype_modules.ftrack.lib import BaseEvent


class ThumbnailEvents(BaseEvent):
    settings_key = "thumbnail_updates"

    def launch(self, session, event):
        """Updates thumbnails of entities from new AssetVersion."""
        filtered_entities = self.filter_entities(event)
        if not filtered_entities:
            return

        for project_id, entities_info in filtered_entities.items():
            self.process_project_entities(
                session, event, project_id, entities_info
            )

    def process_project_entities(
        self, session, event, project_id, entities_info
    ):
        project_name = self.get_project_name_from_event(
            session, event, project_id
        )
        # Load settings
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )

        event_settings = (
            project_settings
            ["ftrack"]
            ["events"]
            [self.settings_key]
        )
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" does not have activated {}.".format(
                project_name, self.__class__.__name__
            ))
            return

        self.log.debug("Processing {} on project \"{}\".".format(
            self.__class__.__name__, project_name
        ))

        parent_levels = event_settings["levels"]
        if parent_levels < 1:
            self.log.debug(
                "Project \"{}\" has parent levels set to {}. Skipping".format(
                    project_name, parent_levels
                )
            )
            return

        asset_version_ids = set()
        for entity in entities_info:
            asset_version_ids.add(entity["entityId"])

        # Do not use attribute `asset_version_entities` will be filtered
        # to when `asset_versions_by_id` is filled
        asset_version_entities = session.query((
            "select task_id, thumbnail_id from AssetVersion where id in ({})"
        ).format(self.join_query_keys(asset_version_ids))).all()

        asset_versions_by_id = {}
        for asset_version_entity in asset_version_entities:
            if not asset_version_entity["thumbnail_id"]:
                continue
            entity_id = asset_version_entity["id"]
            asset_versions_by_id[entity_id] = asset_version_entity

        if not asset_versions_by_id:
            self.log.debug("None of asset versions has set thumbnail id.")
            return

        entity_ids_by_asset_version_id = collections.defaultdict(list)
        hierarchy_ids = set()
        for entity_info in entities_info:
            entity_id = entity_info["entityId"]
            if entity_id not in asset_versions_by_id:
                continue

            parent_ids = []
            counter = None
            for parent_info in entity_info["parents"]:
                if counter is not None:
                    if counter >= parent_levels:
                        break
                    parent_ids.append(parent_info["entityId"])
                    counter += 1

                elif parent_info["entityType"] == "asset":
                    counter = 0

            for parent_id in parent_ids:
                hierarchy_ids.add(parent_id)
                entity_ids_by_asset_version_id[entity_id].append(parent_id)

        for asset_version_entity in asset_versions_by_id.values():
            task_id = asset_version_entity["task_id"]
            if task_id:
                hierarchy_ids.add(task_id)
                asset_version_id = asset_version_entity["id"]
                entity_ids_by_asset_version_id[asset_version_id].append(
                    task_id
                )

        entities = session.query((
            "select thumbnail_id, link from TypedContext where id in ({})"
        ).format(self.join_query_keys(hierarchy_ids))).all()
        entities_by_id = {
            entity["id"]: entity
            for entity in entities
        }

        for version_id, version_entity in asset_versions_by_id.items():
            for entity_id in entity_ids_by_asset_version_id[version_id]:
                entity = entities_by_id.get(entity_id)
                if not entity:
                    continue

                entity["thumbnail_id"] = version_entity["thumbnail_id"]
                self.log.info("Updating thumbnail for entity [ {} ]".format(
                    self.get_entity_path(entity)
                ))

            try:
                session.commit()
            except Exception:
                session.rollback()

    def filter_entities(self, event):
        filtered_entities_info = {}
        for entity_info in event["data"].get("entities", []):
            action = entity_info.get("action")
            if not action:
                continue

            if (
                action == "remove"
                or entity_info["entityType"].lower() != "assetversion"
                or "thumbid" not in (entity_info.get("keys") or [])
            ):
                continue

            # Get project id from entity info
            project_id = entity_info["parents"][-1]["entityId"]
            if project_id not in filtered_entities_info:
                filtered_entities_info[project_id] = []
            filtered_entities_info[project_id].append(entity_info)
        return filtered_entities_info


def register(session):
    ThumbnailEvents(session).register()
