import os
import copy

from openpype.pipeline import Anatomy
from openpype.client import get_workfile_info
from openpype.client.operations import (
    OperationsSession,
    new_workfile_info_doc,
    prepare_workfile_info_update_data,
)


def get_workfile_doc(project_name, asset_id, task_name, filepath):
    """Return workfile document from database, if it exists.

    Args:
        project_name (str): Project name.
        asset_id (ObjectID): Asset ID.
        task_name (str): Task name.
        filepath (str): Workfile filepath.
    """
    filename = os.path.basename(filepath)
    return get_workfile_info(project_name, asset_id, task_name, filename)


def create_workfile_doc(project_name, asset_id, task_name, filepath):
    """Create workfile document in database.

    If it already exists. the existing document is returned.

    Args:
        project_name (str): Project name.
        asset_id (ObjectID): Asset ID.
        task_name (str): Task name.
        filepath (str): Workfile filepath.
    """
    workdir, filename = os.path.split(filepath)
    workfile_doc = get_workfile_info(
        project_name, asset_id, task_name, filename
    )
    if workfile_doc:
        return workfile_doc

    # Create a new document
    anatomy = Anatomy(project_name)
    success, rootless_dir = anatomy.find_root_template_from_path(workdir)
    filepath = "/".join(
        [
            os.path.normpath(rootless_dir).replace("\\", "/"),
        ]
    )

    workfile_doc = new_workfile_info_doc(
        filename, asset_id, task_name, [filepath]
    )

    session = OperationsSession()
    session.create_entity(project_name, "workfile", workfile_doc)
    session.commit()

    return workfile_doc


def set_workfile_data(project_name, asset_id, task_name, filepath, data):
    """Update workfile data.

    If the workfile document does not exist in the database yet
    it will be created.

    Args:
        project_name (str): Project name.
        asset_id (ObjectID): Asset ID.
        task_name (str): Task name.
        filepath (str): Workfile filepath.
        data (dict): Workfile data content.
    """
    # This does not create the document if it already exists.
    workfile_doc = create_workfile_doc(
        project_name, asset_id, task_name, filepath
    )
    if workfile_doc.get("data") == data:
        # Nothing to update
        return

    new_workfile_doc = copy.deepcopy(workfile_doc)
    new_workfile_doc.setdefault("data", {}).update(data)
    update_data = prepare_workfile_info_update_data(
        workfile_doc, new_workfile_doc
    )
    if not update_data:
        return

    session = OperationsSession()
    session.update_entity(
        project_name, "workfile", workfile_doc["_id"], update_data
    )
    session.commit()
