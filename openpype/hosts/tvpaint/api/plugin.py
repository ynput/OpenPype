from openpype.api import PypeCreatorMixin
from avalon.tvpaint import pipeline


class Creator(PypeCreatorMixin, pipeline.Creator):
    @classmethod
    def get_dynamic_data(cls, *args, **kwargs):
        dynamic_data = super(Creator, cls).get_dynamic_data(*args, **kwargs)

        # Change asset and name by current workfile context
        workfile_context = pipeline.get_current_workfile_context()
        asset_name = workfile_context.get("asset")
        task_name = workfile_context.get("task")
        if "asset" not in dynamic_data and asset_name:
            dynamic_data["asset"] = asset_name

        if "task" not in dynamic_data and task_name:
            dynamic_data["task"] = task_name
        return dynamic_data
