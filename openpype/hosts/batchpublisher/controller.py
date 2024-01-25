import glob
import os

from openpype.settings import get_project_settings
from openpype.client.entities import (
    get_projects,
    get_assets,
)
from openpype.hosts.batchpublisher import publish


# TODO: add to OpenPype settings so other studios can change
FILE_MAPPINGS = [
    {
        "glob": "*/fbx/*.fbx",
        "is_sequence": False,
        "product_type": "model",
    }
]


class IngestFile(object):
    def __init__(
        self,
        filepath,
        product_type,
        product_name,
        representation_name,
        version=None,
        enabled=True,
        folder_path=None,
        task_name=None
    ):
        self.enabled = enabled
        self.filepath = filepath
        self.product_type = product_type
        self.product_name = product_name or ""
        self.representation_name = representation_name
        self.version = version
        self.folder_path = folder_path or ""
        self.task_name = task_name or ""
        self.task_names = []

    @property
    def defined(self):
        return all([
            bool(self.filepath),
            bool(self.folder_path),
            bool(self.task_name),
            bool(self.product_type),
            bool(self.product_name),
            bool(self.representation_name)])


class HierarchyItem:
    def __init__(self, folder_name, folder_path, folder_id, parent_id):
        self.folder_name = folder_name
        self.folder_path = folder_path
        self.folder_id = folder_id
        self.parent_id = parent_id


class BatchPublisherController(object):

    def __init__(self):
        self._selected_project_name = None
        self._project_names = None
        self._asset_docs_by_project = {}
        self._asset_docs_by_path = {}

    def get_project_names(self):
        if self._project_names is None:
            projects = get_projects(fields={"name"})
            project_names = []
            for project in projects:
                project_names.append(project["name"])
            self._project_names = project_names
        return self._project_names

    def get_selected_project_name(self):
        return self._selected_project_name

    def set_selected_project_name(self, project_name):
        self._selected_project_name = project_name

    def _get_asset_docs(self):
        """

        Returns:
            dict[str, dict]: Dictionary of asset documents by path.
        """

        project_name = self._selected_project_name
        if not project_name:
            return {}

        asset_docs = self._asset_docs_by_project.get(project_name)
        if asset_docs is None:
            asset_docs = get_assets(
                project_name
            )
            asset_docs_by_path = self._prepare_assets_by_path(asset_docs)
            self._asset_docs_by_project[project_name] = asset_docs_by_path
        return self._asset_docs_by_project[project_name]

    def get_hierarchy_items(self):
        """

        Returns:
            list[HierarchyItem]: List of hierarchy items.
        """

        asset_docs = self._get_asset_docs()
        if not asset_docs:
            return []

        output = []
        for folder_path, asset_doc in asset_docs.items():
            folder_name = asset_doc["name"]
            folder_id = asset_doc["_id"]
            parent_id = asset_doc["data"]["visualParent"]
            hierarchy_item = HierarchyItem(
                folder_name, folder_path, folder_id, parent_id)
            output.append(hierarchy_item)
        return output

    def get_task_names(self, folder_path):
        asset_docs_by_path = self._get_asset_docs()
        if not asset_docs_by_path:
            return []

        asset_doc = asset_docs_by_path.get(folder_path)
        return list(asset_doc["data"]["tasks"].keys())

    def _prepare_assets_by_path(self, asset_docs):
        output = {}
        for asset_doc in asset_docs:
            folder_path = (
                "/" + "/".join(
                    asset_doc["data"]["parents"] + [asset_doc["name"]]
                )
            )
            output[folder_path] = asset_doc
        return output

    def get_ingest_files(self, directory):
        """

        Returns:
            list[IngestFile]: List of ingest files for the given directory
        """

        output = []
        if not directory or not os.path.exists(directory):
            return output

        # project_name = self._selected_project_name
        # project_settings = get_project_settings(project_name)
        # file_mappings = project_settings["batchpublisher"].get("file_mappings", [])
        file_mappings = FILE_MAPPINGS
        for file_mapping in file_mappings:
            product_type = file_mapping["product_type"]
            glob_full_path = directory + "/" + file_mapping["glob"]
            files = glob.glob(glob_full_path, recursive=False)
            for filepath in files:
                filename = os.path.basename(filepath)
                representation_name = os.path.splitext(
                    filename)[1].lstrip(".")
                product_name = os.path.splitext(filename)[0]
                ingest_file = IngestFile(
                    filepath,
                    product_type,
                    product_name,
                    representation_name)
                output.append(ingest_file)
        return output

    def publish_ingest_files(self, ingest_files):
        """

        Args:
            ingest_files (list[IngestFile]): List of ingest files to publish.
        """

        for ingest_file in ingest_files:
            if ingest_file.enabled and ingest_file.defined:
                self._publish_ingest_file(ingest_file)

    def _publish_ingest_file(self, ingest_file):
        msg = f"""
Publishing (ingesting): {ingest_file.filepath}
As Folder (Asset): {ingest_file.folder_path}
Task: {ingest_file.task_name}
Product Type (Family): {ingest_file.product_type}
Product Name (Subset): {ingest_file.product_name}
Representation: {ingest_file.representation_name}
Version: {ingest_file.version}"
Project: {self._selected_project_name}"""
        print(msg)
        publish_data = dict()
        expected_representations = dict()
        expected_representations[ingest_file.representation_name] = \
            ingest_file.filepath
        publish.publish_version(
            self._selected_project_name,
            ingest_file.folder_path,
            ingest_file.task_name,
            ingest_file.product_type,
            ingest_file.product_name,
            expected_representations,
            publish_data)
        # publish.publish_version(
        #     project_name,
        #     asset_name,
        #     task_name,
        #     family_name,
        #     subset_name,
        #     expected_representations,
        #     publish_data,
