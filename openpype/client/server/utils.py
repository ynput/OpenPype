import os
import uuid

import ayon_api

from openpype.client.operations_base import REMOVED_VALUE


class _GlobalCache:
    initialized = False


def get_ayon_server_api_connection():
    if _GlobalCache.initialized:
        con = ayon_api.get_server_api_connection()
    else:
        from openpype.lib.local_settings import get_local_site_id

        _GlobalCache.initialized = True
        site_id = get_local_site_id()
        version = os.getenv("AYON_VERSION")
        if ayon_api.is_connection_created():
            con = ayon_api.get_server_api_connection()
            con.set_site_id(site_id)
            con.set_client_version(version)
        else:
            con = ayon_api.create_connection(site_id, version)
    return con


def create_entity_id():
    return uuid.uuid1().hex


def prepare_attribute_changes(old_entity, new_entity, replace=False):
    """Prepare changes of attributes on entities.

    Compare 'attrib' of old and new entity data to prepare only changed
    values that should be sent to server for update.

    Example:
        >>> # Limited entity data to 'attrib'
        >>> old_entity = {
        ...     "attrib": {"attr_1": 1, "attr_2": "MyString", "attr_3": True}
        ... }
        >>> new_entity = {
        ...     "attrib": {"attr_1": 2, "attr_3": True, "attr_4": 3}
        ... }
        >>> # Changes if replacement should not happen
        >>> expected_changes = {
        ...   "attr_1": 2,
        ...   "attr_4": 3
        ... }
        >>> changes = prepare_attribute_changes(old_entity, new_entity)
        >>> changes == expected_changes
        True

        >>> # Changes if replacement should happen
        >>> expected_changes_replace = {
        ...   "attr_1": 2,
        ...   "attr_2": REMOVED_VALUE,
        ...   "attr_4": 3
        ... }
        >>> changes_replace = prepare_attribute_changes(
        ...     old_entity, new_entity, True)
        >>> changes_replace == expected_changes_replace
        True

    Args:
        old_entity (dict[str, Any]): Data of entity queried from server.
        new_entity (dict[str, Any]): Entity data with applied changes.
        replace (bool): New entity should fully replace all old entity values.

    Returns:
        Dict[str, Any]: Values from new entity only if value has changed.
    """

    attrib_changes = {}
    new_attrib = new_entity.get("attrib")
    old_attrib = old_entity.get("attrib")
    if new_attrib is None:
        if not replace:
            return attrib_changes
        new_attrib = {}

    if old_attrib is None:
        return new_attrib

    for attr, new_attr_value in new_attrib.items():
        old_attr_value = old_attrib.get(attr)
        if old_attr_value != new_attr_value:
            attrib_changes[attr] = new_attr_value

    if replace:
        for attr in old_attrib:
            if attr not in new_attrib:
                attrib_changes[attr] = REMOVED_VALUE

    return attrib_changes


def prepare_entity_changes(old_entity, new_entity, replace=False):
    """Prepare changes of AYON entities.

    Compare old and new entity to filter values from new data that changed.

    Args:
        old_entity (dict[str, Any]): Data of entity queried from server.
        new_entity (dict[str, Any]): Entity data with applied changes.
        replace (bool): All attributes should be replaced by new values. So
            all attribute values that are not on new entity will be removed.

    Returns:
        Dict[str, Any]: Only values from new entity that changed.
    """

    changes = {}
    for key, new_value in new_entity.items():
        if key == "attrib":
            continue

        old_value = old_entity.get(key)
        if old_value != new_value:
            changes[key] = new_value

    if replace:
        for key in old_entity:
            if key not in new_entity:
                changes[key] = REMOVED_VALUE

    attr_changes = prepare_attribute_changes(old_entity, new_entity, replace)
    if attr_changes:
        changes["attrib"] = attr_changes
    return changes
