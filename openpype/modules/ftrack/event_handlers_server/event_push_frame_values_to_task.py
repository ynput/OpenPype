import collections
import copy
from typing import Any

import ftrack_api

from openpype.client import get_project
from openpype_modules.ftrack.lib import (
    BaseEvent,
    query_custom_attributes,
)


class PushHierValuesToNonHierEvent(BaseEvent):
    """Push value changes between hierarchical and non-hierarchical attributes.

    Changes of non-hierarchical attributes are pushed to hierarchical and back.
    The attributes must have same definition of custom attribute.

    Handler does not handle changes of hierarchical parents. So if entity does
    not have explicitly set value of hierarchical attribute and any parent
    would change it the change would not be propagated.

    The handler also push the value to task entity on task creation
        and movement. To push values between hierarchical & non-hierarchical
        add 'Task' to entity types in settings.

    Todos:
        Task attribute values push on create/move should be possible to
            enabled by settings.
    """

    # Ignore event handler by default
    cust_attrs_query = (
        "select id, key, object_type_id, is_hierarchical, default"
        " from CustomAttributeConfiguration"
        " where key in ({})"
    )

    _cached_task_object_id = None
    _cached_interest_object_ids = None
    _cached_user_id = None
    _cached_changes = []
    _max_delta = 30

    settings_key = "sync_hier_entity_attributes"

    def filter_entities_info(
        self, event: ftrack_api.event.base.Event
    ) -> dict[str, list[dict[str, Any]]]:
        """Basic entities filter info we care about.

        This filtering is first of many filters. This does not query anything
        from ftrack nor use settings.

        Args:
            event (ftrack_api.event.base.Event): Ftrack event with update
                information.

        Returns:
            dict[str, list[dict[str, Any]]]: Filtered entity changes by
                project id.
        """

        # Filter if event contain relevant data
        entities_info = event["data"].get("entities")
        if not entities_info:
            return

        entities_info_by_project_id = collections.defaultdict(list)
        for entity_info in entities_info:
            # Ignore removed entities
            if entity_info.get("action") == "remove":
                continue

            # Care only about information with changes of entities
            changes = entity_info.get("changes")
            if not changes:
                continue

            # Get project id from entity info
            project_id = None
            for parent_item in reversed(entity_info["parents"]):
                if parent_item["entityType"] == "show":
                    project_id = parent_item["entityId"]
                    break

            if project_id is None:
                continue

            entities_info_by_project_id[project_id].append(entity_info)

        return entities_info_by_project_id

    def _get_attrs_configurations(self, session, interest_attributes):
        """Get custom attribute configurations by name.

        Args:
            session (ftrack_api.Session): Ftrack sesson.
            interest_attributes (list[str]): Names of custom attributes
                that should be synchronized.

        Returns:
            tuple[dict[str, list], list]: Attributes by object id and
                hierarchical attributes.
        """

        attrs = session.query(self.cust_attrs_query.format(
            self.join_query_keys(interest_attributes)
        )).all()

        attrs_by_obj_id = collections.defaultdict(list)
        hier_attrs = []
        for attr in attrs:
            if attr["is_hierarchical"]:
                hier_attrs.append(attr)
                continue
            obj_id = attr["object_type_id"]
            attrs_by_obj_id[obj_id].append(attr)
        return attrs_by_obj_id, hier_attrs

    def _get_handler_project_settings(
        self,
        session: ftrack_api.Session,
        event: ftrack_api.event.base.Event,
        project_id: str
    ) -> tuple[set[str], set[str]]:
        """Get handler settings based on the project.

        Args:
            session (ftrack_api.Session): Ftrack session.
            event (ftrack_api.event.base.Event): Ftrack event which triggered
                the changes.
            project_id (str): Project id where the current changes are handled.

        Returns:
            tuple[set[str], set[str]]: Attribute names we care about and
                entity types we care about.
        """

        project_name: str = self.get_project_name_from_event(
            session, event, project_id
        )
        if get_project(project_name) is None:
            self.log.debug("Project not found in OpenPype. Skipping")
            return set(), set()

        # Load settings
        project_settings: dict[str, Any] = (
            self.get_project_settings_from_event(event, project_name)
        )
        # Load status mapping from presets
        event_settings: dict[str, Any] = (
            project_settings
            ["ftrack"]
            ["events"]
            [self.settings_key]
        )
        # Skip if event is not enabled
        if not event_settings["enabled"]:
            self.log.debug("Project \"{}\" has disabled {}".format(
                project_name, self.__class__.__name__
            ))
            return set(), set()

        interest_attributes: list[str] = event_settings["interest_attributes"]
        if not interest_attributes:
            self.log.info((
                "Project \"{}\" does not have filled 'interest_attributes',"
                " skipping."
            ))

        interest_entity_types: list[str] = (
            event_settings["interest_entity_types"])
        if not interest_entity_types:
            self.log.info((
                "Project \"{}\" does not have filled 'interest_entity_types',"
                " skipping."
            ))

        # Unify possible issues from settings ('Asset Build' -> 'assetbuild')
        interest_entity_types: set[str] = {
            entity_type.replace(" ", "").lower()
            for entity_type in interest_entity_types
        }
        return set(interest_attributes), interest_entity_types

    def _entities_filter_by_settings(
        self,
        entities_info: list[dict[str, Any]],
        interest_attributes: set[str],
        interest_entity_types: set[str]
    ):
        new_entities_info = []
        for entity_info in entities_info:
            entity_type_low = entity_info["entity_type"].lower()

            changes = entity_info["changes"]
            # SPECIAL CASE: Capture changes of task created/moved under
            #   interested entity type
            if (
                entity_type_low == "task"
                and "parent_id" in changes
            ):
                # Direct parent is always second item in 'parents' and 'Task'
                #   must have at least one parent
                parent_info = entity_info["parents"][1]
                parent_entity_type = (
                    parent_info["entity_type"]
                    .replace(" ", "")
                    .lower()
                )
                if parent_entity_type in interest_entity_types:
                    new_entities_info.append(entity_info)
                    continue

            # Skip if entity type is not enabled for attr value sync
            if entity_type_low not in interest_entity_types:
                continue

            valid_attr_change = entity_info.get("action") == "add"
            for attr_key in interest_attributes:
                if valid_attr_change:
                    break

                if attr_key not in changes:
                    continue

                if changes[attr_key]["new"] is not None:
                    valid_attr_change = True

            if not valid_attr_change:
                continue

            new_entities_info.append(entity_info)

        return new_entities_info

    def propagate_attribute_changes(
        self,
        session,
        interest_attributes,
        entities_info,
        attrs_by_obj_id,
        hier_attrs,
        real_values_by_entity_id,
        hier_values_by_entity_id,
    ):
        hier_attr_ids_by_key = {
            attr["key"]: attr["id"]
            for attr in hier_attrs
        }
        filtered_interest_attributes = {
            attr_name
            for attr_name in interest_attributes
            if attr_name in hier_attr_ids_by_key
        }
        attrs_keys_by_obj_id = {}
        for obj_id, attrs in attrs_by_obj_id.items():
            attrs_keys_by_obj_id[obj_id] = {
                attr["key"]: attr["id"]
                for attr in attrs
            }

        op_changes = []
        for entity_info in entities_info:
            entity_id = entity_info["entityId"]
            obj_id = entity_info["objectTypeId"]
            # Skip attributes sync if does not have object specific custom
            #   attribute
            if obj_id not in attrs_keys_by_obj_id:
                continue
            attr_keys = attrs_keys_by_obj_id[obj_id]
            real_values = real_values_by_entity_id[entity_id]
            hier_values = hier_values_by_entity_id[entity_id]

            changes = copy.deepcopy(entity_info["changes"])
            obj_id_attr_keys = {
                attr_key
                for attr_key in filtered_interest_attributes
                if attr_key in attr_keys
            }
            if not obj_id_attr_keys:
                continue

            value_by_key = {}
            is_new_entity = entity_info.get("action") == "add"
            for attr_key in obj_id_attr_keys:
                if (
                    attr_key in changes
                    and changes[attr_key]["new"] is not None
                ):
                    value_by_key[attr_key] = changes[attr_key]["new"]

                if not is_new_entity:
                    continue

                hier_attr_id = hier_attr_ids_by_key[attr_key]
                attr_id = attr_keys[attr_key]
                if hier_attr_id in real_values or attr_id in real_values:
                    continue

                value_by_key[attr_key] = hier_values[hier_attr_id]

            for key, new_value in value_by_key.items():
                if new_value is None:
                    continue

                hier_id = hier_attr_ids_by_key[key]
                std_id = attr_keys[key]
                real_hier_value = real_values.get(hier_id)
                real_std_value = real_values.get(std_id)
                hier_value = hier_values[hier_id]
                # Get right type of value for conversion
                #   - values in event are strings
                type_value = real_hier_value
                if type_value is None:
                    type_value = real_std_value
                    if type_value is None:
                        type_value = hier_value
                        # Skip if current values are not set
                        if type_value is None:
                            continue

                try:
                    new_value = type(type_value)(new_value)
                except Exception:
                    self.log.warning((
                        "Couldn't convert from {} to {}."
                        " Skipping update values."
                    ).format(type(new_value), type(type_value)))
                    continue

                real_std_value_is_same = new_value == real_std_value
                real_hier_value_is_same = new_value == real_hier_value
                # New value does not match anything in current entity values
                if (
                    not is_new_entity
                    and not real_std_value_is_same
                    and not real_hier_value_is_same
                ):
                    continue

                if not real_std_value_is_same:
                    op_changes.append((
                        std_id,
                        entity_id,
                        new_value,
                        real_values.get(std_id),
                        std_id in real_values
                    ))

                if not real_hier_value_is_same:
                    op_changes.append((
                        hier_id,
                        entity_id,
                        new_value,
                        real_values.get(hier_id),
                        hier_id in real_values
                    ))

        for change in op_changes:
            (
                attr_id,
                entity_id,
                new_value,
                old_value,
                do_update
            ) = change

            entity_key = collections.OrderedDict([
                ("configuration_id", attr_id),
                ("entity_id", entity_id)
            ])
            if do_update:
                op = ftrack_api.operation.UpdateEntityOperation(
                    "CustomAttributeValue",
                    entity_key,
                    "value",
                    old_value,
                    new_value
                )

            else:
                op = ftrack_api.operation.CreateEntityOperation(
                    "CustomAttributeValue",
                    entity_key,
                    {"value": new_value}
                )

            session.recorded_operations.push(op)
            if len(session.recorded_operations) > 100:
                session.commit()
        session.commit()

    def process_by_project(
        self,
        session: ftrack_api.Session,
        event: ftrack_api.event.base.Event,
        project_id: str,
        entities_info: list[dict[str, Any]]
    ):
        """Process changes in single project.

        Args:
            session (ftrack_api.Session): Ftrack session.
            event (ftrack_api.event.base.Event): Event which has all changes
                information.
            project_id (str): Project id related to changes.
            entities_info (list[dict[str, Any]]): Changes of entities.
        """

        (
            interest_attributes,
            interest_entity_types
        ) = self._get_handler_project_settings(session, event, project_id)
        if not interest_attributes or not interest_entity_types:
            return

        entities_info: list[dict[str, Any]] = (
            self._entities_filter_by_settings(
                entities_info,
                interest_attributes,
                interest_entity_types
            )
        )
        if not entities_info:
            return

        attrs_by_obj_id, hier_attrs = self._get_attrs_configurations(
            session, interest_attributes
        )
        # Skip if attributes are not available
        #   - there is nothing to sync
        if not attrs_by_obj_id or not hier_attrs:
            return

        entity_ids_by_parent_id = collections.defaultdict(set)
        all_entity_ids = set()
        for entity_info in entities_info:
            entity_id = None
            for item in entity_info["parents"]:
                item_id = item["entityId"]
                all_entity_ids.add(item_id)
                if entity_id is not None:
                    entity_ids_by_parent_id[item_id].add(entity_id)
                entity_id = item_id

        attr_ids = {attr["id"] for attr in hier_attrs}
        for attrs in attrs_by_obj_id.values():
            attr_ids |= {attr["id"] for attr in attrs}

        # Query real custom attribute values
        #   - we have to know what are the real values, if are set and to what
        #       value
        value_items = query_custom_attributes(
            session, attr_ids, all_entity_ids, True
        )
        real_values_by_entity_id = collections.defaultdict(dict)
        for item in value_items:
            entity_id = item["entity_id"]
            attr_id = item["configuration_id"]
            real_values_by_entity_id[entity_id][attr_id] = item["value"]

        hier_values_by_entity_id = {}
        default_values = {
            attr["id"]: attr["default"]
            for attr in hier_attrs
        }
        hier_queue = collections.deque()
        hier_queue.append((default_values, [project_id]))
        while hier_queue:
            parent_values, entity_ids = hier_queue.popleft()
            for entity_id in entity_ids:
                entity_values = copy.deepcopy(parent_values)
                real_values = real_values_by_entity_id[entity_id]
                for attr_id, value in real_values.items():
                    entity_values[attr_id] = value
                hier_values_by_entity_id[entity_id] = entity_values
                hier_queue.append(
                    (entity_values, entity_ids_by_parent_id[entity_id])
                )

        self.propagate_attribute_changes(
            session,
            interest_attributes,
            entities_info,
            attrs_by_obj_id,
            hier_attrs,
            real_values_by_entity_id,
            hier_values_by_entity_id,
        )

    def launch(self, session, event):
        filtered_entities_info = self.filter_entities_info(event)
        if not filtered_entities_info:
            return

        for project_id, entities_info in filtered_entities_info.items():
            self.process_by_project(session, event, project_id, entities_info)


def register(session):
    PushHierValuesToNonHierEvent(session).register()
