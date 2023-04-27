import re
import copy
import collections

from bson.objectid import ObjectId
from pymongo import DeleteOne, InsertOne, UpdateOne

from openpype.client.operations_base import (
    REMOVED_VALUE,
    CreateOperation,
    UpdateOperation,
    DeleteOperation,
    BaseOperationsSession
)
from .mongo import get_project_connection
from .entities import get_project


PROJECT_NAME_ALLOWED_SYMBOLS = "a-zA-Z0-9_"
PROJECT_NAME_REGEX = re.compile(
    "^[{}]+$".format(PROJECT_NAME_ALLOWED_SYMBOLS)
)

CURRENT_PROJECT_SCHEMA = "openpype:project-3.0"
CURRENT_PROJECT_CONFIG_SCHEMA = "openpype:config-2.0"
CURRENT_ASSET_DOC_SCHEMA = "openpype:asset-3.0"
CURRENT_SUBSET_SCHEMA = "openpype:subset-3.0"
CURRENT_VERSION_SCHEMA = "openpype:version-3.0"
CURRENT_HERO_VERSION_SCHEMA = "openpype:hero_version-1.0"
CURRENT_REPRESENTATION_SCHEMA = "openpype:representation-2.0"
CURRENT_WORKFILE_INFO_SCHEMA = "openpype:workfile-1.0"
CURRENT_THUMBNAIL_SCHEMA = "openpype:thumbnail-1.0"


def _create_or_convert_to_mongo_id(mongo_id):
    if mongo_id is None:
        return ObjectId()
    return ObjectId(mongo_id)


def new_project_document(
    project_name, project_code, config, data=None, entity_id=None
):
    """Create skeleton data of project document.

    Args:
        project_name (str): Name of project. Used as identifier of a project.
        project_code (str): Shorter version of projet without spaces and
            special characters (in most of cases). Should be also considered
            as unique name across projects.
        config (Dic[str, Any]): Project config consist of roots, templates,
            applications and other project Anatomy related data.
        data (Dict[str, Any]): Project data with information about it's
            attributes (e.g. 'fps' etc.) or integration specific keys.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of project document.
    """

    if data is None:
        data = {}

    data["code"] = project_code

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "name": project_name,
        "type": CURRENT_PROJECT_SCHEMA,
        "entity_data": data,
        "config": config
    }


def new_asset_document(
    name, project_id, parent_id, parents, data=None, entity_id=None
):
    """Create skeleton data of asset document.

    Args:
        name (str): Is considered as unique identifier of asset in project.
        project_id (Union[str, ObjectId]): Id of project doument.
        parent_id (Union[str, ObjectId]): Id of parent asset.
        parents (List[str]): List of parent assets names.
        data (Dict[str, Any]): Asset document data. Empty dictionary is used
            if not passed. Value of 'parent_id' is used to fill 'visualParent'.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of asset document.
    """

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
    """Create skeleton data of subset document.

    Args:
        name (str): Is considered as unique identifier of subset under asset.
        family (str): Subset's family.
        asset_id (Union[str, ObjectId]): Id of parent asset.
        data (Dict[str, Any]): Subset document data. Empty dictionary is used
            if not passed. Value of 'family' is used to fill 'family'.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of subset document.
    """

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
    """Create skeleton data of version document.

    Args:
        version (int): Is considered as unique identifier of version
            under subset.
        subset_id (Union[str, ObjectId]): Id of parent subset.
        data (Dict[str, Any]): Version document data.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of version document.
    """

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


def new_hero_version_doc(version_id, subset_id, data=None, entity_id=None):
    """Create skeleton data of hero version document.

    Args:
        version_id (ObjectId): Is considered as unique identifier of version
            under subset.
        subset_id (Union[str, ObjectId]): Id of parent subset.
        data (Dict[str, Any]): Version document data.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of version document.
    """

    if data is None:
        data = {}

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "schema": CURRENT_HERO_VERSION_SCHEMA,
        "type": "hero_version",
        "version_id": version_id,
        "parent": subset_id,
        "data": data
    }


def new_representation_doc(
    name, version_id, context, data=None, entity_id=None
):
    """Create skeleton data of asset document.

    Args:
        version (int): Is considered as unique identifier of version
            under subset.
        version_id (Union[str, ObjectId]): Id of parent version.
        context (Dict[str, Any]): Representation context used for fill template
            of to query.
        data (Dict[str, Any]): Representation document data.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of version document.
    """

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


def new_thumbnail_doc(data=None, entity_id=None):
    """Create skeleton data of thumbnail document.

    Args:
        data (Dict[str, Any]): Thumbnail document data.
        entity_id (Union[str, ObjectId]): Predefined id of document. New id is
            created if not passed.

    Returns:
        Dict[str, Any]: Skeleton of thumbnail document.
    """

    if data is None:
        data = {}

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "type": "thumbnail",
        "schema": CURRENT_THUMBNAIL_SCHEMA,
        "data": data
    }


def new_workfile_info_doc(
    filename, asset_id, task_name, files, data=None, entity_id=None
):
    """Create skeleton data of workfile info document.

    Workfile document is at this moment used primarily for artist notes.

    Args:
        filename (str): Filename of workfile.
        asset_id (Union[str, ObjectId]): Id of asset under which workfile live.
        task_name (str): Task under which was workfile created.
        files (List[str]): List of rootless filepaths related to workfile.
        data (Dict[str, Any]): Additional metadata.

    Returns:
        Dict[str, Any]: Skeleton of workfile info document.
    """

    if not data:
        data = {}

    return {
        "_id": _create_or_convert_to_mongo_id(entity_id),
        "type": "workfile",
        "parent": ObjectId(asset_id),
        "task_name": task_name,
        "filename": filename,
        "data": data,
        "files": files
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
    """Compare two subset documents and prepare update data.

    Based on compared values will create update data for
    'MongoUpdateOperation'.

    Empty output means that documents are identical.

    Returns:
        Dict[str, Any]: Changes between old and new document.
    """

    return _prepare_update_data(old_doc, new_doc, replace)


def prepare_version_update_data(old_doc, new_doc, replace=True):
    """Compare two version documents and prepare update data.

    Based on compared values will create update data for
    'MongoUpdateOperation'.

    Empty output means that documents are identical.

    Returns:
        Dict[str, Any]: Changes between old and new document.
    """

    return _prepare_update_data(old_doc, new_doc, replace)


def prepare_hero_version_update_data(old_doc, new_doc, replace=True):
    """Compare two hero version documents and prepare update data.

    Based on compared values will create update data for 'UpdateOperation'.

    Empty output means that documents are identical.

    Returns:
        Dict[str, Any]: Changes between old and new document.
    """

    return _prepare_update_data(old_doc, new_doc, replace)


def prepare_representation_update_data(old_doc, new_doc, replace=True):
    """Compare two representation documents and prepare update data.

    Based on compared values will create update data for
    'MongoUpdateOperation'.

    Empty output means that documents are identical.

    Returns:
        Dict[str, Any]: Changes between old and new document.
    """

    return _prepare_update_data(old_doc, new_doc, replace)


def prepare_workfile_info_update_data(old_doc, new_doc, replace=True):
    """Compare two workfile info documents and prepare update data.

    Based on compared values will create update data for
    'MongoUpdateOperation'.

    Empty output means that documents are identical.

    Returns:
        Dict[str, Any]: Changes between old and new document.
    """

    return _prepare_update_data(old_doc, new_doc, replace)


class MongoCreateOperation(CreateOperation):
    """Operation to create an entity.

    Args:
        project_name (str): On which project operation will happen.
        entity_type (str): Type of entity on which change happens.
            e.g. 'asset', 'representation' etc.
        data (Dict[str, Any]): Data of entity that will be created.
    """

    operation_name = "create"

    def __init__(self, project_name, entity_type, data):
        super(MongoCreateOperation, self).__init__(
            project_name, entity_type, data
        )

        if "_id" not in self._data:
            self._data["_id"] = ObjectId()
        else:
            self._data["_id"] = ObjectId(self._data["_id"])

    @property
    def entity_id(self):
        return self._data["_id"]

    def to_mongo_operation(self):
        return InsertOne(copy.deepcopy(self._data))


class MongoUpdateOperation(UpdateOperation):
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
        super(MongoUpdateOperation, self).__init__(
            project_name, entity_type, entity_id, update_data
        )

        self._entity_id = ObjectId(self._entity_id)

    def to_mongo_operation(self):
        unset_data = {}
        set_data = {}
        for key, value in self._update_data.items():
            if value is REMOVED_VALUE:
                unset_data[key] = None
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


class MongoDeleteOperation(DeleteOperation):
    """Operation to delete an entity.

    Args:
        project_name (str): On which project operation will happen.
        entity_type (str): Type of entity on which change happens.
            e.g. 'asset', 'representation' etc.
        entity_id (Union[str, ObjectId]): Entity id that will be removed.
    """

    operation_name = "delete"

    def __init__(self, project_name, entity_type, entity_id):
        super(MongoDeleteOperation, self).__init__(
            project_name, entity_type, entity_id
        )

        self._entity_id = ObjectId(self._entity_id)

    def to_mongo_operation(self):
        return DeleteOne({"_id": self.entity_id})


class MongoOperationsSession(BaseOperationsSession):
    """Session storing operations that should happen in an order.

    At this moment does not handle anything special can be sonsidered as
    stupid list of operations that will happen after each other. If creation
    of same entity is there multiple times it's handled in any way and document
    values are not validated.

    All operations must be related to single project.

    Args:
        project_name (str): Project name to which are operations related.
    """

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
        """Fast access to 'MongoCreateOperation'.

        Returns:
            MongoCreateOperation: Object of update operation.
        """

        operation = MongoCreateOperation(project_name, entity_type, data)
        self.add(operation)
        return operation

    def update_entity(self, project_name, entity_type, entity_id, update_data):
        """Fast access to 'MongoUpdateOperation'.

        Returns:
            MongoUpdateOperation: Object of update operation.
        """

        operation = MongoUpdateOperation(
            project_name, entity_type, entity_id, update_data
        )
        self.add(operation)
        return operation

    def delete_entity(self, project_name, entity_type, entity_id):
        """Fast access to 'MongoDeleteOperation'.

        Returns:
            MongoDeleteOperation: Object of delete operation.
        """

        operation = MongoDeleteOperation(project_name, entity_type, entity_id)
        self.add(operation)
        return operation


def create_project(project_name, project_code, library_project=False):
    """Create project using OpenPype settings.

    This project creation function is not validating project document on
    creation. It is because project document is created blindly with only
    minimum required information about project which is it's name, code, type
    and schema.

    Entered project name must be unique and project must not exist yet.

    Note:
        This function is here to be OP v4 ready but in v3 has more logic
            to do. That's why inner imports are in the body.

    Args:
        project_name(str): New project name. Should be unique.
        project_code(str): Project's code should be unique too.
        library_project(bool): Project is library project.

    Raises:
        ValueError: When project name already exists in MongoDB.

    Returns:
        dict: Created project document.
    """

    from openpype.settings import ProjectSettings, SaveWarningExc
    from openpype.pipeline.schema import validate

    if get_project(project_name, fields=["name"]):
        raise ValueError("Project with name \"{}\" already exists".format(
            project_name
        ))

    if not PROJECT_NAME_REGEX.match(project_name):
        raise ValueError((
            "Project name \"{}\" contain invalid characters"
        ).format(project_name))

    project_doc = {
        "type": "project",
        "name": project_name,
        "data": {
            "code": project_code,
            "library_project": library_project
        },
        "schema": CURRENT_PROJECT_SCHEMA
    }

    op_session = MongoOperationsSession()
    # Insert document with basic data
    create_op = op_session.create_entity(
        project_name, project_doc["type"], project_doc
    )
    op_session.commit()

    # Load ProjectSettings for the project and save it to store all attributes
    #   and Anatomy
    try:
        project_settings_entity = ProjectSettings(project_name)
        project_settings_entity.save()
    except SaveWarningExc as exc:
        print(str(exc))
    except Exception:
        op_session.delete_entity(
            project_name, project_doc["type"], create_op.entity_id
        )
        op_session.commit()
        raise

    project_doc = get_project(project_name)

    try:
        # Validate created project document
        validate(project_doc)
    except Exception:
        # Remove project if is not valid
        op_session.delete_entity(
            project_name, project_doc["type"], create_op.entity_id
        )
        op_session.commit()
        raise

    return project_doc
