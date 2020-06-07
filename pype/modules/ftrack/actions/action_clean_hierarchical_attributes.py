import collections
import ftrack_api
from pype.modules.ftrack.lib import BaseAction, statics_icon
from pype.modules.ftrack.lib.avalon_sync import get_avalon_attr


class CleanHierarchicalAttrsAction(BaseAction):
    identifier = "clean.hierarchical.attr"
    label = "Pype Admin"
    variant = "- Clean hierarchical custom attributes"
    description = "Unset empty hierarchical attribute values."
    role_list = ["Pypeclub", "Administrator", "Project Manager"]
    icon = statics_icon("ftrack", "action_icons", "PypeAdmin.svg")

    all_project_entities_query = (
        "select id, name, parent_id, link"
        " from TypedContext where project_id is \"{}\""
    )
    cust_attr_query = (
        "select value, entity_id from CustomAttributeValue "
        "where entity_id in ({}) and configuration_id is \"{}\""
    )

    def discover(self, session, entities, event):
        """Show only on project entity."""
        if len(entities) == 1 and entities[0].entity_type.lower() == "project":
            return True
        return False

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

        attrs, hier_attrs = get_avalon_attr(session)

        for attr in hier_attrs:
            configuration_key = attr["key"]
            self.log.debug(
                "Looking for cleanup of custom attribute \"{}\"".format(
                    configuration_key
                )
            )
            configuration_id = attr["id"]
            call_expr = [{
                "action": "query",
                "expression": self.cust_attr_query.format(
                    entity_ids_joined, configuration_id
                )
            }]

            [values] = self.session.call(call_expr)

            data = {}
            for item in values["data"]:
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
                entity_key = collections.OrderedDict({
                    "configuration_id": configuration_id,
                    "entity_id": entity_id
                })
                session.recorded_operations.push(
                    ftrack_api.operation.DeleteEntityOperation(
                        "CustomAttributeValue",
                        entity_key
                    )
                )
            session.commit()

        return True


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    CleanHierarchicalAttrsAction(session, plugins_presets).register()
