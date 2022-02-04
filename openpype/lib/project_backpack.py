"""These lib functions are primarily for development purposes.

WARNING: This is not meant for production data.

Goal is to be able create package of current state of project with related
documents from mongo and files from disk to zip file and then be able recreate
the project based on the zip.

This gives ability to create project where a changes and tests can be done.

Keep in mind that to be able create a package of project has few requirements.
Possible requirement should be listed in 'pack_project' function.
"""
import os
import json
import platform
import tempfile
import shutil
import datetime

import zipfile
from bson.json_util import (
    loads,
    dumps,
    CANONICAL_JSON_OPTIONS
)

from avalon.api import AvalonMongoDB

DOCUMENTS_FILE_NAME = "database"
METADATA_FILE_NAME = "metadata"
PROJECT_FILES_DIR = "project_files"


def add_timestamp(filepath):
    """Add timestamp string to a file."""
    base, ext = os.path.splitext(filepath)
    timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    new_base = "{}_{}".format(base, timestamp)
    return new_base + ext


def pack_project(project_name, destination_dir=None):
    """Make a package of a project with mongo documents and files.

    This function has few restrictions:
    - project must have only one root
    - project must have all templates starting with
        "{root[...]}/{project[name]}"

    Args:
        project_name(str): Project that should be packaged.
        destination_dir(str): Optinal path where zip will be stored. Project's
            root is used if not passed.
    """
    print("Creating package of project \"{}\"".format(project_name))
    # Validate existence of project
    dbcon = AvalonMongoDB()
    dbcon.Session["AVALON_PROJECT"] = project_name
    project_doc = dbcon.find_one({"type": "project"})
    if not project_doc:
        raise ValueError("Project \"{}\" was not found in database".format(
            project_name
        ))

    roots = project_doc["config"]["roots"]
    # Determine root directory of project
    source_root = None
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
    docs = list(dbcon.find({}))
    data = dumps(
        docs, json_options=CANONICAL_JSON_OPTIONS
    )
    with open(temp_docs_json, "w") as stream:
        stream.write(data)

    print("Packing files into zip")
    # Write all to zip file
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_stream:
        # Add metadata file
        zip_stream.write(temp_metadata_json, METADATA_FILE_NAME + ".json")
        # Add database documents
        zip_stream.write(temp_docs_json, DOCUMENTS_FILE_NAME + ".json")
        # Add project files to zip
        for root, _, filenames in os.walk(project_source_path):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                # TODO add one more folder
                archive_name = os.path.join(
                    PROJECT_FILES_DIR,
                    os.path.relpath(filepath, root_path)
                )
                zip_stream.write(filepath, archive_name)

    print("Cleaning up")
    # Cleanup
    os.remove(temp_docs_json)
    os.remove(temp_metadata_json)
    dbcon.uninstall()
    print("*** Packing finished ***")


def unpack_project(path_to_zip, new_root=None):
    """Unpack project zip file to recreate project.

    Args:
        path_to_zip(str): Path to zip which was created using 'pack_project'
            function.
        new_root(str): Optional way how to set different root path for unpacked
            project.
    """
    print("Unpacking project from zip {}".format(path_to_zip))
    if not os.path.exists(path_to_zip):
        print("Zip file does not exists: {}".format(path_to_zip))
        return

    tmp_dir = tempfile.mkdtemp(prefix="unpack_")
    print("Zip is extracted to temp: {}".format(tmp_dir))
    with zipfile.ZipFile(path_to_zip, "r") as zip_stream:
        zip_stream.extractall(tmp_dir)

    metadata_json_path = os.path.join(tmp_dir, METADATA_FILE_NAME + ".json")
    with open(metadata_json_path, "r") as stream:
        metadata = json.load(stream)

    docs_json_path = os.path.join(tmp_dir, DOCUMENTS_FILE_NAME + ".json")
    with open(docs_json_path, "r") as stream:
        content = stream.readlines()
    docs = loads("".join(content))

    low_platform = platform.system().lower()
    project_name = metadata["project_name"]
    source_root = metadata["root"]
    root_path = source_root[low_platform]

    # Drop existing collection
    dbcon = AvalonMongoDB()
    database = dbcon.database
    if project_name in database.list_collection_names():
        database.drop_collection(project_name)
        print("Removed existing project collection")

    print("Creating project documents ({})".format(len(docs)))
    # Create new collection with loaded docs
    collection = database[project_name]
    collection.insert_many(docs)

    # Skip change of root if is the same as the one stored in metadata
    if (
        new_root
        and (os.path.normpath(new_root) == os.path.normpath(root_path))
    ):
        new_root = None

    if new_root:
        print("Using different root path {}".format(new_root))
        root_path = new_root

        project_doc = collection.find_one({"type": "project"})
        roots = project_doc["config"]["roots"]
        key = tuple(roots.keys())[0]
        update_key = "config.roots.{}.{}".format(key, low_platform)
        collection.update_one(
            {"_id": project_doc["_id"]},
            {"$set": {
                update_key: new_root
            }}
        )

    # Make sure root path exists
    if not os.path.exists(root_path):
        os.makedirs(root_path)

    src_project_files_dir = os.path.join(
        tmp_dir, PROJECT_FILES_DIR, project_name
    )
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

    # CLeanup
    print("Cleaning up")
    shutil.rmtree(tmp_dir)
    dbcon.uninstall()
    print("*** Unpack finished ***")
