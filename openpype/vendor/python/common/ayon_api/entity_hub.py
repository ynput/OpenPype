import re
import copy
import collections
from abc import ABCMeta, abstractmethod

import six
from ._api import get_server_api_connection
from .utils import create_entity_id, convert_entity_id, slugify_string


class _CustomNone(object):
    def __init__(self, name=None):
        self._name = name or "CustomNone"

    def __repr__(self):
        return "<{}>".format(self._name)

    def __bool__(self):
        return False


UNKNOWN_VALUE = _CustomNone("UNKNOWN_VALUE")
PROJECT_PARENT_ID = _CustomNone("PROJECT_PARENT_ID")
_NOT_SET = _CustomNone("_NOT_SET")


class EntityHub(object):
    """Helper to create, update or remove entities in project.

    The hub is a guide to operation with folder entities and update of project.
    Project entity must already exist on server (can be only updated).

    Object is caching entities queried from server. They won't be required once
    they were queried, so it is recommended to create new hub or clear cache
    frequently.

    Todos:
        Listen to server events about entity changes to be able update already
            queried entities.

    Args:
        project_name (str): Name of project where changes will happen.
        connection (ServerAPI): Connection to server with logged user.
        allow_data_changes (bool): This option gives ability to change 'data'
            key on entities. This is not recommended as 'data' may be use for
            secure information and would also slow down server queries. Content
            of 'data' key can't be received only GraphQl.
    """

    def __init__(
        self, project_name, connection=None, allow_data_changes=None
    ):
        if not connection:
            connection = get_server_api_connection()
        major, minor, patch, _, _ = connection.server_version_tuple
        path_start_with_slash = True
        if (major, minor) < (0, 6):
            path_start_with_slash = False

        if allow_data_changes is None:
            allow_data_changes = connection.graphql_allows_data_in_query

        self._connection = connection
        self._path_start_with_slash = path_start_with_slash

        self._project_name = project_name
        self._entities_by_id = {}
        self._entities_by_parent_id = collections.defaultdict(list)
        self._project_entity = UNKNOWN_VALUE

        self._allow_data_changes = allow_data_changes

        self._path_reset_queue = None

    @property
    def allow_data_changes(self):
        """Entity hub allows changes of 'data' key on entities.

        Data are private and not all users may have access to them. Also to get
        'data' for entity is required to use REST api calls, which means to
        query each entity on-by-one from server.

        Returns:
            bool: Data changes are allowed.
        """

        return self._allow_data_changes

    @property
    def path_start_with_slash(self):
        """Folder path should start with slash.

        This changed in 0.6.x server version.

        Returns:
            bool: Path starts with slash.
        """

        return self._path_start_with_slash

    @property
    def project_name(self):
        """Project name which is maintained by hub.

        Returns:
            str: Name of project.
        """

        return self._project_name

    @property
    def project_entity(self):
        """Project entity.

        Returns:
            ProjectEntity: Project entity.
        """

        if self._project_entity is UNKNOWN_VALUE:
            self.fill_project_from_server()
        return self._project_entity

    def get_attributes_for_type(self, entity_type):
        """Get attributes available for a type.

        Attributes are based on entity types.

        Todos:
            Use attribute schema to validate values on entities.

        Args:
            entity_type (Literal["project", "folder", "task"]): Entity type
                for which should be attributes received.

        Returns:
            Dict[str, Dict[str, Any]]: Attribute schemas that are available
                for entered entity type.
        """

        return self._connection.get_attributes_for_type(entity_type)

    def get_entity_by_id(self, entity_id):
        """Receive entity by its id without entity type.

        The entity must be already existing in cached objects.

        Args:
            entity_id (str): Id of entity.

        Returns:
            Union[BaseEntity, None]: Entity object or None.
        """

        return self._entities_by_id.get(entity_id)

    def get_folder_by_id(self, entity_id, allow_query=True):
        """Get folder entity by id.

        Args:
            entity_id (str): Id of folder entity.
            allow_query (bool): Try to query entity from server if is not
                available in cache.

        Returns:
            Union[FolderEntity, None]: Object of folder or 'None'.
        """

        if allow_query:
            return self.get_or_query_entity_by_id(entity_id, ["folder"])
        return self._entities_by_id.get(entity_id)

    def get_task_by_id(self, entity_id, allow_query=True):
        """Get task entity by id.

        Args:
           entity_id (str): Id of task entity.
           allow_query (bool): Try to query entity from server if is not
               available in cache.

        Returns:
           Union[TaskEntity, None]: Object of folder or 'None'.
        """

        if allow_query:
            return self.get_or_query_entity_by_id(entity_id, ["task"])
        return self._entities_by_id.get(entity_id)

    def get_or_query_entity_by_id(self, entity_id, entity_types):
        """Get or query entity based on it's id and possible entity types.

        This is a helper function when entity id is known but entity type may
        have multiple possible options.

        Args:
            entity_id (str): Entity id.
            entity_types (Iterable[str]): Possible entity types that can the id
                represent. e.g. '["folder", "project"]'
        """

        existing_entity = self._entities_by_id.get(entity_id)
        if existing_entity is not None:
            return existing_entity

        if not entity_types:
            return None

        entity_data = None
        for entity_type in entity_types:
            if entity_type == "folder":
                entity_data = self._connection.get_folder_by_id(
                    self.project_name,
                    entity_id,
                    fields=self._get_folder_fields(),
                    own_attributes=True
                )
            elif entity_type == "task":
                entity_data = self._connection.get_task_by_id(
                    self.project_name,
                    entity_id,
                    own_attributes=True
                )
            else:
                raise ValueError(
                    "Unknonwn entity type \"{}\"".format(entity_type)
                )

            if entity_data:
                break

        if not entity_data:
            return None

        if entity_type == "folder":
            return self.add_folder(entity_data)
        elif entity_type == "task":
            return self.add_task(entity_data)

        return None

    @property
    def entities(self):
        """Iterator over available entities.

        Returns:
            Iterator[BaseEntity]: All queried/created entities cached in hub.
        """

        for entity in self._entities_by_id.values():
            yield entity

    def add_new_folder(self, *args, created=True, **kwargs):
        """Create folder object and add it to entity hub.

        Args:
            folder_type (str): Type of folder. Folder type must be available in
                config of project folder types.
            entity_id (Union[str, None]): Id of the entity. New id is created if
                not passed.
            parent_id (Union[str, None]): Id of parent entity.
            name (str): Name of entity.
            label (Optional[str]): Folder label.
            path (Optional[str]): Folder path. Path consist of all parent names
                with slash('/') used as separator.
            attribs (Dict[str, Any]): Attribute values.
            data (Dict[str, Any]): Entity data (custom data).
            thumbnail_id (Union[str, None]): Id of entity's thumbnail.
            active (bool): Is entity active.
            created (Optional[bool]): Entity is new. When 'None' is passed the
                value is defined based on value of 'entity_id'.

        Returns:
            FolderEntity: Added folder entity.
        """

        folder_entity = FolderEntity(
            *args, **kwargs, created=created, entity_hub=self
        )
        self.add_entity(folder_entity)
        return folder_entity

    def add_new_task(self, *args, created=True, **kwargs):
        """Create folder object and add it to entity hub.

        Args:
            task_type (str): Type of task. Task type must be available in
                config of project folder types.
            entity_id (Union[str, None]): Id of the entity. New id is created if
                not passed.
            parent_id (Union[str, None]): Id of parent entity.
            name (str): Name of entity.
            label (Optional[str]): Folder label.
            attribs (Dict[str, Any]): Attribute values.
            data (Dict[str, Any]): Entity data (custom data).
            thumbnail_id (Union[str, None]): Id of entity's thumbnail.
            active (bool): Is entity active.
            created (Optional[bool]): Entity is new. When 'None' is passed the
                value is defined based on value of 'entity_id'.

        Returns:
            TaskEntity: Added task entity.
        """

        task_entity = TaskEntity(
            *args, **kwargs, created=created, entity_hub=self
        )
        self.add_entity(task_entity)
        return task_entity

    def add_folder(self, folder):
        """Create folder object and add it to entity hub.

        Args:
            folder (Dict[str, Any]): Folder entity data.

        Returns:
            FolderEntity: Added folder entity.
        """

        folder_entity = FolderEntity.from_entity_data(folder, entity_hub=self)
        self.add_entity(folder_entity)
        return folder_entity

    def add_task(self, task):
        """Create task object and add it to entity hub.

        Args:
            task (Dict[str, Any]): Task entity data.

        Returns:
            TaskEntity: Added task entity.
        """

        task_entity = TaskEntity.from_entity_data(task, entity_hub=self)
        self.add_entity(task_entity)
        return task_entity

    def add_entity(self, entity):
        """Add entity to hub cache.

        Args:
            entity (BaseEntity): Entity that should be added to hub's cache.
        """

        self._entities_by_id[entity.id] = entity
        parent_children = self._entities_by_parent_id[entity.parent_id]
        if entity not in parent_children:
            parent_children.append(entity)

        if entity.parent_id is PROJECT_PARENT_ID:
            return

        parent = self._entities_by_id.get(entity.parent_id)
        if parent is not None:
            parent.add_child(entity.id)

    def folder_path_reseted(self, folder_id):
        """Method called from 'FolderEntity' on path reset.

        This should reset cache of folder paths on all children entities.

        The path cache is always propagated from top to bottom so if an entity
        has not cached path it means that any children can't have it cached.
        """

        if self._path_reset_queue is not None:
            self._path_reset_queue.append(folder_id)
            return

        self._path_reset_queue = collections.deque()
        self._path_reset_queue.append(folder_id)
        while self._path_reset_queue:
            children = self._entities_by_parent_id[folder_id]
            for child in children:
                # Get child path but don't trigger cache
                path = child.get_path(False)
                if path is not None:
                    # Reset it's path cache if is set
                    child.reset_path()
                else:
                    self._path_reset_queue.append(child.id)

        self._path_reset_queue = None

    def unset_entity_parent(self, entity_id, parent_id):
        entity = self._entities_by_id.get(entity_id)
        parent = self._entities_by_id.get(parent_id)
        children_ids = UNKNOWN_VALUE
        if parent is not None:
            children_ids = parent.get_children_ids(False)

        has_set_parent = False
        if entity is not None:
            has_set_parent = entity.parent_id == parent_id

        new_parent_id = None
        if has_set_parent:
            entity.parent_id = new_parent_id

        if children_ids is not UNKNOWN_VALUE and entity_id in children_ids:
            parent.remove_child(entity_id)

        if entity is None or not has_set_parent:
            self.reset_immutable_for_hierarchy_cache(parent_id)
            return

        orig_parent_children = self._entities_by_parent_id[parent_id]
        if entity in orig_parent_children:
            orig_parent_children.remove(entity)

        new_parent_children = self._entities_by_parent_id[new_parent_id]
        if entity not in new_parent_children:
            new_parent_children.append(entity)
        self.reset_immutable_for_hierarchy_cache(parent_id)

    def set_entity_parent(self, entity_id, parent_id, orig_parent_id=_NOT_SET):
        parent = self._entities_by_id.get(parent_id)
        entity = self._entities_by_id.get(entity_id)
        if entity is None:
            if parent is not None:
                children_ids = parent.get_children_ids(False)
                if (
                    children_ids is not UNKNOWN_VALUE
                    and entity_id in children_ids
                ):
                    parent.remove_child(entity_id)
                self.reset_immutable_for_hierarchy_cache(parent.id)
            return

        if orig_parent_id is _NOT_SET:
            orig_parent_id = entity.parent_id
            if orig_parent_id == parent_id:
                return

        orig_parent_children = self._entities_by_parent_id[orig_parent_id]
        if entity in orig_parent_children:
            orig_parent_children.remove(entity)
        self.reset_immutable_for_hierarchy_cache(orig_parent_id)

        orig_parent = self._entities_by_id.get(orig_parent_id)
        if orig_parent is not None:
            orig_parent.remove_child(entity_id)

        parent_children = self._entities_by_parent_id[parent_id]
        if entity not in parent_children:
            parent_children.append(entity)

        entity.parent_id = parent_id
        if parent is None or parent.get_children_ids(False) is UNKNOWN_VALUE:
            return

        parent.add_child(entity_id)
        self.reset_immutable_for_hierarchy_cache(parent_id)

    def _query_entity_children(self, entity):
        folder_fields = self._get_folder_fields()
        tasks = []
        folders = []
        if entity.entity_type == "project":
            folders = list(self._connection.get_folders(
                entity["name"],
                parent_ids=[entity.id],
                fields=folder_fields,
                own_attributes=True
            ))

        elif entity.entity_type == "folder":
            folders = list(self._connection.get_folders(
                self.project_entity["name"],
                parent_ids=[entity.id],
                fields=folder_fields,
                own_attributes=True
            ))

            tasks = list(self._connection.get_tasks(
                self.project_entity["name"],
                folder_ids=[entity.id],
                own_attributes=True
            ))

        children_ids = {
            child.id
            for child in self._entities_by_parent_id[entity.id]
        }
        for folder in folders:
            folder_entity = self._entities_by_id.get(folder["id"])
            if folder_entity is not None:
                if folder_entity.parent_id == entity.id:
                    children_ids.add(folder_entity.id)
                continue

            folder_entity = self.add_folder(folder)
            children_ids.add(folder_entity.id)

        for task in tasks:
            task_entity = self._entities_by_id.get(task["id"])
            if task_entity is not None:
                if task_entity.parent_id == entity.id:
                    children_ids.add(task_entity.id)
                continue

            task_entity = self.add_task(task)
            children_ids.add(task_entity.id)

        entity.fill_children_ids(children_ids)

    def get_entity_children(self, entity, allow_query=True):
        children_ids = entity.get_children_ids(allow_query=False)
        if children_ids is not UNKNOWN_VALUE:
            return entity.get_children()

        if children_ids is UNKNOWN_VALUE and not allow_query:
            return UNKNOWN_VALUE

        self._query_entity_children(entity)

        return entity.get_children()

    def delete_entity(self, entity):
        parent_id = entity.parent_id
        if parent_id is None:
            return

        parent = self._entities_by_id.get(parent_id)
        if parent is not None:
            parent.remove_child(entity.id)

    def reset_immutable_for_hierarchy_cache(
        self, entity_id, bottom_to_top=True
    ):
        if bottom_to_top is None or entity_id is None:
            return

        reset_queue = collections.deque()
        reset_queue.append(entity_id)
        if bottom_to_top:
            while reset_queue:
                entity_id = reset_queue.popleft()
                entity = self.get_entity_by_id(entity_id)
                if entity is None:
                    continue
                entity.reset_immutable_for_hierarchy_cache(None)
                reset_queue.append(entity.parent_id)
        else:
            while reset_queue:
                entity_id = reset_queue.popleft()
                entity = self.get_entity_by_id(entity_id)
                if entity is None:
                    continue
                entity.reset_immutable_for_hierarchy_cache(None)
                for child in self._entities_by_parent_id[entity.id]:
                    reset_queue.append(child.id)

    def fill_project_from_server(self):
        """Query project data from server and create project entity.

        This method will invalidate previous object of Project entity.

        Returns:
            ProjectEntity: Entity that was updated with server data.

        Raises:
            ValueError: When project was not found on server.
        """

        project_name = self.project_name
        project = self._connection.get_project(
            project_name,
            own_attributes=True
        )
        if not project:
            raise ValueError(
                "Project \"{}\" was not found.".format(project_name)
            )

        self._project_entity = ProjectEntity(
            project["code"],
            parent_id=PROJECT_PARENT_ID,
            entity_id=project["name"],
            library=project["library"],
            folder_types=project["folderTypes"],
            task_types=project["taskTypes"],
            statuses=project["statuses"],
            name=project["name"],
            attribs=project["ownAttrib"],
            data=project["data"],
            active=project["active"],
            entity_hub=self
        )
        self.add_entity(self._project_entity)
        return self._project_entity

    def _get_folder_fields(self):
        folder_fields = set(
            self._connection.get_default_fields_for_type("folder")
        )
        folder_fields.add("hasProducts")
        if self._allow_data_changes:
            folder_fields.add("data")
        return folder_fields

    def query_entities_from_server(self):
        """Query whole project at once."""

        project_entity = self.fill_project_from_server()

        folder_fields = self._get_folder_fields()

        folders = self._connection.get_folders(
            project_entity.name,
            fields=folder_fields,
            own_attributes=True
        )
        tasks = self._connection.get_tasks(
            project_entity.name,
            own_attributes=True
        )
        folders_by_parent_id = collections.defaultdict(list)
        for folder in folders:
            parent_id = folder["parentId"]
            folders_by_parent_id[parent_id].append(folder)

        tasks_by_parent_id = collections.defaultdict(list)
        for task in tasks:
            parent_id = task["folderId"]
            tasks_by_parent_id[parent_id].append(task)

        lock_queue = collections.deque()
        hierarchy_queue = collections.deque()
        hierarchy_queue.append((None, project_entity))
        while hierarchy_queue:
            item = hierarchy_queue.popleft()
            parent_id, parent_entity = item

            lock_queue.append(parent_entity)

            children_ids = set()
            for folder in folders_by_parent_id[parent_id]:
                folder_entity = self.add_folder(folder)
                children_ids.add(folder_entity.id)
                folder_entity.has_published_content = folder["hasProducts"]
                hierarchy_queue.append((folder_entity.id, folder_entity))

            for task in tasks_by_parent_id[parent_id]:
                task_entity = self.add_task(task)
                lock_queue.append(task_entity)
                children_ids.add(task_entity.id)

            parent_entity.fill_children_ids(children_ids)

        # Lock entities when all are added to hub
        # - lock only entities added in this method
        while lock_queue:
            entity = lock_queue.popleft()
            entity.lock()

    def lock(self):
        if self._project_entity is None:
            return

        for entity in self._entities_by_id.values():
            entity.lock()

    def _get_top_entities(self):
        all_ids = set(self._entities_by_id.keys())
        return [
            entity
            for entity in self._entities_by_id.values()
            if entity.parent_id not in all_ids
        ]

    def _split_entities(self):
        top_entities = self._get_top_entities()
        entities_queue = collections.deque(top_entities)
        removed_entity_ids = []
        created_entity_ids = []
        other_entity_ids = []
        while entities_queue:
            entity = entities_queue.popleft()
            removed = entity.removed
            if removed:
                removed_entity_ids.append(entity.id)
            elif entity.created:
                created_entity_ids.append(entity.id)
            else:
                other_entity_ids.append(entity.id)

            for child in tuple(self._entities_by_parent_id[entity.id]):
                if removed:
                    self.unset_entity_parent(child.id, entity.id)
                entities_queue.append(child)
        return created_entity_ids, other_entity_ids, removed_entity_ids

    def _get_update_body(self, entity, changes=None):
        if changes is None:
            changes = entity.changes

        if not changes:
            return None
        return {
            "type": "update",
            "entityType": entity.entity_type,
            "entityId": entity.id,
            "data": changes
        }

    def _get_create_body(self, entity):
        return {
            "type": "create",
            "entityType": entity.entity_type,
            "entityId": entity.id,
            "data": entity.to_create_body_data()
        }

    def _get_delete_body(self, entity):
        return {
            "type": "delete",
            "entityType": entity.entity_type,
            "entityId": entity.id
        }

    def _pre_commit_types_changes(
        self, project_changes, orig_types, changes_key, post_changes
    ):
        """Compare changes of types on a project.

        Compare old and new types. Change project changes content if some old
        types were removed. In that case the  final change of types will
        happen when all other entities have changed.

        Args:
            project_changes (dict[str, Any]): Project changes.
            orig_types (list[dict[str, Any]]): Original types.
            changes_key (Literal[folderTypes, taskTypes]): Key of type changes
                in project changes.
            post_changes (dict[str, Any]): An object where post changes will
                be stored.
        """

        if changes_key not in project_changes:
            return

        new_types = project_changes[changes_key]

        orig_types_by_name = {
            type_info["name"]: type_info
            for type_info in orig_types
        }
        new_names = {
            type_info["name"]
            for type_info in new_types
        }
        diff_names = set(orig_types_by_name) - new_names
        if not diff_names:
            return

        # Create copy of folder type changes to post changes
        #   - post changes will be commited at the end
        post_changes[changes_key] = copy.deepcopy(new_types)

        for type_name in diff_names:
            new_types.append(orig_types_by_name[type_name])

    def _pre_commit_project(self):
        """Some project changes cannot be committed before hierarchy changes.

        It is not possible to change folder types or task types if there are
        existing hierarchy items using the removed types. For that purposes
        is first committed union of all old and new types and post changes
        are prepared when all existing entities are changed.

        Returns:
            dict[str, Any]: Changes that will be committed after hierarchy
                changes.
        """

        project_changes = self.project_entity.changes

        post_changes = {}
        if not project_changes:
            return post_changes

        self._pre_commit_types_changes(
            project_changes,
            self.project_entity.get_orig_folder_types(),
            "folderType",
            post_changes
        )
        self._pre_commit_types_changes(
            project_changes,
            self.project_entity.get_orig_task_types(),
            "taskType",
            post_changes
        )
        self._connection.update_project(self.project_name, **project_changes)
        return post_changes

    def commit_changes(self):
        """Commit any changes that happened on entities.

        Todos:
            Use Operations Session instead of known operations body.
        """

        post_project_changes = self._pre_commit_project()
        self.project_entity.lock()

        project_changes = self.project_entity.changes
        if project_changes:
            response = self._connection.patch(
                "projects/{}".format(self.project_name),
                **project_changes
            )
            response.raise_for_status()

        self.project_entity.lock()

        operations_body = []

        created_entity_ids, other_entity_ids, removed_entity_ids = (
            self._split_entities()
        )
        processed_ids = set()
        for entity_id in other_entity_ids:
            if entity_id in processed_ids:
                continue

            entity = self._entities_by_id[entity_id]
            changes = entity.changes
            processed_ids.add(entity_id)
            if not changes:
                continue

            bodies = [self._get_update_body(entity, changes)]
            # Parent was created and was not yet added to operations body
            parent_queue = collections.deque()
            parent_queue.append(entity.parent_id)
            while parent_queue:
                # Make sure entity's parents are created
                parent_id = parent_queue.popleft()
                if (
                    parent_id is UNKNOWN_VALUE
                    or parent_id in processed_ids
                    or parent_id not in created_entity_ids
                ):
                    continue

                parent = self._entities_by_id.get(parent_id)
                processed_ids.add(parent.id)
                bodies.append(self._get_create_body(parent))
                parent_queue.append(parent.id)

            operations_body.extend(reversed(bodies))

        for entity_id in created_entity_ids:
            if entity_id in processed_ids:
                continue
            entity = self._entities_by_id[entity_id]
            processed_ids.add(entity_id)
            operations_body.append(self._get_create_body(entity))

        for entity_id in reversed(removed_entity_ids):
            if entity_id in processed_ids:
                continue

            entity = self._entities_by_id.pop(entity_id)
            parent_children = self._entities_by_parent_id[entity.parent_id]
            if entity in parent_children:
                parent_children.remove(entity)

            if not entity.created:
                operations_body.append(self._get_delete_body(entity))

        self._connection.send_batch_operations(
            self.project_name, operations_body
        )
        if post_project_changes:
            self._connection.update_project(
                self.project_name, **post_project_changes)

        self.lock()


class AttributeValue(object):
    def __init__(self, value):
        self._value = value
        self._origin_value = copy.deepcopy(value)

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value

    value = property(get_value, set_value)

    @property
    def changed(self):
        return self._value != self._origin_value

    def lock(self):
        self._origin_value = copy.deepcopy(self._value)


class Attributes(object):
    """Object representing attribs of entity.

    Todos:
        This could be enhanced to know attribute schema and validate values
        based on the schema.

    Args:
        attrib_keys (Iterable[str]): Keys that are available in attribs of the
            entity.
        values (Union[None, Dict[str, Any]]): Values of attributes.
    """

    def __init__(self, attrib_keys, values=UNKNOWN_VALUE):
        if values in (UNKNOWN_VALUE, None):
            values = {}
        self._attributes = {
            key: AttributeValue(values.get(key))
            for key in attrib_keys
        }

    def __contains__(self, key):
        return key in self._attributes

    def __getitem__(self, key):
        return self._attributes[key].value

    def __setitem__(self, key, value):
        self._attributes[key].set_value(value)

    def __iter__(self):
        for key in self._attributes:
            yield key

    def keys(self):
        return self._attributes.keys()

    def values(self):
        for attribute in self._attributes.values():
            yield attribute.value

    def items(self):
        for key, attribute in self._attributes.items():
            yield key, attribute.value

    def get(self, key, default=None):
        """Get value of attribute.

        Args:
            key (str): Attribute name.
            default (Any): Default value to return when attribute was not
                found.
        """

        attribute = self._attributes.get(key)
        if attribute is None:
            return default
        return attribute.value

    def set(self, key, value):
        """Change value of attribute.

        Args:
            key (str): Attribute name.
            value (Any): New value of the attribute.
        """

        self[key] = value

    def get_attribute(self, key):
        """Access to attribute object.

        Args:
            key (str): Name of attribute.

        Returns:
            AttributeValue: Object of attribute value.

        Raises:
            KeyError: When attribute is not available.
        """

        return self._attributes[key]

    def lock(self):
        for attribute in self._attributes.values():
            attribute.lock()

    @property
    def changes(self):
        """Attribute value changes.

        Returns:
            Dict[str, Any]: Key mapping with new values.
        """

        return {
            attr_key: attribute.value
            for attr_key, attribute in self._attributes.items()
            if attribute.changed
        }

    def to_dict(self, ignore_none=True):
        output = {}
        for key, value in self.items():
            if (
                value is UNKNOWN_VALUE
                or (ignore_none and value is None)
            ):
                continue

            output[key] = value
        return output


@six.add_metaclass(ABCMeta)
class BaseEntity(object):
    """Object representation of entity from server which is capturing changes.

    All data on created object are expected as "current data" on server entity
    unless the entity has set 'created' to 'True'. So if new data should be
    stored to server entity then fill entity with server data first and
    then change them.

    Calling 'lock' method will mark entity as "saved" and all changes made on
    entity are set as "current data" on server.

    Args:
        entity_id (Union[str, None]): Id of the entity. New id is created if
            not passed.
        parent_id (Union[str, None]): Id of parent entity.
        name (str): Name of entity.
        attribs (Dict[str, Any]): Attribute values.
        data (Dict[str, Any]): Entity data (custom data).
        thumbnail_id (Union[str, None]): Id of entity's thumbnail.
        active (bool): Is entity active.
        entity_hub (EntityHub): Object of entity hub which created object of
            the entity.
        created (Optional[bool]): Entity is new. When 'None' is passed the
            value is defined based on value of 'entity_id'.
    """

    def __init__(
        self,
        entity_id=None,
        parent_id=UNKNOWN_VALUE,
        name=UNKNOWN_VALUE,
        attribs=UNKNOWN_VALUE,
        data=UNKNOWN_VALUE,
        thumbnail_id=UNKNOWN_VALUE,
        active=UNKNOWN_VALUE,
        entity_hub=None,
        created=None
    ):
        if entity_hub is None:
            raise ValueError("Missing required kwarg 'entity_hub'")

        self._entity_hub = entity_hub

        if created is None:
            created = entity_id is None

        entity_id = self._prepare_entity_id(entity_id)

        if data is None:
            data = {}

        children_ids = UNKNOWN_VALUE
        if created:
            children_ids = set()

        if not created and parent_id is UNKNOWN_VALUE:
            raise ValueError("Existing entity is missing parent id.")

        # These are public without any validation at this moment
        #   may change in future (e.g. name will have regex validation)
        self._entity_id = entity_id

        self._parent_id = parent_id
        self._name = name
        self.active = active
        self._created = created
        self._thumbnail_id = thumbnail_id
        self._attribs = Attributes(
            self._get_attributes_for_type(self.entity_type),
            attribs
        )
        self._data = data
        self._children_ids = children_ids

        self._orig_parent_id = parent_id
        self._orig_name = name
        self._orig_data = copy.deepcopy(data)
        self._orig_thumbnail_id = thumbnail_id
        self._orig_active = active

        self._immutable_for_hierarchy_cache = None

    def __repr__(self):
        return "<{} - {}>".format(self.__class__.__name__, self.id)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def _prepare_entity_id(self, entity_id):
        entity_id = convert_entity_id(entity_id)
        if entity_id is None:
            entity_id = create_entity_id()
        return entity_id

    @property
    def id(self):
        """Access to entity id under which is entity available on server.

        Returns:
            str: Entity id.
        """

        return self._entity_id

    @property
    def removed(self):
        return self._parent_id is None

    @property
    def orig_parent_id(self):
        return self._orig_parent_id

    @property
    def attribs(self):
        """Entity attributes based on server configuration.

        Returns:
            Attributes: Attributes object handling changes and values of
                attributes on entity.
        """

        return self._attribs

    @property
    def data(self):
        """Entity custom data that are not stored by any deterministic model.

        Be aware that 'data' can't be queried using GraphQl and cannot be
            updated partially.

        Returns:
            Dict[str, Any]: Custom data on entity.
        """

        return self._data

    @property
    def project_name(self):
        """Quick access to project from entity hub.

        Returns:
            str: Name of project under which entity lives.
        """

        return self._entity_hub.project_name

    @property
    @abstractmethod
    def entity_type(self):
        """Entity type coresponding to server.

        Returns:
            Literal[project, folder, task]: Entity type.
        """

        pass

    @property
    @abstractmethod
    def parent_entity_types(self):
        """Entity type coresponding to server.

        Returns:
            Iterable[str]: Possible entity types of parent.
        """

        pass

    @property
    @abstractmethod
    def changes(self):
        """Receive entity changes.

        Returns:
            Union[Dict[str, Any], None]: All values that have changed on
                entity. New entity must return None.
        """

        pass

    @classmethod
    @abstractmethod
    def from_entity_data(cls, entity_data, entity_hub):
        """Create entity based on queried data from server.

        Args:
            entity_data (Dict[str, Any]): Entity data from server.
            entity_hub (EntityHub): Hub which handle the entity.

        Returns:
            BaseEntity: Object of the class.
        """

        pass

    @abstractmethod
    def to_create_body_data(self):
        """Convert object of entity to data for server on creation.

        Returns:
            Dict[str, Any]: Entity data.
        """

        pass

    @property
    def immutable_for_hierarchy(self):
        """Entity is immutable for hierarchy changes.

        Hierarchy changes can be considered as change of name or parents.

        Returns:
            bool: Entity is immutable for hierarchy changes.
        """

        if self._immutable_for_hierarchy_cache is not None:
            return self._immutable_for_hierarchy_cache

        immutable_for_hierarchy = self._immutable_for_hierarchy
        if immutable_for_hierarchy is not None:
            self._immutable_for_hierarchy_cache = immutable_for_hierarchy
            return self._immutable_for_hierarchy_cache

        for child in self._entity_hub.get_entity_children(self):
            if child.immutable_for_hierarchy:
                self._immutable_for_hierarchy_cache = True
                return self._immutable_for_hierarchy_cache

        self._immutable_for_hierarchy_cache = False
        return self._immutable_for_hierarchy_cache

    @property
    def _immutable_for_hierarchy(self):
        """Override this method to define if entity object is immutable.

        This property was added to define immutable state of Folder entities
        which is used in property 'immutable_for_hierarchy'.

        Returns:
            Union[bool, None]: Bool to explicitly telling if is immutable or
                not otherwise None.
        """

        return None

    @property
    def has_cached_immutable_hierarchy(self):
        return self._immutable_for_hierarchy_cache is not None

    def reset_immutable_for_hierarchy_cache(self, bottom_to_top=True):
        """Clear cache of immutable hierarchy property.

        This is used when entity changed parent or a child was added.

        Args:
            bottom_to_top (bool): Reset cache from top hierarchy to bottom or
                from bottom hierarchy to top.
        """

        self._immutable_for_hierarchy_cache = None
        self._entity_hub.reset_immutable_for_hierarchy_cache(
            self.id, bottom_to_top
        )

    def _get_default_changes(self):
        """Collect changes of common data on entity.

        Returns:
            Dict[str, Any]: Changes on entity. Key and it's new value.
        """

        changes = {}
        if self._orig_name != self._name:
            changes["name"] = self._name

        if self._entity_hub.allow_data_changes:
            if (
                self._data is not UNKNOWN_VALUE
                and self._orig_data != self._data
            ):
                changes["data"] = self._data

        if self._orig_thumbnail_id != self._thumbnail_id:
            changes["thumbnailId"] = self._thumbnail_id

        if self._orig_active != self.active:
            changes["active"] = self.active

        attrib_changes = self.attribs.changes
        if attrib_changes:
            changes["attrib"] = attrib_changes
        return changes

    def _get_attributes_for_type(self, entity_type):
        return self._entity_hub.get_attributes_for_type(entity_type)

    def lock(self):
        """Lock entity as 'saved' so all changes are discarded."""

        self._orig_parent_id = self._parent_id
        self._orig_name = self._name
        self._orig_data = copy.deepcopy(self._data)
        self._orig_thumbnail_id = self.thumbnail_id
        self._attribs.lock()

        self._immutable_for_hierarchy_cache = None
        self._created = False

    def _get_entity_by_id(self, entity_id):
        return self._entity_hub.get_entity_by_id(entity_id)

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    name = property(get_name, set_name)

    def get_parent_id(self):
        """Parent entity id.

        Returns:
            Union[str, None]: Id of parent entity or none if is not set.
        """

        return self._parent_id

    def set_parent_id(self, parent_id):
        """Change parent by id.

        Args:
            parent_id (Union[str, None]): Id of new parent for entity.

        Raises:
            ValueError: If parent was not found by id.
            TypeError: If validation of parent does not pass.
        """

        if parent_id != self._parent_id:
            orig_parent_id = self._parent_id
            self._parent_id = parent_id
            self._entity_hub.set_entity_parent(
                self.id, parent_id, orig_parent_id
            )

    parent_id = property(get_parent_id, set_parent_id)

    def get_parent(self, allow_query=True):
        """Parent entity.

        Returns:
            Union[BaseEntity, None]: Parent object.
        """

        parent = self._entity_hub.get_entity_by_id(self._parent_id)
        if parent is not None:
            return parent

        if not allow_query:
            return self._parent_id

        if self._parent_id is UNKNOWN_VALUE:
            return self._parent_id

        return self._entity_hub.get_or_query_entity_by_id(
            self._parent_id, self.parent_entity_types
        )

    def set_parent(self, parent):
        """Change parent object.

        Args:
            parent (BaseEntity): New parent for entity.

        Raises:
            TypeError: If validation of parent does not pass.
        """

        parent_id = None
        if parent is not None:
            parent_id = parent.id
        self._entity_hub.set_entity_parent(self.id, parent_id)

    parent = property(get_parent, set_parent)

    def get_children_ids(self, allow_query=True):
        """Access to children objects.

        Todos:
            Children should be maybe handled by EntityHub instead of entities
                themselves. That would simplify 'set_entity_parent',
                'unset_entity_parent' and other logic related to changing
                hierarchy.

        Returns:
            Union[List[str], Type[UNKNOWN_VALUE]]: Children iterator.
        """

        if self._children_ids is UNKNOWN_VALUE:
            if not allow_query:
                return self._children_ids
            self._entity_hub.get_entity_children(self, True)
        return set(self._children_ids)

    children_ids = property(get_children_ids)

    def get_children(self, allow_query=True):
        """Access to children objects.

        Returns:
            Union[List[BaseEntity], Type[UNKNOWN_VALUE]]: Children iterator.
        """

        if self._children_ids is UNKNOWN_VALUE:
            if not allow_query:
                return self._children_ids
            return self._entity_hub.get_entity_children(self, True)

        return [
            self._entity_hub.get_entity_by_id(children_id)
            for children_id in self._children_ids
        ]

    children = property(get_children)

    def add_child(self, child):
        """Add child entity.

        Args:
            child (BaseEntity): Child object to add.

        Raises:
            TypeError: When child object has invalid type to be children.
        """

        child_id = child
        if isinstance(child_id, BaseEntity):
            child_id = child.id

        if self._children_ids is not UNKNOWN_VALUE:
            self._children_ids.add(child_id)

        self._entity_hub.set_entity_parent(child_id, self.id)

    def remove_child(self, child):
        """Remove child entity.

        Is ignored if child is not in children.

        Args:
            child (Union[str, BaseEntity]): Child object or child id to remove.
        """

        child_id = child
        if isinstance(child_id, BaseEntity):
            child_id = child.id

        if self._children_ids is not UNKNOWN_VALUE:
            self._children_ids.discard(child_id)
        self._entity_hub.unset_entity_parent(child_id, self.id)

    def get_thumbnail_id(self):
        """Thumbnail id of entity.

        Returns:
            Union[str, None]: Id of parent entity or none if is not set.
        """

        return self._thumbnail_id

    def set_thumbnail_id(self, thumbnail_id):
        """Change thumbnail id.

        Args:
            thumbnail_id (Union[str, None]): Id of thumbnail for entity.
        """

        self._thumbnail_id = thumbnail_id

    thumbnail_id = property(get_thumbnail_id, set_thumbnail_id)

    @property
    def created(self):
        """Entity is new.

        Returns:
            bool: Entity is newly created.
        """

        return self._created

    def fill_children_ids(self, children_ids):
        """Fill children ids on entity.

        Warning:
            This is not an api call but is called from entity hub.
        """

        self._children_ids = set(children_ids)


class ProjectStatus:
    """Project status class.

    Args:
        name (str): Name of the status. e.g. 'In progress'
        short_name (Optional[str]): Short name of the status. e.g. 'IP'
        state (Optional[Literal[not_started, in_progress, done, blocked]]): A
            state of the status.
        icon (Optional[str]): Icon of the status. e.g. 'play_arrow'.
        color (Optional[str]): Color of the status. e.g. '#eeeeee'.
        index (Optional[int]): Index of the status.
        project_statuses (Optional[_ProjectStatuses]): Project statuses
            wrapper.
    """

    valid_states = ("not_started", "in_progress", "done", "blocked")
    color_regex = re.compile(r"#([a-f0-9]{6})$")
    default_state = "in_progress"
    default_color = "#eeeeee"

    def __init__(
        self,
        name,
        short_name=None,
        state=None,
        icon=None,
        color=None,
        index=None,
        project_statuses=None,
        is_new=None,
    ):
        short_name = short_name or ""
        icon = icon or ""
        state = state or self.default_state
        color = color or self.default_color
        self._name = name
        self._short_name = short_name
        self._icon = icon
        self._slugified_name = None
        self._state = None
        self._color = None
        self.set_state(state)
        self.set_color(color)

        self._original_name = name
        self._original_short_name = short_name
        self._original_icon = icon
        self._original_state = state
        self._original_color = color
        self._original_index = index

        self._index = index
        self._project_statuses = project_statuses
        if is_new is None:
            is_new = index is None or project_statuses is None
        self._is_new = is_new

    def __str__(self):
        short_name = ""
        if self.short_name:
            short_name = "({})".format(self.short_name)
        return "<{} {}{}>".format(
            self.__class__.__name__, self.name, short_name
        )

    def __repr__(self):
        return str(self)

    def __getitem__(self, key):
        if key in {
            "name", "short_name", "icon", "state", "color", "slugified_name"
        }:
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key in {"name", "short_name", "icon", "state", "color"}:
            return setattr(self, key, value)
        raise KeyError(key)

    def lock(self):
        """Lock status.

        Changes were commited and current values are now the original values.
        """

        self._is_new = False
        self._original_name = self.name
        self._original_short_name = self.short_name
        self._original_icon = self.icon
        self._original_state = self.state
        self._original_color = self.color
        self._original_index = self.index

    @staticmethod
    def slugify_name(name):
        """Slugify status name for name comparison.

        Args:
            name (str): Name of the status.

        Returns:
            str: Slugified name.
        """

        return slugify_string(name.lower())

    def get_project_statuses(self):
        """Internal logic method.

        Returns:
            _ProjectStatuses: Project statuses object.
        """

        return self._project_statuses

    def set_project_statuses(self, project_statuses):
        """Internal logic method to change parent object.

        Args:
            project_statuses (_ProjectStatuses): Project statuses object.
        """

        self._project_statuses = project_statuses

    def unset_project_statuses(self, project_statuses):
        """Internal logic method to unset parent object.

        Args:
            project_statuses (_ProjectStatuses): Project statuses object.
        """

        if self._project_statuses is project_statuses:
            self._project_statuses = None
            self._index = None

    @property
    def changed(self):
        """Status has changed.

        Returns:
            bool: Status has changed.
        """

        return (
            self._is_new
            or self._original_name != self._name
            or self._original_short_name != self._short_name
            or self._original_index != self._index
            or self._original_state != self._state
            or self._original_icon != self._icon
            or self._original_color != self._color
        )

    def delete(self):
        """Remove status from project statuses object."""

        if self._project_statuses is not None:
            self._project_statuses.remove(self)

    def get_index(self):
        """Get index of status.

        Returns:
            Union[int, None]: Index of status or None if status is not under
                project.
        """

        return self._index

    def set_index(self, index, **kwargs):
        """Change status index.

        Returns:
            Union[int, None]: Index of status or None if status is not under
                project.
        """

        if kwargs.get("from_parent"):
            self._index = index
        else:
            self._project_statuses.set_status_index(self, index)

    def get_name(self):
        """Status name.

        Returns:
            str: Status name.
        """

        return self._name

    def set_name(self, name):
        """Change status name.

        Args:
            name (str): New status name.
        """

        if not isinstance(name, six.string_types):
            raise TypeError("Name must be a string.")
        if name == self._name:
            return
        self._name = name
        self._slugified_name = None

    def get_short_name(self):
        """Status short name 3 letters tops.

        Returns:
            str: Status short name.
        """

        return self._short_name

    def set_short_name(self, short_name):
        """Change status short name.

        Args:
            short_name (str): New status short name. 3 letters tops.
        """

        if not isinstance(short_name, six.string_types):
            raise TypeError("Short name must be a string.")
        self._short_name = short_name

    def get_icon(self):
        """Name of icon to use for status.

        Returns:
            str: Name of the icon.
        """

        return self._icon

    def set_icon(self, icon):
        """Change status icon name.

        Args:
            icon (str): Name of the icon.
        """

        if icon is None:
            icon = ""
        if not isinstance(icon, six.string_types):
            raise TypeError("Icon name must be a string.")
        self._icon = icon

    @property
    def slugified_name(self):
        """Slugified and lowere status name.

        Can be used for comparison of existing statuses. e.g. 'In Progress'
            vs. 'in-progress'.

        Returns:
            str: Slugified and lower status name.
        """

        if self._slugified_name is None:
            self._slugified_name = self.slugify_name(self.name)
        return self._slugified_name

    def get_state(self):
        """Get state of project status.

        Return:
            Literal[not_started, in_progress, done, blocked]: General
                state of status.
        """

        return self._state

    def set_state(self, state):
        """Set color of project status.

        Args:
            state (Literal[not_started, in_progress, done, blocked]): General
                state of status.
        """

        if state not in self.valid_states:
            raise ValueError("Invalid state '{}'".format(str(state)))
        self._state = state

    def get_color(self):
        """Get color of project status.

        Returns:
            str: Status color.
        """

        return self._color

    def set_color(self, color):
        """Set color of project status.

        Args:
            color (str): Color in hex format. Example: '#ff0000'.
        """

        if not isinstance(color, six.string_types):
            raise TypeError(
                "Color must be string got '{}'".format(type(color)))
        color = color.lower()
        if self.color_regex.fullmatch(color) is None:
            raise ValueError("Invalid color value '{}'".format(color))
        self._color = color

    name = property(get_name, set_name)
    short_name = property(get_short_name, set_short_name)
    project_statuses = property(get_project_statuses, set_project_statuses)
    index = property(get_index, set_index)
    state = property(get_state, set_state)
    color = property(get_color, set_color)
    icon = property(get_icon, set_icon)

    def _validate_other_p_statuses(self, other):
        """Validate if other status can be used for move.

        To be able to work with other status, and position them in relation,
        they must belong to same existing object of '_ProjectStatuses'.

        Args:
            other (ProjectStatus): Other status to validate.
        """

        o_project_statuses = other.project_statuses
        m_project_statuses = self.project_statuses
        if o_project_statuses is None and m_project_statuses is None:
            raise ValueError("Both statuses are not assigned to a project.")

        missing_status = None
        if o_project_statuses is None:
            missing_status = other
        elif m_project_statuses is None:
            missing_status = self
        if missing_status is not None:
            raise ValueError(
                "Status '{}' is not assigned to a project.".format(
                    missing_status.name))
        if m_project_statuses is not o_project_statuses:
            raise ValueError(
                "Statuse are assigned to different projects."
                " Cannot execute move."
            )

    def move_before(self, other):
        """Move status before other status.

        Args:
            other (ProjectStatus): Status to move before.
        """

        self._validate_other_p_statuses(other)
        self._project_statuses.set_status_index(self, other.index)

    def move_after(self, other):
        """Move status after other status.

        Args:
            other (ProjectStatus): Status to move after.
        """

        self._validate_other_p_statuses(other)
        self._project_statuses.set_status_index(self, other.index + 1)

    def to_data(self):
        """Convert status to data.

        Returns:
            dict[str, str]: Status data.
        """

        output = {
            "name": self.name,
            "shortName": self.short_name,
            "state": self.state,
            "icon": self.icon,
            "color": self.color,
        }
        if (
            not self._is_new
            and self._original_name
            and self.name != self._original_name
        ):
            output["original_name"] = self._original_name
        return output

    @classmethod
    def from_data(cls, data, index=None, project_statuses=None):
        """Create project status from data.

        Args:
            data (dict[str, str]): Status data.
            index (Optional[int]): Status index.
            project_statuses (Optional[ProjectStatuses]): Project statuses
                object which wraps the status for a project.
        """

        return cls(
            data["name"],
            data.get("shortName", data.get("short_name")),
            data.get("state"),
            data.get("icon"),
            data.get("color"),
            index=index,
            project_statuses=project_statuses
        )


class _ProjectStatuses:
    """Wrapper for project statuses.

    Supports basic methods to add, change or remove statuses from a project.

    To add new statuses use 'create' or 'add_status' methods. To change
        statuses receive them by one of the getter methods and change their
        values.

    Todos:
        Validate if statuses are duplicated.
    """

    def __init__(self, statuses):
        self._statuses = [
            ProjectStatus.from_data(status, idx, self)
            for idx, status in enumerate(statuses)
        ]
        self._orig_status_length = len(self._statuses)
        self._set_called = False

    def __len__(self):
        return len(self._statuses)

    def __iter__(self):
        """Iterate over statuses.

        Yields:
            ProjectStatus: Project status.
        """

        for status in self._statuses:
            yield status

    def create(
        self,
        name,
        short_name=None,
        state=None,
        icon=None,
        color=None,
    ):
        """Create project status.

        Args:
            name (str): Name of the status. e.g. 'In progress'
            short_name (Optional[str]): Short name of the status. e.g. 'IP'
            state (Optional[Literal[not_started, in_progress, done, blocked]]): A
                state of the status.
            icon (Optional[str]): Icon of the status. e.g. 'play_arrow'.
            color (Optional[str]): Color of the status. e.g. '#eeeeee'.

        Returns:
            ProjectStatus: Created project status.
        """

        status = ProjectStatus(
            name, short_name, state, icon, color, is_new=True
        )
        self.append(status)
        return status

    def lock(self):
        """Lock statuses.

        Changes were commited and current values are now the original values.
        """

        self._orig_status_length = len(self._statuses)
        self._set_called = False
        for status in self._statuses:
            status.lock()

    def to_data(self):
        """Convert to project statuses data."""

        return [
            status.to_data()
            for status in self._statuses
        ]

    def set(self, statuses):
        """Explicitly override statuses.

        This method does not handle if statuses changed or not.

        Args:
            statuses (list[dict[str, str]]): List of statuses data.
        """

        self._set_called = True
        self._statuses = [
            ProjectStatus.from_data(status, idx, self)
            for idx, status in enumerate(statuses)
        ]

    @property
    def changed(self):
        """Statuses have changed.

        Returns:
            bool: True if statuses changed, False otherwise.
        """

        if self._set_called:
            return True

        # Check if status length changed
        #   - when all statuses are removed it is a changed
        if self._orig_status_length != len(self._statuses):
            return True
        # Go through all statuses and check if any of them changed
        for status in self._statuses:
            if status.changed:
                return True
        return False

    def get(self, name, default=None):
        """Get status by name.

        Args:
            name (str): Status name.
            default (Any): Default value of status is not found.

        Returns:
            Union[ProjectStatus, Any]: Status or default value.
        """

        return next(
            (
                status
                for status in self._statuses
                if status.name == name
            ),
            default
        )

    get_status_by_name = get

    def index(self, status, **kwargs):
        """Get status index.

        Args:
            status (ProjectStatus): Status to get index of.
            default (Optional[Any]): Default value if status is not found.

        Returns:
            Union[int, Any]: Status index.

        Raises:
            ValueError: If status is not found and default value is not
                defined.
        """

        output = next(
            (
                idx
                for idx, st in enumerate(self._statuses)
                if st is status
            ),
            None
        )
        if output is not None:
            return output

        if "default" in kwargs:
            return kwargs["default"]
        raise ValueError("Status '{}' not found".format(status.name))

    def get_status_by_slugified_name(self, name):
        """Get status by slugified name.

        Args:
            name (str): Status name. Is slugified before search.

        Returns:
            Union[ProjectStatus, None]: Status or None if not found.
        """

        slugified_name = ProjectStatus.slugify_name(name)
        return next(
            (
                status
                for status in self._statuses
                if status.slugified_name == slugified_name
            ),
            None
        )

    def remove_by_name(self, name, ignore_missing=False):
        """Remove status by name.

        Args:
            name (str): Status name.
            ignore_missing (Optional[bool]): If True, no error is raised if
                status is not found.

        Returns:
            ProjectStatus: Removed status.
        """

        matching_status = self.get(name)
        if matching_status is None:
            if ignore_missing:
                return
            raise ValueError(
                "Status '{}' not found in project".format(name))
        return self.remove(matching_status)

    def remove(self, status, ignore_missing=False):
        """Remove status.

        Args:
            status (ProjectStatus): Status to remove.
            ignore_missing (Optional[bool]): If True, no error is raised if
                status is not found.

        Returns:
            Union[ProjectStatus, None]: Removed status.
        """

        index = self.index(status, default=None)
        if index is None:
            if ignore_missing:
                return None
            raise ValueError("Status '{}' not in project".format(status))

        return self.pop(index)

    def pop(self, index):
        """Remove status by index.

        Args:
            index (int): Status index.

        Returns:
            ProjectStatus: Removed status.
        """

        status = self._statuses.pop(index)
        status.unset_project_statuses(self)
        for st in self._statuses[index:]:
            st.set_index(st.index - 1, from_parent=True)
        return status

    def insert(self, index, status):
        """Insert status at index.

        Args:
            index (int): Status index.
            status (Union[ProjectStatus, dict[str, str]]): Status to insert.
                Can be either status object or status data.

        Returns:
            ProjectStatus: Inserted status.
        """

        if not isinstance(status, ProjectStatus):
            status = ProjectStatus.from_data(status)

        start_index = index
        end_index = len(self._statuses) + 1
        matching_index = self.index(status, default=None)
        if matching_index is not None:
            if matching_index == index:
                status.set_index(index, from_parent=True)
                return

            self._statuses.pop(matching_index)
            if matching_index < index:
                start_index = matching_index
                end_index = index + 1
            else:
                end_index -= 1

        status.set_project_statuses(self)
        self._statuses.insert(index, status)
        for idx, st in enumerate(self._statuses[start_index:end_index]):
            st.set_index(start_index + idx, from_parent=True)
        return status

    def append(self, status):
        """Add new status to the end of the list.

        Args:
            status (Union[ProjectStatus, dict[str, str]]): Status to insert.
                Can be either status object or status data.

        Returns:
            ProjectStatus: Inserted status.
        """

        return self.insert(len(self._statuses), status)

    def set_status_index(self, status, index):
        """Set status index.

        Args:
            status (ProjectStatus): Status to set index.
            index (int): New status index.
        """

        return self.insert(index, status)


class ProjectEntity(BaseEntity):
    """Entity representing project on AYON server.

    Args:
        project_code (str): Project code.
        library (bool): Is project library project.
        folder_types (list[dict[str, Any]]): Folder types definition.
        task_types (list[dict[str, Any]]): Task types definition.
        entity_id (Optional[str]): Id of the entity. New id is created if
            not passed.
        parent_id (Union[str, None]): Id of parent entity.
        name (str): Name of entity.
        attribs (Dict[str, Any]): Attribute values.
        data (Dict[str, Any]): Entity data (custom data).
        thumbnail_id (Union[str, None]): Id of entity's thumbnail.
        active (bool): Is entity active.
        entity_hub (EntityHub): Object of entity hub which created object of
            the entity.
        created (Optional[bool]): Entity is new. When 'None' is passed the
            value is defined based on value of 'entity_id'.
    """

    entity_type = "project"
    parent_entity_types = []
    # TODO These are hardcoded but maybe should be used from server???
    default_folder_type_icon = "folder"
    default_task_type_icon = "task_alt"

    def __init__(
        self,
        project_code,
        library,
        folder_types,
        task_types,
        statuses,
        *args,
        **kwargs
    ):
        super(ProjectEntity, self).__init__(*args, **kwargs)

        self._project_code = project_code
        self._library_project = library
        self._folder_types = folder_types
        self._task_types = task_types
        self._statuses_obj = _ProjectStatuses(statuses)

        self._orig_project_code = project_code
        self._orig_library_project = library
        self._orig_folder_types = copy.deepcopy(folder_types)
        self._orig_task_types = copy.deepcopy(task_types)
        self._orig_statuses = copy.deepcopy(statuses)

    def _prepare_entity_id(self, entity_id):
        if entity_id != self.project_name:
            raise ValueError(
                "Unexpected entity id value \"{}\". Expected \"{}\"".format(
                    entity_id, self.project_name))
        return entity_id

    def get_parent(self, *args, **kwargs):
        return None

    def set_parent(self, parent):
        raise ValueError(
            "Parent of project cannot be set to {}".format(parent)
        )

    parent = property(get_parent, set_parent)

    def get_orig_folder_types(self):
        return copy.deepcopy(self._orig_folder_types)

    def get_folder_types(self):
        return copy.deepcopy(self._folder_types)

    def set_folder_types(self, folder_types):
        new_folder_types = []
        for folder_type in folder_types:
            if "icon" not in folder_type:
                folder_type["icon"] = self.default_folder_type_icon
            new_folder_types.append(folder_type)
        self._folder_types = new_folder_types

    def get_orig_task_types(self):
        return copy.deepcopy(self._orig_task_types)

    def get_task_types(self):
        return copy.deepcopy(self._task_types)

    def set_task_types(self, task_types):
        new_task_types = []
        for task_type in task_types:
            if "icon" not in task_type:
                task_type["icon"] = self.default_task_type_icon
            new_task_types.append(task_type)
        self._task_types = new_task_types

    def get_orig_statuses(self):
        return copy.deepcopy(self._orig_statuses)

    def get_statuses(self):
        return self._statuses_obj

    def set_statuses(self, statuses):
        self._statuses_obj.set(statuses)

    folder_types = property(get_folder_types, set_folder_types)
    task_types = property(get_task_types, set_task_types)
    statuses = property(get_statuses, set_statuses)

    def lock(self):
        super(ProjectEntity, self).lock()
        self._orig_folder_types = copy.deepcopy(self._folder_types)
        self._orig_task_types = copy.deepcopy(self._task_types)
        self._statuses_obj.lock()

    @property
    def changes(self):
        changes = self._get_default_changes()
        if self._orig_folder_types != self._folder_types:
            changes["folderTypes"] = self.get_folder_types()

        if self._orig_task_types != self._task_types:
            changes["taskTypes"] = self.get_task_types()

        if self._statuses_obj.changed:
            changes["statuses"] = self._statuses_obj.to_data()

        return changes

    @classmethod
    def from_entity_data(cls, project, entity_hub):
        return cls(
            project["code"],
            parent_id=PROJECT_PARENT_ID,
            entity_id=project["name"],
            library=project["library"],
            folder_types=project["folderTypes"],
            task_types=project["taskTypes"],
            name=project["name"],
            attribs=project["ownAttrib"],
            data=project["data"],
            active=project["active"],
            entity_hub=entity_hub
        )

    def to_create_body_data(self):
        raise NotImplementedError(
            "ProjectEntity does not support conversion to entity data"
        )


class FolderEntity(BaseEntity):
    """Entity representing a folder on AYON server.

    Args:
        folder_type (str): Type of folder. Folder type must be available in
            config of project folder types.
        entity_id (Union[str, None]): Id of the entity. New id is created if
            not passed.
        parent_id (Union[str, None]): Id of parent entity.
        name (str): Name of entity.
        attribs (Dict[str, Any]): Attribute values.
        data (Dict[str, Any]): Entity data (custom data).
        thumbnail_id (Union[str, None]): Id of entity's thumbnail.
        active (bool): Is entity active.
        label (Optional[str]): Folder label.
        path (Optional[str]): Folder path. Path consist of all parent names
            with slash('/') used as separator.
        entity_hub (EntityHub): Object of entity hub which created object of
            the entity.
        created (Optional[bool]): Entity is new. When 'None' is passed the
            value is defined based on value of 'entity_id'.
    """

    entity_type = "folder"
    parent_entity_types = ["folder", "project"]

    def __init__(self, folder_type, *args, label=None, path=None, **kwargs):
        super(FolderEntity, self).__init__(*args, **kwargs)
        # Autofill project as parent of folder if is not yet set
        # - this can be guessed only if folder was just created
        if self.created and self._parent_id is UNKNOWN_VALUE:
            self._parent_id = self.project_name

        self._folder_type = folder_type
        self._label = label

        self._orig_folder_type = folder_type
        self._orig_label = label
        # Know if folder has any products
        # - is used to know if folder allows hierarchy changes
        self._has_published_content = False
        self._path = path

    def get_folder_type(self):
        return self._folder_type

    def set_folder_type(self, folder_type):
        self._folder_type = folder_type

    folder_type = property(get_folder_type, set_folder_type)

    def get_label(self):
        return self._label

    def set_label(self, label):
        self._label = label

    label = property(get_label, set_label)

    def get_path(self, dynamic_value=True):
        if not dynamic_value:
            return self._path

        if self._path is None:
            parent = self.parent
            if parent.entity_type == "folder":
                parent_path = parent.path
                path = "/".join([parent_path, self.name])
            elif self._entity_hub.path_start_with_slash:
                path = "/{}".format(self.name)
            else:
                path = self.name
            self._path = path
        return self._path

    def reset_path(self):
        self._path = None
        self._entity_hub.folder_path_reseted(self.id)

    path = property(get_path)

    def get_has_published_content(self):
        return self._has_published_content

    def set_has_published_content(self, has_published_content):
        if self._has_published_content is has_published_content:
            return

        self._has_published_content = has_published_content
        # Reset immutable cache of parents
        self._entity_hub.reset_immutable_for_hierarchy_cache(self.id)

    has_published_content = property(
        get_has_published_content, set_has_published_content
    )

    @property
    def _immutable_for_hierarchy(self):
        if self.has_published_content:
            return True
        return None

    def lock(self):
        super(FolderEntity, self).lock()
        self._orig_folder_type = self._folder_type

    @property
    def changes(self):
        changes = self._get_default_changes()

        if self._orig_parent_id != self._parent_id:
            parent_id = self._parent_id
            if parent_id == self.project_name:
                parent_id = None
            changes["parentId"] = parent_id

        if self._orig_folder_type != self._folder_type:
            changes["folderType"] = self._folder_type

        label = self._label
        if self._name == label:
            label = None

        if label != self._orig_label:
            changes["label"] = label

        return changes

    @classmethod
    def from_entity_data(cls, folder, entity_hub):
        parent_id = folder["parentId"]
        if parent_id is None:
            parent_id = entity_hub.project_entity.id
        return cls(
            folder["folderType"],
            label=folder["label"],
            path=folder["path"],
            entity_id=folder["id"],
            parent_id=parent_id,
            name=folder["name"],
            data=folder.get("data"),
            attribs=folder["ownAttrib"],
            active=folder["active"],
            thumbnail_id=folder["thumbnailId"],
            created=False,
            entity_hub=entity_hub
        )

    def to_create_body_data(self):
        parent_id = self._parent_id
        if parent_id is UNKNOWN_VALUE:
            raise ValueError("Folder does not have set 'parent_id'")

        if parent_id == self.project_name:
            parent_id = None

        if not self.name or self.name is UNKNOWN_VALUE:
            raise ValueError("Folder does not have set 'name'")

        output = {
            "name": self.name,
            "folderType": self.folder_type,
            "parentId": parent_id,
        }
        attrib = self.attribs.to_dict()
        if attrib:
            output["attrib"] = attrib

        if self.active is not UNKNOWN_VALUE:
            output["active"] = self.active

        if self.thumbnail_id is not UNKNOWN_VALUE:
            output["thumbnailId"] = self.thumbnail_id

        if (
            self._entity_hub.allow_data_changes
            and self._data is not UNKNOWN_VALUE
        ):
            output["data"] = self._data
        return output


class TaskEntity(BaseEntity):
    """Entity representing a task on AYON server.

    Args:
        task_type (str): Type of task. Task type must be available in config
            of project task types.
        entity_id (Union[str, None]): Id of the entity. New id is created if
            not passed.
        parent_id (Union[str, None]): Id of parent entity.
        name (str): Name of entity.
        label (Optional[str]): Task label.
        attribs (Dict[str, Any]): Attribute values.
        data (Dict[str, Any]): Entity data (custom data).
        thumbnail_id (Union[str, None]): Id of entity's thumbnail.
        active (bool): Is entity active.
        entity_hub (EntityHub): Object of entity hub which created object of
            the entity.
        created (Optional[bool]): Entity is new. When 'None' is passed the
            value is defined based on value of 'entity_id'.
    """

    entity_type = "task"
    parent_entity_types = ["folder"]

    def __init__(self, task_type, *args, label=None, **kwargs):
        super(TaskEntity, self).__init__(*args, **kwargs)

        self._task_type = task_type
        self._label = label

        self._orig_task_type = task_type
        self._orig_label = label

        self._children_ids = set()

    def lock(self):
        super(TaskEntity, self).lock()
        self._orig_task_type = self._task_type

    def get_task_type(self):
        return self._task_type

    def set_task_type(self, task_type):
        self._task_type = task_type

    task_type = property(get_task_type, set_task_type)

    def get_label(self):
        return self._label

    def set_label(self, label):
        self._label = label

    label = property(get_label, set_label)

    def add_child(self, child):
        raise ValueError("Task does not support to add children")

    @property
    def changes(self):
        changes = self._get_default_changes()

        if self._orig_parent_id != self._parent_id:
            changes["folderId"] = self._parent_id

        if self._orig_task_type != self._task_type:
            changes["taskType"] = self._task_type

        label = self._label
        if self._name == label:
            label = None

        if label != self._orig_label:
            changes["label"] = label

        return changes

    @classmethod
    def from_entity_data(cls, task, entity_hub):
        return cls(
            task["taskType"],
            entity_id=task["id"],
            label=task["label"],
            parent_id=task["folderId"],
            name=task["name"],
            data=task.get("data"),
            attribs=task["ownAttrib"],
            active=task["active"],
            created=False,
            entity_hub=entity_hub
        )

    def to_create_body_data(self):
        if self.parent_id is UNKNOWN_VALUE:
            raise ValueError("Task does not have set 'parent_id'")

        output = {
            "name": self.name,
            "taskType": self.task_type,
            "folderId": self.parent_id,
            "attrib": self.attribs.to_dict(),
        }
        attrib = self.attribs.to_dict()
        if attrib:
            output["attrib"] = attrib

        if self.active is not UNKNOWN_VALUE:
            output["active"] = self.active

        if (
            self._entity_hub.allow_data_changes
            and self._data is not UNKNOWN_VALUE
        ):
            output["data"] = self._data
        return output
