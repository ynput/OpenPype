import re
import uuid
import copy
import collections
from abc import ABCMeta, abstractmethod, abstractproperty

import six
from bson.objectid import ObjectId
from pymongo import DeleteOne, InsertOne, UpdateOne

from .mongo import get_project_connection

REMOVED_VALUE = object()

CURRENT_PROJECT_SCHEMA = "openpype:project-3.0"
CURRENT_PROJECT_CONFIG_SCHEMA = "openpype:config-2.0"
CURRENT_ASSET_DOC_SCHEMA = "openpype:asset-3.0"
CURRENT_SUBSET_SCHEMA = "openpype:subset-3.0"
CURRENT_VERSION_SCHEMA = "openpype:version-3.0"
CURRENT_REPRESENTATION_SCHEMA = "openpype:representation-2.0"


def _create_or_convert_to_mongo_id(mongo_id):
    if mongo_id is None:
        return ObjectId()
    return ObjectId(mongo_id)


def new_project_document(
    project_name, project_code, config, data=None, entity_id=None
):
    if data is None:
        data = {}

    data["code"] = project_code

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "name": project_name,
        "type": CURRENT_PROJECT_SCHEMA,
        "data": data,
        "config": config
    }


def new_asset_document(
    name, project_id, parent_id, parents, data=None, entity_id=None
):
    if data is None:
        data = {}
    if parent_id is not None:
        parent_id = ObjectId(parent_id)
    data["visualParent"] = parent_id
    data["parents"] = parents

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "type": "asset",
        "name": name,
        "parent": ObjectId(project_id),
        "data": data,
        "schema": CURRENT_ASSET_DOC_SCHEMA
    }


def new_subset_document(name, family, asset_id, data=None, entity_id=None):
    if data is None:
        data = {}
    data["family"] = family
    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "schema": CURRENT_SUBSET_SCHEMA,
        "type": "subset",
        "name": name,
        "data": data,
        "parent": asset_id
    }


def new_version_doc(version, subset_id, data=None, entity_id=None):
    if data is None:
        data = {}

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "schema": CURRENT_VERSION_SCHEMA,
        "type": "version",
        "name": int(version),
        "parent": subset_id,
        "data": data
    }


def new_representation_doc(
    name, version_id, context, data=None, entity_id=None
):
    if data is None:
        data = {}

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "schema": CURRENT_REPRESENTATION_SCHEMA,
        "type": "representation",
        "parent": version_id,
        "name": name,
        "data": data,

        # Imprint shortcut to context for performance reasons.
        "context": context
    }


def _prepare_update_data(old_doc, new_doc, replace):
    changes = {}
    for key, value in new_doc.items():
        if key not in old_doc or value != old_doc[key]:
            changes[key] = value

    if replace:
        for key in old_doc.keys():
            if key not in new_doc:
                changes[key] = REMOVED_VALUE
    return changes


def prepare_subset_update_data(old_doc, new_doc, replace=True):
    return _prepare_update_data(old_doc, new_doc, replace)


def prepare_version_update_data(old_doc, new_doc, replace=True):
    return _prepare_update_data(old_doc, new_doc, replace)


def prepare_representation_update_data(old_doc, new_doc, replace=True):
    return _prepare_update_data(old_doc, new_doc, replace)


@six.add_metaclass(ABCMeta)
class AbstractOperation(object):
    """Base operation class."""

    def __init__(self, project_name, entity_type):
        self._project_name = project_name
        self._entity_type = entity_type
        self._id = str(uuid.uuid4())

    @property
    def project_name(self):
        return self._project_name

    @property
    def id(self):
        return self._id

    @property
    def entity_type(self):
        return self._entity_type

    @abstractproperty
    def operation_name(self):
        pass

    @abstractmethod
    def to_mongo_operation(self):
        pass

    def to_data(self):
        return {
            "id": self._id,
            "entity_type": self.entity_type,
            "project_name": self.project_name,
            "operation": self.operation_name
        }


class CreateOperation(AbstractOperation):
    operation_name = "create"

    def __init__(self, project_name, entity_type, data):
        super(CreateOperation, self).__init__(project_name, entity_type)

        if not data:
            data = {}
        else:
            data = copy.deepcopy(dict(data))

        if "_id" not in data:
            data["_id"] = ObjectId()
        else:
            data["_id"] = ObjectId(data["_id"])

        self._entity_id = data["_id"]
        self._data = data

    def __setitem__(self, key, value):
        self.set_value(key, value)

    def __getitem__(self, key):
        return self.data[key]

    def set_value(self, key, value):
        self.data[key] = value

    def get(self, key, *args, **kwargs):
        return self.data.get(key, *args, **kwargs)

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def data(self):
        return self._data

    def to_mongo_operation(self):
        return InsertOne(copy.deepcopy(self._data))

    def to_data(self):
        output = super(CreateOperation, self).to_data()
        output["data"] = copy.deepcopy(self.data)
        return output


class UpdateOperation(AbstractOperation):
    operation_name = "update"

    def __init__(self, project_name, entity_type, entity_id, update_data):
        super(UpdateOperation, self).__init__(project_name, entity_type)

        self._entity_id = ObjectId(entity_id)
        self._update_data = update_data

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def update_data(self):
        return self._update_data

    def to_mongo_operation(self):
        unset_data = {}
        set_data = {}
        for key, value in self._update_data.items():
            if value is REMOVED_VALUE:
                unset_data[key] = value
            else:
                set_data[key] = value

        op_data = {}
        if unset_data:
            op_data["$unset"] = unset_data
        if set_data:
            op_data["$set"] = set_data

        if not op_data:
            return None

        return UpdateOne(
            {"_id": self.entity_id},
            op_data
        )

    def to_data(self):
        fields = {}
        for key, value in self._update_data.items():
            if value is REMOVED_VALUE:
                value = None
            fields[key] = value

        output = super(UpdateOperation, self).to_data()
        output.update({
            "entity_id": str(self.entity_id),
            "fields": fields
        })
        return output


class DeleteOperation(AbstractOperation):
    operation_name = "delete"

    def __init__(self, project_name, entity_type, entity_id):
        super(DeleteOperation, self).__init__(project_name, entity_type)

        self._entity_id = ObjectId(entity_id)

    @property
    def entity_id(self):
        return self._entity_id

    def to_mongo_operation(self):
        return DeleteOne({"_id": self.entity_id})

    def to_data(self):
        output = super(DeleteOperation, self).to_data()
        output["entity_id"] = self.entity_id
        return output


class OperationsSession(object):
    """Session storing operations that should happen in an order.

    At this moment does not handle anything special can be sonsidered as
    stupid list of operations that will happen after each other. If creation
    of same entity is there multiple times it's handled in any way and document
    values are not validated.

    All operations must be related to single project.

    Args:
        project_name (str): Project name to which are operations related.
    """

    def __init__(self):
        self._operations = []

    def add(self, operation):
        """Add operation to be processed.

        Args:
            operation (BaseOperation): Operation that should be processed.
        """
        if not isinstance(
            operation,
            (CreateOperation, UpdateOperation, DeleteOperation)
        ):
            raise TypeError("Expected Operation object got {}".format(
                str(type(operation))
            ))

        self._operations.append(operation)

    def append(self, operation):
        """Add operation to be processed.

        Args:
            operation (BaseOperation): Operation that should be processed.
        """

        self.add(operation)

    def extend(self, operations):
        """Add operations to be processed.

        Args:
            operations (List[BaseOperation]): Operations that should be
                processed.
        """

        for operation in operations:
            self.add(operation)

    def remove(self, operation):
        """Remove operation."""

        self._operations.remove(operation)

    def clear(self):
        """Clear all registered operations."""

        self._operations = []

    def to_data(self):
        return [
            operation.to_data()
            for operation in self._operations
        ]

    def commit(self):
        """Commit session operations."""

        operations, self._operations = self._operations, []
        if not operations:
            return

        operations_by_project = collections.defaultdict(list)
        for operation in operations:
            operations_by_project[operation.project_name].append(operation)

        for project_name, operations in operations_by_project.items():
            bulk_writes = []
            for operation in operations:
                mongo_op = operation.to_mongo_operation()
                if mongo_op is not None:
                    bulk_writes.append(mongo_op)

            if bulk_writes:
                collection = get_project_connection(project_name)
                collection.bulk_write(bulk_writes)

    def create_entity(self, project_name, entity_type, data):
        operation = CreateOperation(project_name, entity_type, data)
        self.add(operation)
        return operation

    def update_entity(self, project_name, entity_type, entity_id, update_data):
        operation = UpdateOperation(
            project_name, entity_type, entity_id, update_data
        )
        self.add(operation)
        return operation

    def delete_entity(self, project_name, entity_type, entity_id):
        operation = DeleteOperation(project_name, entity_type, entity_id)
        self.add(operation)
        return operation
