import collections
import ftrack_api
from openpype_modules.ftrack.lib import (
    BaseAction,
    statics_icon,
    get_openpype_attr
)


class CleanHierarchicalAttrsAction(BaseAction):
    identifier = "clean.hierarchical.attr"
    label = "OpenPype Admin"
    variant = "- Clean hierarchical custom attributes"
    description = "Unset empty hierarchical attribute values."
    icon = statics_icon("ftrack", "action_icons", "OpenPypeAdmin.svg")

    all_project_entities_query = (
        "select id, name, parent_id, link"
        " from TypedContext where project_id is \"{}\""
    )
    cust_attr_query = (
        "select value, entity_id from CustomAttributeValue"
        " where entity_id in ({}) and configuration_id is \"{}\""
    )
    settings_key = "clean_hierarchical_attr"

    def discover(self, session, entities, event):
        """Show only on project entity."""
        if (
            len(entities) != 1
            or entities[0].entity_type.lower() != "project"
        ):
            return False

        return self.valid_roles(session, entities, event)

    def launch(self, session, entities, event):
        project = entities[0]

        user_message = "This may take some time"
        self.show_message(event, user_message, result=True)
        self.log.debug("Preparing entities for cleanup.")

        all_entities = session.query(
            self.all_project_entities_query.format(project["id"])
        ).all()

        all_entities_ids = [
            "\"{}\"".format(entity["id"])
            for entity in all_entities
            if entity.entity_type.lower() != "task"
        ]
        self.log.debug(
            "Collected {} entities to process.".format(len(all_entities_ids))
        )
        entity_ids_joined = ", ".join(all_entities_ids)

        attrs, hier_attrs = get_openpype_attr(session)

        for attr in hier_attrs:
            configuration_key = attr["key"]
            self.log.debug(
                "Looking for cleanup of custom attribute \"{}\"".format(
                    configuration_key
                )
            )
            configuration_id = attr["id"]
            values = session.query(
                self.cust_attr_query.format(
                    entity_ids_joined, configuration_id
                )
            ).all()

            data = {}
            for item in values:
                value = item["value"]
                if value is None:
                    data[item["entity_id"]] = value

            if not data:
                self.log.debug(
                    "Nothing to clean for \"{}\".".format(configuration_key)
                )
                continue

            self.log.debug("Cleaning up {} values for \"{}\".".format(
                len(data), configuration_key
            ))
            for entity_id, value in data.items():
                entity_key = collections.OrderedDict((
                    ("configuration_id", configuration_id),
                    ("entity_id", entity_id)
                ))
                session.recorded_operations.push(
                    ftrack_api.operation.DeleteEntityOperation(
                        "CustomAttributeValue",
                        entity_key
                    )
                )
            session.commit()

        return True


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    CleanHierarchicalAttrsAction(session).register()
