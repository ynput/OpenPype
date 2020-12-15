from pype.modules.ftrack import BaseEvent


class ThumbnailEvents(BaseEvent):
    def launch(self, session, event):
        """Updates thumbnails of entities from new AssetVersion."""

        for entity in event["data"].get("entities", []):
            action = entity.get("action")
            if not action:
                continue
            if (
                entity["action"] == "remove"
                or entity["entityType"].lower() != "assetversion"
                or "thumbid" not in (entity.get("keys") or [])
            ):
                continue

            # update created task thumbnail with first parent thumbnail
            version = session.get("AssetVersion", entity["entityId"])
            if not version:
                continue

            thumbnail = version.get("thumbnail")
            if not thumbnail:
                continue

            parent = version["asset"]["parent"]
            task = version["task"]
            parent["thumbnail_id"] = version["thumbnail_id"]
            if parent.entity_type.lower() == "project":
                name = parent["full_name"]
            else:
                name = parent["name"]

            task_msg = ""
            if task:
                task["thumbnail_id"] = version["thumbnail_id"]
                task_msg = " and task [ {} ]".format(task["name"])

            self.log.info(">>> Updating thumbnail for shot [ {} ]{}".format(
                name, task_msg
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


def register(session, plugins_presets):
    ThumbnailEvents(session, plugins_presets).register()
