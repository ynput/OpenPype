from pype.modules.ftrack import BaseEvent


class ThumbnailEvents(BaseEvent):
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
        project_entity = self.get_project_entity_from_event(
            session, event, project_id
        )
        project_settings = self.get_settings_for_project(
            session, event, project_entity=project_entity
        )

        project_name = project_entity["full_name"]
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
                continue

                continue


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
