"""These lib functions are for development purposes.

WARNING:
    This is not meant for production data. Please don't write code which is
        dependent on functionality here.

Goal is to be able to create package of current state of project with related
documents from mongo and files from disk to zip file and then be able
to recreate the project based on the zip.

This gives ability to create project where a changes and tests can be done.

Keep in mind that to be able to create a package of project has few
requirements. Possible requirement should be listed in 'pack_project' function.
"""

import os
import json
import platform
import tempfile
import shutil
import datetime

import zipfile
from openpype.client.mongo import (
    load_json_file,
    get_project_connection,
    replace_project_documents,
    store_project_documents,
)

DOCUMENTS_FILE_NAME = "database"
METADATA_FILE_NAME = "metadata"
PROJECT_FILES_DIR = "project_files"


def add_timestamp(filepath):
    """Add timestamp string to a file."""
    base, ext = os.path.splitext(filepath)
    timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    new_base = "{}_{}".format(base, timestamp)
    return new_base + ext


def get_project_document(project_name, database_name=None):
    """Query project document.

    Function 'get_project' from client api cannot be used as it does not allow
    to change which 'database_name' is used.

    Args:
        project_name (str): Name of project.
        database_name (Optional[str]): Name of mongo database where to look for
            project.

    Returns:
        Union[dict[str, Any], None]: Project document or None.
    """

    col = get_project_connection(project_name, database_name)
    return col.find_one({"type": "project"})


def _pack_files_to_zip(zip_stream, source_path, root_path):
    """Pack files to a zip stream.

    Args:
        zip_stream (zipfile.ZipFile): Stream to a zipfile.
        source_path (str): Path to a directory where files are.
        root_path (str): Path to a directory which is used for calculation
            of relative path.
    """

    for root, _, filenames in os.walk(source_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            # TODO add one more folder
            archive_name = os.path.join(
                PROJECT_FILES_DIR,
                os.path.relpath(filepath, root_path)
            )
            zip_stream.write(filepath, archive_name)


def pack_project(
    project_name,
    destination_dir=None,
    only_documents=False,
    database_name=None
):
    """Make a package of a project with mongo documents and files.

    This function has few restrictions:
    - project must have only one root
    - project must have all templates starting with
        "{root[...]}/{project[name]}"

    Args:
        project_name (str): Project that should be packaged.
        destination_dir (Optional[str]): Optional path where zip will be
            stored. Project's root is used if not passed.
        only_documents (Optional[bool]): Pack only Mongo documents and skip
            files.
        database_name (Optional[str]): Custom database name from which is
            project queried.
    """

    print("Creating package of project \"{}\"".format(project_name))
    # Validate existence of project
    project_doc = get_project_document(project_name, database_name)
    if not project_doc:
        raise ValueError("Project \"{}\" was not found in database".format(
            project_name
        ))

    root_path = None
    source_root = {}
    project_source_path = None
    if not only_documents:
        roots = project_doc["config"]["roots"]
        # Determine root directory of project
        source_root_name = None
        for root_name, root_value in roots.items():
            if source_root is not None:
                raise ValueError(
                    "Packaging is supported only for single root projects"
                )
            source_root = root_value
            source_root_name = root_name

        root_path = source_root[platform.system().lower()]
        print("Using root \"{}\" with path \"{}\"".format(
            source_root_name, root_path
        ))

        project_source_path = os.path.join(root_path, project_name)
        if not os.path.exists(project_source_path):
            raise ValueError("Didn't find source of project files")

    # Determine zip filepath where data will be stored
    if not destination_dir:
        destination_dir = root_path

    if not destination_dir:
        if only_documents:
            raise ValueError((
                "Destination dir must be passed."
                " Use '--dirpath {output dir path}' if using command line."
            ))
        raise ValueError(
            "Project {} does not have any roots.".format(project_name)
        )

    destination_dir = os.path.normpath(destination_dir)
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    zip_path = os.path.join(destination_dir, project_name + ".zip")

    print("Project will be packaged into \"{}\"".format(zip_path))
    # Rename already existing zip
    if os.path.exists(zip_path):
        dst_filepath = add_timestamp(zip_path)
        os.rename(zip_path, dst_filepath)

    # We can add more data
    metadata = {
        "project_name": project_name,
        "root": source_root,
        "version": 1
    }
    # Create temp json file where metadata are stored
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as s:
        temp_metadata_json = s.name

    with open(temp_metadata_json, "w") as stream:
        json.dump(metadata, stream)

    # Create temp json file where database documents are stored
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as s:
        temp_docs_json = s.name

    # Query all project documents and store them to temp json
    store_project_documents(project_name, temp_docs_json, database_name)

    print("Packing files into zip")
    # Write all to zip file
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_stream:
        # Add metadata file
        zip_stream.write(temp_metadata_json, METADATA_FILE_NAME + ".json")
        # Add database documents
        zip_stream.write(temp_docs_json, DOCUMENTS_FILE_NAME + ".json")

        # Add project files to zip
        if not only_documents:
            _pack_files_to_zip(zip_stream, project_source_path, root_path)

    print("Cleaning up")
    # Cleanup
    os.remove(temp_docs_json)
    os.remove(temp_metadata_json)

    print("*** Packing finished ***")


def _unpack_project_files(unzip_dir, root_path, project_name):
    """Move project files from unarchived temp folder to new root.

    Unpack is skipped if source files are not available in the zip. That can
    happen if nothing was published yet or only documents were stored to
    package.

    Args:
        unzip_dir (str): Location where zip was unzipped.
        root_path (str): Path to new root.
        project_name (str): Name of project.
    """

    src_project_files_dir = os.path.join(
        unzip_dir, PROJECT_FILES_DIR, project_name
    )
    # Skip if files are not in the zip
    if not os.path.exists(src_project_files_dir):
        return

    # Make sure root path exists
    if not os.path.exists(root_path):
        os.makedirs(root_path)

    dst_project_files_dir = os.path.normpath(
        os.path.join(root_path, project_name)
    )
    if os.path.exists(dst_project_files_dir):
        new_path = add_timestamp(dst_project_files_dir)
        print("Project folder already exists. Renamed \"{}\" -> \"{}\"".format(
            dst_project_files_dir, new_path
        ))
        os.rename(dst_project_files_dir, new_path)

    print("Moving project files from temp \"{}\" -> \"{}\"".format(
        src_project_files_dir, dst_project_files_dir
    ))
    shutil.move(src_project_files_dir, dst_project_files_dir)


def unpack_project(
    path_to_zip, new_root=None, database_only=None, database_name=None
):
    """Unpack project zip file to recreate project.

    Args:
        path_to_zip (str): Path to zip which was created using 'pack_project'
            function.
        new_root (str): Optional way how to set different root path for
            unpacked project.
        database_only (Optional[bool]): Unpack only database from zip.
        database_name (str): Name of database where project will be recreated.
    """

    if database_only is None:
        database_only = False

    print("Unpacking project from zip {}".format(path_to_zip))
    if not os.path.exists(path_to_zip):
        print("Zip file does not exists: {}".format(path_to_zip))
        return

    tmp_dir = tempfile.mkdtemp(prefix="unpack_")
    print("Zip is extracted to temp: {}".format(tmp_dir))
    with zipfile.ZipFile(path_to_zip, "r") as zip_stream:
        if database_only:
            for filename in (
                "{}.json".format(METADATA_FILE_NAME),
                "{}.json".format(DOCUMENTS_FILE_NAME),
            ):
                zip_stream.extract(filename, tmp_dir)
        else:
            zip_stream.extractall(tmp_dir)

    metadata_json_path = os.path.join(tmp_dir, METADATA_FILE_NAME + ".json")
    with open(metadata_json_path, "r") as stream:
        metadata = json.load(stream)

    docs_json_path = os.path.join(tmp_dir, DOCUMENTS_FILE_NAME + ".json")
    docs = load_json_file(docs_json_path)

    low_platform = platform.system().lower()
    project_name = metadata["project_name"]
    root_path = metadata["root"].get(low_platform)

    # Drop existing collection
    replace_project_documents(project_name, docs, database_name)
    print("Creating project documents ({})".format(len(docs)))

    # Skip change of root if is the same as the one stored in metadata
    if (
        new_root
        and (os.path.normpath(new_root) == os.path.normpath(root_path))
    ):
        new_root = None

    if new_root:
        print("Using different root path {}".format(new_root))
        root_path = new_root

        project_doc = get_project_document(project_name)
        roots = project_doc["config"]["roots"]
        key = tuple(roots.keys())[0]
        update_key = "config.roots.{}.{}".format(key, low_platform)
        collection = get_project_connection(project_name, database_name)
        collection.update_one(
            {"_id": project_doc["_id"]},
            {"$set": {
                update_key: new_root
            }}
        )

    _unpack_project_files(tmp_dir, root_path, project_name)

    # CLeanup
    print("Cleaning up")
    shutil.rmtree(tmp_dir)
    print("*** Unpack finished ***")
