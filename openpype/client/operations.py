import uuid
import copy
from abc import ABCMeta, abstractmethod

import six
from bson.objectid import ObjectId
from pymongo import DeleteOne, InsertOne, UpdateOne

from .mongo import get_project_connection

REMOVED_VALUE = object()


@six.add_metaclass(ABCMeta)
class AbstractOperation(object):
    """Base operation class."""

    def __init__(self, entity_type):
        self._entity_type = entity_type
        self._id = uuid.uuid4()

    @property
    def id(self):
        return self._id

    @property
    def entity_type(self):
        return self._entity_type

    @abstractmethod
    def to_mongo_operation(self):
        pass


class CreateOperation(AbstractOperation):
    def __init__(self, project_name, entity_type, data):
        super(CreateOperation, self).__init__(entity_type)

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
        return {
            "operation": "create",
            "entity_type": self.entity_type,
            "data": copy.deepcopy(self.data)
        }


class UpdateOperation(AbstractOperation):
    def __init__(self, project_name, entity_type, entity_id, update_fields):
        super(CreateOperation, self).__init__(entity_type)

        self._entity_id = ObjectId(entity_id)
        self._update_fields = update_fields

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def update_fields(self):
        return self._update_fields

    def to_mongo_operation(self):
        unset_data = {}
        set_data = {}
        for key, value in self._update_fields.items():
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
        for key, value in self._update_fields.items():
            if value is REMOVED_VALUE:
                value = None
            fields[key] = value

        return {
            "operation": "update",
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "fields": fields
        }


class DeleteOperation(AbstractOperation):
    def __init__(self, entity_type, entity_id):
        super(DeleteOperation, self).__init__(entity_type)

        self._entity_id = ObjectId(entity_id)

    @property
    def entity_id(self):
        return self._entity_id

    def to_mongo_operation(self):
        return DeleteOne({"_id": self.entity_id})

    def to_data(self):
        return {
            "operation": "delete",
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id)
        }


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

    def __init__(self, project_name):
        self._project_name = project_name
        self._operations = []

    @property
    def project_name(self):
        return self._project_name

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
        return {
            "project_name": self.project_name,
            "operations": [
                operation.to_data()
                for operation in self._operations
            ]
        }

    def commit(self):
        """Commit session operations."""

        operations, self._operations = self._operations, []
        if not operations:
            return

        bulk_writes = []
        for operation in operations:
            mongo_op = operation.to_mongo_operation()
            if mongo_op is not None:
                bulk_writes.append(mongo_op)

        if bulk_writes:
            collection = get_project_connection(self.project_name)
            collection.bulk_write(bulk_writes)
