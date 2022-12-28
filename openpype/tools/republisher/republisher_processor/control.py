import requests


class PublishItem:
    def __init__(
        self,
        src_project_name,
        src_representation_id,
        dst_project_name,
        dst_asset_id,
        dst_task_name
    ):
        self.src_project_name = src_project_name
        self.src_representation_id = src_representation_id
        self.dst_project_name = dst_project_name
        self.dst_asset_id = dst_asset_id
        self.dst_task_name = dst_task_name


class RepublisherController:
    def __init__(self):
        pass


