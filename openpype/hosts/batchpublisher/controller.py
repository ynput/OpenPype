import glob
import os

# from openpype.settings import get_project_settings
from openpype.client.entities import (
    get_projects,
    get_assets,
)
from openpype.hosts.batchpublisher import publish


# List that contains dictionary including glob statement to check for match.
# If filepath matches then it becomes product type.
# TODO: add to OpenPype settings so other studios can change
FILE_MAPPINGS = [
    {
        "glob": "*/fbx/*.fbx",
        "is_sequence": False,
        "product_type": "model",
    }
]

# Dictionary that maps the extension name to the representation name
# we want to use for it
EXT_TO_REP_NAME = {
    ".nk": "nuke",
    ".ma": "maya",
    ".mb": "maya",
    ".hip": "houdini",
    ".sfx": "silhouette",
    ".mocha": "mocha",
    ".psd": "photoshop"
}


class ProductItem(object):
    def __init__(
        self,
        filepath,
        product_type,
        product_name,
        representation_name,
        version=None,
        comment=None,
        enabled=True,
        folder_path=None,
        task_name=None
    ):
        self.enabled = enabled
        self.filepath = filepath
        self.product_type = product_type
        self.product_name = product_name
        self.representation_name = representation_name
        self.version = version
        self.folder_path = folder_path
        self.comment = comment
        self.task_name = task_name

    @property
    def defined(self):
        return all([
            self.filepath,
            self.folder_path,
            self.task_name,
            self.product_type,
            self.product_name,
            self.representation_name])


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
            asset_docs = list(get_assets(
                project_name,
                fields={
                    "name",
                    "data.visualParent",
                    "data.parents",
                    "data.tasks",
                }
            ))
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
        if not asset_doc:
            return []
        return list(asset_doc["data"]["tasks"].keys())

    def _prepare_assets_by_path(self, asset_docs):
        output = {}
        for asset_doc in asset_docs:
            parents = list(asset_doc["data"]["parents"])
            parents.append(asset_doc["name"])
            folder_path = "/" + "/".join(parents)
            output[folder_path] = asset_doc
        return output

    def get_product_items(self, directory):
        """

        Returns:
            list[ProductItem]: List of ingest files for the given directory
        """
        product_items = []
        if not directory or not os.path.exists(directory):
            return product_items
        # project_name = self._selected_project_name
        # project_settings = get_project_settings(project_name)
        # file_mappings = project_settings["batchpublisher"].get(
        #     "file_mappings", [])
        file_mappings = FILE_MAPPINGS
        for file_mapping in file_mappings:
            product_type = file_mapping["product_type"]
            glob_full_path = directory + "/" + file_mapping["glob"]
            files = glob.glob(glob_full_path, recursive=False)
            for filepath in files:
                filename = os.path.basename(filepath)
                product_name, extension = os.path.splitext(filename)
                # Create representation name from extension
                representation_name = EXT_TO_REP_NAME.get(extension)
                if not representation_name:
                    representation_name = extension.lstrip(".")
                product_item = ProductItem(
                    filepath,
                    product_type,
                    product_name,
                    representation_name)
                product_items.append(product_item)
        return product_items

    def publish_product_items(self, product_items):
        """

        Args:
            product_items (list[ProductItem]): List of ingest files to publish.
        """

        for product_item in product_items:
            if product_item.enabled and product_item.defined:
                self._publish_product_item(product_item)

    def _publish_product_item(self, product_item):
        msg = f"""
Publishing (ingesting): {product_item.filepath}
As Folder (Asset): {product_item.folder_path}
Task: {product_item.task_name}
Product Type (Family): {product_item.product_type}
Product Name (Subset): {product_item.product_name}
Representation: {product_item.representation_name}
Version: {product_item.version}"
Project: {self._selected_project_name}"""
        print(msg)
        publish_data = dict()
        publish_data["version"] = product_item.version
        publish_data["comment"] = product_item.comment
        expected_representations = dict()
        expected_representations[product_item.representation_name] = \
            product_item.filepath
        publish.publish_version_pyblish(
            self._selected_project_name,
            product_item.folder_path,
            product_item.task_name,
            product_item.product_type,
            product_item.product_name,
            expected_representations,
            publish_data)
        # publish.publish_version(
        #     self._selected_project_name,
        #     product_item.folder_path,
        #     product_item.task_name,
        #     product_item.product_type,
        #     product_item.product_name,
        #     expected_representations,
        #     publish_data)
        # publish.publish_version(
        #     project_name,
        #     asset_name,
        #     task_name,
        #     family_name,
        #     subset_name,
        #     expected_representations,
        #     publish_data,
