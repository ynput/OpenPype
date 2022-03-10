import pyblish.api
from avalon import io

from openpype.pipeline import PublishXmlValidationError


class ValidateTaskExistence(pyblish.api.ContextPlugin):
    """Validating tasks on instances are filled and existing."""

    label = "Validate Task Existence"
    order = pyblish.api.ValidatorOrder

    hosts = ["standalonepublisher"]
    families = ["render_mov_batch"]

    def process(self, context):
        asset_names = set()
        for instance in context:
            asset_names.add(instance.data["asset"])

        asset_docs = io.find(
            {
                "type": "asset",
                "name": {"$in": list(asset_names)}
            },
            {
                "name": 1,
                "data.tasks": 1
            }
        )
        tasks_by_asset_names = {}
        for asset_doc in asset_docs:
            asset_name = asset_doc["name"]
            asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
            tasks_by_asset_names[asset_name] = list(asset_tasks.keys())

        missing_tasks = []
        for instance in context:
            asset_name = instance.data["asset"]
            task_name = instance.data["task"]
            task_names = tasks_by_asset_names.get(asset_name) or []
            if task_name and task_name in task_names:
                continue
            missing_tasks.append((asset_name, task_name))

        # Everything is OK
        if not missing_tasks:
            return

        # Raise an exception
        msg = "Couldn't find task name/s required for publishing.\n{}"
        pair_msgs = []
        for missing_pair in missing_tasks:
            pair_msgs.append(
                "Asset: \"{}\" Task: \"{}\"".format(*missing_pair)
            )

        msg = msg.format("\n".join(pair_msgs))

        formatting_data = {"task_not_found": '    - {}'.join(pair_msgs)}
        if pair_msgs:
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
