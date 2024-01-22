

from openpype.client.entities import (
    get_assets,
    get_asset_by_name)
from openpype.hosts.batchpublisher import publish


class BatchPublisherController(object):

    def __init__(self):
        self._project_name = list()
        self._folder_names = []
        from openpype.hosts.batchpublisher.models. \
            batch_publisher_model import BatchPublisherModel
        self.model = BatchPublisherModel(self)

    @property
    def project_name(self):
        return self._project_name

    @project_name.setter
    def project_name(self, project_name):
        msg = "Project name changed to: {}".format(project_name)
        print(msg)
        self._project_name = project_name
        # Update cache of asset names for project
        # self._folder_names = [
        #     "assets",
        #     "assets/myasset",
        #     "assets/myasset/mytest"]
        self._folder_names = list()
        assets = get_assets(project_name)
        for asset in assets:
            asset_name = "/".join(asset["data"]["parents"])
            asset_name += "/" + asset["name"]
            self._folder_names.append(asset_name)
        # Clear the existing picked folder names, since project changed
        self.model._change_project(project_name)

    @property
    def folder_names(self):
        return self._folder_names

    @property
    def ingest_filepaths(self):
        return self.model.ingest_filepaths

    def populate_from_directory(self, directory):
        self.model.populate_from_directory(directory)

    def publish(self):
        self.model.publish()

    def publish_ingest_file(self, ingest_file):
        if not ingest_file.enabled:
            print("Skipping publish, not enabled: " + ingest_file.filepath)
            return
        if not ingest_file.defined:
            print("Skipping publish, not defined: " + ingest_file.filepath)
            return
        msg = f"""
Publishing (ingesting): {ingest_file.filepath}
As Folder (Asset): {ingest_file.folder_path}
Task: {ingest_file.task_name}
Product Type (Family): {ingest_file.product_type}
Product Name (Subset): {ingest_file.product_name}
Representation: {ingest_file.representation_name}
Version: {ingest_file.version}"
Project: {self._project}"""
        print(msg)
        publish_data = dict()
        expected_representations = dict()
        expected_representations[ingest_file.representation_name] = \
            ingest_file.filepath
        publish.publish_version(
            self._project,
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

    def _cache_task_names(self, ingest_file):
        if not ingest_file.folder_path:
            ingest_file.task_name = str()
            return
        asset_doc = get_asset_by_name(
            self._project_name,
            ingest_file.folder_path)
        if not asset_doc:
            ingest_file.task_name = str()
            return
        # Since we have the tasks available for the asset (folder) cache it now
        ingest_file.task_names = list(asset_doc["data"]["tasks"].keys())
        # Default to the first task available
        if not ingest_file.task_name and ingest_file.task_names:
            ingest_file.task_name = ingest_file.task_names[0]
