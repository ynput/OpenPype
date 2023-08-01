import uuid
import copy
from abc import ABCMeta, abstractmethod, abstractproperty
import six

REMOVED_VALUE = object()


@six.add_metaclass(ABCMeta)
class AbstractOperation(object):
    """Base operation class.

    Operation represent a call into database. The call can create, change or
    remove data.

    Args:
        project_name (str): On which project operation will happen.
        entity_type (str): Type of entity on which change happens.
            e.g. 'asset', 'representation' etc.
    """

    def __init__(self, project_name, entity_type):
        self._project_name = project_name
        self._entity_type = entity_type
        self._id = str(uuid.uuid4())

    @property
    def project_name(self):
        return self._project_name

    @property
    def id(self):
        """Identifier of operation."""

        return self._id

    @property
    def entity_type(self):
        return self._entity_type

    @abstractproperty
    def operation_name(self):
        """Stringified type of operation."""

        pass

    def to_data(self):
        """Convert operation to data that can be converted to json or others.

        Warning:
            Current state returns ObjectId objects which cannot be parsed by
                json.

        Returns:
            Dict[str, Any]: Description of operation.
        """

        return {
            "id": self._id,
            "entity_type": self.entity_type,
            "project_name": self.project_name,
            "operation": self.operation_name
        }


class CreateOperation(AbstractOperation):
    """Operation to create an entity.

    Args:
        project_name (str): On which project operation will happen.
        entity_type (str): Type of entity on which change happens.
            e.g. 'asset', 'representation' etc.
        data (Dict[str, Any]): Data of entity that will be created.
    """

    operation_name = "create"

    def __init__(self, project_name, entity_type, data):
        super(CreateOperation, self).__init__(project_name, entity_type)

        if not data:
            data = {}
        else:
            data = copy.deepcopy(dict(data))
        self._data = data

    def __setitem__(self, key, value):
        self.set_value(key, value)

    def __getitem__(self, key):
        return self.data[key]

    def set_value(self, key, value):
        self.data[key] = value

    def get(self, key, *args, **kwargs):
        return self.data.get(key, *args, **kwargs)

    @abstractproperty
    def entity_id(self):
        pass

    @property
    def data(self):
        return self._data

    def to_data(self):
        output = super(CreateOperation, self).to_data()
        output["data"] = copy.deepcopy(self.data)
        return output


class UpdateOperation(AbstractOperation):
    """Operation to update an entity.

    Args:
        project_name (str): On which project operation will happen.
        entity_type (str): Type of entity on which change happens.
            e.g. 'asset', 'representation' etc.
        entity_id (Union[str, ObjectId]): Identifier of an entity.
        update_data (Dict[str, Any]): Key -> value changes that will be set in
            database. If value is set to 'REMOVED_VALUE' the key will be
            removed. Only first level of dictionary is checked (on purpose).
    """

    operation_name = "update"

    def __init__(self, project_name, entity_type, entity_id, update_data):
        super(UpdateOperation, self).__init__(project_name, entity_type)

        self._entity_id = entity_id
        self._update_data = update_data

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def update_data(self):
        return self._update_data

    def to_data(self):
        changes = {}
        for key, value in self._update_data.items():
            if value is REMOVED_VALUE:
                value = None
            changes[key] = value

        output = super(UpdateOperation, self).to_data()
        output.update({
            "entity_id": self.entity_id,
            "changes": changes
        })
        return output


class DeleteOperation(AbstractOperation):
    """Operation to delete an entity.

    Args:
        project_name (str): On which project operation will happen.
        entity_type (str): Type of entity on which change happens.
            e.g. 'asset', 'representation' etc.
        entity_id (Union[str, ObjectId]): Entity id that will be removed.
    """

    operation_name = "delete"

    def __init__(self, project_name, entity_type, entity_id):
        super(DeleteOperation, self).__init__(project_name, entity_type)

        self._entity_id = entity_id

    @property
    def entity_id(self):
        return self._entity_id

    def to_data(self):
        output = super(DeleteOperation, self).to_data()
        output["entity_id"] = self.entity_id
        return output


class BaseOperationsSession(object):
    """Session storing operations that should happen in an order.

    At this moment does not handle anything special can be considered as
    stupid list of operations that will happen after each other. If creation
    of same entity is there multiple times it's handled in any way and document
    values are not validated.
    """

    def __init__(self):
        self._operations = []

    def __len__(self):
        return len(self._operations)

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

    @abstractmethod
    def commit(self):
        """Commit session operations."""
        pass

    def create_entity(self, project_name, entity_type, data):
        """Fast access to 'CreateOperation'.

        Returns:
            CreateOperation: Object of update operation.
        """

        operation = CreateOperation(project_name, entity_type, data)
        self.add(operation)
        return operation

    def update_entity(self, project_name, entity_type, entity_id, update_data):
        """Fast access to 'UpdateOperation'.

        Returns:
            UpdateOperation: Object of update operation.
        """

        operation = UpdateOperation(
            project_name, entity_type, entity_id, update_data
        )
        self.add(operation)
        return operation

    def delete_entity(self, project_name, entity_type, entity_id):
        """Fast access to 'DeleteOperation'.

        Returns:
            DeleteOperation: Object of delete operation.
        """

        operation = DeleteOperation(project_name, entity_type, entity_id)
        self.add(operation)
        return operation
