import copy
import json
import collections

import ftrack_api

from openpype_modules.ftrack.lib import (
    ServerAction,
    statics_icon,
)
from openpype_modules.ftrack.lib.avalon_sync import create_chunks


class TransferHierarchicalValues(ServerAction):
    """Transfer values across hierarhcical attributes.

    Aalso gives ability to convert types meanwhile. That is limited to
    conversions between numbers and strings
    - int <-> float
    - in, float -> string
    """

    identifier = "transfer.hierarchical.values"
    label = "OpenPype Admin"
    variant = "- Transfer values between 2 custom attributes"
    description = (
        "Move values from a hierarchical attribute to"
        " second hierarchical attribute."
    )
    icon = statics_icon("ftrack", "action_icons", "OpenPypeAdmin.svg")

    all_project_entities_query = (
        "select id, name, parent_id, link"
        " from TypedContext where project_id is \"{}\""
    )
    cust_attr_query = (
        "select value, entity_id from CustomAttributeValue"
        " where entity_id in ({}) and configuration_id is \"{}\""
    )
    settings_key = "transfer_values_of_hierarchical_attributes"

    def discover(self, session, entities, event):
        """Show anywhere."""

        return self.valid_roles(session, entities, event)

    def _selection_interface(self, session, event_values=None):
        title = "Transfer hierarchical values"

        attr_confs = session.query(
            (
                "select id, key from CustomAttributeConfiguration"
                " where is_hierarchical is true"
            )
        ).all()
        attr_items = []
        for attr_conf in attr_confs:
            attr_items.append({
                "value": attr_conf["id"],
                "label": attr_conf["key"]
            })

        if len(attr_items) < 2:
            return {
                "title": title,
                "items": [{
                    "type": "label",
                    "value": (
                        "Didn't found custom attributes"
                        " that can be transfered."
                    )
                }]
            }

        attr_items = sorted(attr_items, key=lambda item: item["label"])
        items = []
        item_splitter = {"type": "label", "value": "---"}
        items.append({
            "type": "label",
            "value": (
                "<h2>Please select source and destination"
                " Custom attribute</h2>"
            )
        })
        items.append({
            "type": "label",
            "value": (
                "<b>WARNING:</b> This will take affect for all projects!"
            )
        })
        if event_values:
            items.append({
                "type": "label",
                "value": (
                    "<b>Note:</b> Please select 2 different custom attributes."
                )
            })

        items.append(item_splitter)

        src_item = {
            "type": "enumerator",
            "label": "Source",
            "name": "src_attr_id",
            "data": copy.deepcopy(attr_items)
        }
        dst_item = {
            "type": "enumerator",
            "label": "Destination",
            "name": "dst_attr_id",
            "data": copy.deepcopy(attr_items)
        }
        delete_item = {
            "type": "boolean",
            "name": "delete_dst_attr_first",
            "label": "Delete first",
            "value": False
        }
        if event_values:
            src_item["value"] = event_values["src_attr_id"]
            dst_item["value"] = event_values["dst_attr_id"]
            delete_item["value"] = event_values["delete_dst_attr_first"]

        items.append(src_item)
        items.append(dst_item)
        items.append(item_splitter)
        items.append({
            "type": "label",
            "value": (
                "<b>WARNING:</b> All values from destination"
                " Custom Attribute will be removed if this is enabled."
            )
        })
        items.append(delete_item)

        return {
            "title": title,
            "items": items
        }

    def interface(self, session, entities, event):
        if event["data"].get("values", {}):
            return None

        return self._selection_interface(session)

    def launch(self, session, entities, event):
        values = event["data"].get("values", {})
        if not values:
            return None
        src_attr_id = values["src_attr_id"]
        dst_attr_id = values["dst_attr_id"]
        delete_dst_values = values["delete_dst_attr_first"]

        if not src_attr_id or not dst_attr_id:
            self.log.info("Attributes were not filled. Nothing to do.")
            return {
                "success": True,
                "message": "Nothing to do"
            }

        if src_attr_id == dst_attr_id:
            self.log.info((
                "Same attributes were selected {}, {}."
                " Showing interface again."
            ).format(src_attr_id, dst_attr_id))
            return self._selection_interface(session, values)

        # Query custom attrbutes
        src_conf = session.query((
            "select id from CustomAttributeConfiguration where id is {}"
        ).format(src_attr_id)).one()
        dst_conf = session.query((
            "select id from CustomAttributeConfiguration where id is {}"
        ).format(dst_attr_id)).one()
        src_type_name = src_conf["type"]["name"]
        dst_type_name = dst_conf["type"]["name"]
        # Limit conversion to
        # - same type -> same type (there is no need to do conversion)
        # - number <Any> -> number <Any> (int to float and back)
        # - number <Any> -> str (any number can be converted to str)
        src_type = None
        dst_type = None
        if src_type_name == "number" or src_type_name != dst_type_name:
            src_type = self._get_attr_type(dst_conf)
            dst_type = self._get_attr_type(dst_conf)
            valid = False
            # Can convert numbers
            if src_type in (int, float) and dst_type in (int, float):
                valid = True
            # Can convert numbers to string
            elif dst_type is str:
                valid = True

            if not valid:
                self.log.info((
                    "Don't know how to properly convert"
                    " custom attribute types {} > {}"
                ).format(src_type_name, dst_type_name))
                return {
                    "message": (
                        "Don't know how to properly convert"
                        " custom attribute types {} > {}"
                    ).format(src_type_name, dst_type_name),
                    "success": False
                }

        # Query source values
        src_attr_values = session.query(
            (
                "select value, entity_id"
                " from CustomAttributeValue"
                " where configuration_id is {}"
            ).format(src_attr_id)
        ).all()

        self.log.debug("Queried source values.")
        failed_entity_ids = []
        if dst_type is not None:
            self.log.debug("Converting source values to desctination type")
            value_by_id = {}
            for attr_value in src_attr_values:
                entity_id = attr_value["entity_id"]
                value = attr_value["value"]
                if value is not None:
                    try:
                        if dst_type is not None:
                            value = dst_type(value)
                        value_by_id[entity_id] = value
                    except Exception:
                        failed_entity_ids.append(entity_id)

        if failed_entity_ids:
            self.log.info(
                "Couldn't convert some values to destination attribute"
            )
            return {
                "success": False,
                "message": (
                    "Couldn't convert some values to destination attribute"
                )
            }

        # Delete destination custom attributes first
        if delete_dst_values:
            self.log.info("Deleting destination custom attribute values first")
            self._delete_custom_attribute_values(session, dst_attr_id)

        self.log.info("Applying source values on destination custom attribute")
        self._apply_values(session, value_by_id, dst_attr_id)
        return True

    def _delete_custom_attribute_values(self, session, dst_attr_id):
        dst_attr_values = session.query(
            (
                "select configuration_id, entity_id"
                " from CustomAttributeValue"
                " where configuration_id is {}"
            ).format(dst_attr_id)
        ).all()
        delete_operations = []
        for attr_value in dst_attr_values:
            entity_id = attr_value["entity_id"]
            configuration_id = attr_value["configuration_id"]
            entity_key = collections.OrderedDict((
                ("configuration_id", configuration_id),
                ("entity_id", entity_id)
            ))
            delete_operations.append(
                ftrack_api.operation.DeleteEntityOperation(
                    "CustomAttributeValue",
                    entity_key
                )
            )

        if not delete_operations:
            return

        for chunk in create_chunks(delete_operations, 500):
            for operation in chunk:
                session.recorded_operations.push(operation)
            session.commit()

    def _apply_values(self, session, value_by_id, dst_attr_id):
        dst_attr_values = session.query(
            (
                "select configuration_id, entity_id"
                " from CustomAttributeValue"
                " where configuration_id is {}"
            ).format(dst_attr_id)
        ).all()

        dst_entity_ids_with_value = {
            item["entity_id"]
            for item in dst_attr_values
        }
        operations = []
        for entity_id, value in value_by_id.items():
            entity_key = collections.OrderedDict((
                ("configuration_id", dst_attr_id),
                ("entity_id", entity_id)
            ))
            if entity_id in dst_entity_ids_with_value:
                operations.append(
                    ftrack_api.operation.UpdateEntityOperation(
                        "CustomAttributeValue",
                        entity_key,
                        "value",
                        ftrack_api.symbol.NOT_SET,
                        value
                    )
                )
            else:
                operations.append(
                    ftrack_api.operation.CreateEntityOperation(
                        "CustomAttributeValue",
                        entity_key,
                        {"value": value}
                    )
                )

        if not operations:
            return

        for chunk in create_chunks(operations, 500):
            for operation in chunk:
                session.recorded_operations.push(operation)
            session.commit()

    def _get_attr_type(self, conf_def):
        type_name = conf_def["type"]["name"]
        if type_name == "text":
            return str

        if type_name == "number":
            config = json.loads(conf_def["config"])
            if config["isdecimal"]:
                return float
            return int
        return None


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    TransferHierarchicalValues(session).register()
