import pyblish.api


class CollectHandles(pyblish.api.InstancePlugin):
    """
    OpenPype collector for handling animation-related tasks.
    It checks the include handle settings of the project, determines whether to include/exclude handles
    based on the current task, and initializes handle values accordingly.

    Attributes:
        order (int): The order of execution for this extractor.
        label (str): The label used to identify this extractor.
        families (list): List of families to which this extractor is applicable.
    """
    order = pyblish.api.CollectorOrder + 0.4999999
    label = "Collect Handles"
    families = ["animation",
                "pointcache",
                "camera",
                "proxyAbc",
                "renderlayer",
                "review",
                "yeticache"]

    def process(self, instance):
        # Check the include handle settings of the actual project
        include_handles_settings = instance.context.data["project_settings"]["maya"]["include_handles"]
        current_task = instance.context.data["anatomyData"]["task"]["name"]
        include_task = include_handles_settings["include_handles_default"]

        # Log information about the current task and handle settings
        self.log.info(f"Processing instance: {instance.name}")
        self.log.info(f"Current Task: {current_task}")
        self.log.info(f"Include Handles Default: {include_task}")

        # Define if we had to include/exclude the handles
        for item in include_handles_settings["per_task_type"]:
            if current_task in item["task_type"]:
                include_task = item["include_handles"]
                break

        # if we exclude, initialize handles values to origin(frame start, frame end)
        if not include_task:
            instance.context.data["frameStartHandle"] = int(instance.context.data.get("frameStart"))
            instance.context.data["frameEndHandle"] = int(instance.context.data.get("frameEnd"))
            instance.context.data["handleStart"] = 0
            instance.context.data["handleEnd"] = 0

            # Log information about the handle values initialization
            self.log.info("Handles excluded.")

        self.log.info(f"Frame Start Handle: {instance.context.data['frameStartHandle']}")
        self.log.info(f"Frame End Handle: {instance.context.data['frameEndHandle']}")
        self.log.info(f"Handle Start: {instance.context.data['handleStart']}")
        self.log.info(f"Handle End: {instance.context.data['handleEnd']}")
