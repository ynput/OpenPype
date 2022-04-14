"""
Requires:
    context > ftrackSession
    context > ftrackEntity
    instance > ftrackEntity

Provides:
    instance > customData > ftrack
"""
import copy

import pyblish.api


class CollectFtrackCustomAttributeData(pyblish.api.ContextPlugin):
    """Collect custom attribute values and store them to customData.

    Data are stored into each instance in context under
        instance.data["customData"]["ftrack"].

    Hierarchical attributes are not looked up properly for that functionality
    custom attribute values lookup must be extended.
    """

    order = pyblish.api.CollectorOrder + 0.4992
    label = "Collect Ftrack Custom Attribute Data"

    # Name of custom attributes for which will be look for
    custom_attribute_keys = []

    def process(self, context):
        if not self.custom_attribute_keys:
            self.log.info("Custom attribute keys are not set. Skipping")
            return

        ftrack_entities_by_id = {}
        default_entity_id = None

        context_entity = context.data.get("ftrackEntity")
        if context_entity:
            entity_id = context_entity["id"]
            default_entity_id = entity_id
            ftrack_entities_by_id[entity_id] = context_entity

        instances_by_entity_id = {
            default_entity_id: []
        }
        for instance in context:
            entity = instance.data.get("ftrackEntity")
            if not entity:
                instances_by_entity_id[default_entity_id].append(instance)
                continue

            entity_id = entity["id"]
            ftrack_entities_by_id[entity_id] = entity
            if entity_id not in instances_by_entity_id:
                instances_by_entity_id[entity_id] = []
            instances_by_entity_id[entity_id].append(instance)

        if not ftrack_entities_by_id:
            self.log.info("Ftrack entities are not set. Skipping")
            return

        session = context.data["ftrackSession"]
        custom_attr_key_by_id = self.query_attr_confs(session)
        if not custom_attr_key_by_id:
            self.log.info((
                "Didn't find any of defined custom attributes {}"
            ).format(", ".join(self.custom_attribute_keys)))
            return

        entity_ids = list(instances_by_entity_id.keys())
        values_by_entity_id = self.query_attr_values(
            session, entity_ids, custom_attr_key_by_id
        )

        for entity_id, instances in instances_by_entity_id.items():
            if entity_id not in values_by_entity_id:
                # Use defaut empty values
                entity_id = None

            for instance in instances:
                value = copy.deepcopy(values_by_entity_id[entity_id])
                if "customData" not in instance.data:
                    instance.data["customData"] = {}
                instance.data["customData"]["ftrack"] = value
                instance_label = (
                    instance.data.get("label") or instance.data["name"]
                )
                self.log.debug((
                    "Added ftrack custom data to instance \"{}\": {}"
                ).format(instance_label, value))

    def query_attr_values(self, session, entity_ids, custom_attr_key_by_id):
        # Prepare values for query
        entity_ids_joined = ",".join([
            '"{}"'.format(entity_id)
            for entity_id in entity_ids
        ])
        conf_ids_joined = ",".join([
            '"{}"'.format(conf_id)
            for conf_id in custom_attr_key_by_id.keys()
        ])
        # Query custom attribute values
        value_items = session.query(
            (
                "select value, entity_id, configuration_id"
                " from CustomAttributeValue"
                " where entity_id in ({}) and configuration_id in ({})"
            ).format(
                entity_ids_joined,
                conf_ids_joined
            )
        ).all()

        # Prepare default value output per entity id
        values_by_key = {
            key: None for key in self.custom_attribute_keys
        }
        # Prepare all entity ids that were queried
        values_by_entity_id = {
            entity_id: copy.deepcopy(values_by_key)
            for entity_id in entity_ids
        }
        # Add none entity id which is used as default value
        values_by_entity_id[None] = copy.deepcopy(values_by_key)
        # Go through queried data and store them
        for item in value_items:
            conf_id = item["configuration_id"]
            conf_key = custom_attr_key_by_id[conf_id]
            entity_id = item["entity_id"]
            values_by_entity_id[entity_id][conf_key] = item["value"]
        return values_by_entity_id

    def query_attr_confs(self, session):
        custom_attributes = set(self.custom_attribute_keys)
        cust_attrs_query = (
            "select id, key from CustomAttributeConfiguration"
            " where key in ({})"
        ).format(", ".join(
            ["\"{}\"".format(attr_name) for attr_name in custom_attributes]
        ))

        custom_attr_confs = session.query(cust_attrs_query).all()
        return {
            conf["id"]: conf["key"]
            for conf in custom_attr_confs
        }
