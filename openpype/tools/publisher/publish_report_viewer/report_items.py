import uuid
import collections
import copy


class PluginItem:
    def __init__(self, plugin_data):
        self._id = uuid.uuid4()

        self.name = plugin_data["name"]
        self.label = plugin_data["label"]
        self.order = plugin_data["order"]
        self.skipped = plugin_data["skipped"]
        self.passed = plugin_data["passed"]

        errored = False
        for instance_data in plugin_data["instances_data"]:
            for log_item in instance_data["logs"]:
                errored = log_item["type"] == "error"
                if errored:
                    break
            if errored:
                break

        self.errored = errored

    @property
    def id(self):
        return self._id


class InstanceItem:
    def __init__(self, instance_id, instance_data, logs_by_instance_id):
        self._id = instance_id
        self.label = instance_data.get("label") or instance_data.get("name")
        self.family = instance_data.get("family")
        self.removed = not instance_data.get("exists", True)

        logs = logs_by_instance_id.get(instance_id) or []
        errored = False
        for log_item in logs:
            if log_item.errored:
                errored = True
                break

        self.errored = errored

    @property
    def id(self):
        return self._id


class LogItem:
    def __init__(self, log_item_data, plugin_id, instance_id):
        self._instance_id = instance_id
        self._plugin_id = plugin_id
        self._errored = log_item_data["type"] == "error"
        self.data = log_item_data

    def __getitem__(self, key):
        return self.data[key]

    @property
    def errored(self):
        return self._errored

    @property
    def instance_id(self):
        return self._instance_id

    @property
    def plugin_id(self):
        return self._plugin_id


class PublishReport:
    def __init__(self, report_data):
        data = copy.deepcopy(report_data)

        context_data = data["context"]
        context_data["name"] = "context"
        context_data["label"] = context_data["label"] or "Context"

        logs = []
        plugins_items_by_id = {}
        plugins_id_order = []
        for plugin_data in data["plugins_data"]:
            item = PluginItem(plugin_data)
            plugins_id_order.append(item.id)
            plugins_items_by_id[item.id] = item
            for instance_data_item in plugin_data["instances_data"]:
                instance_id = instance_data_item["id"]
                for log_item_data in instance_data_item["logs"]:
                    log_item = LogItem(
                        copy.deepcopy(log_item_data), item.id, instance_id
                    )
                    logs.append(log_item)

        logs_by_instance_id = collections.defaultdict(list)
        for log_item in logs:
            logs_by_instance_id[log_item.instance_id].append(log_item)

        instance_items_by_id = {}
        instance_items_by_family = {}
        context_item = InstanceItem(None, context_data, logs_by_instance_id)
        instance_items_by_id[context_item.id] = context_item
        instance_items_by_family[context_item.family] = [context_item]

        for instance_id, instance_data in data["instances"].items():
            item = InstanceItem(
                instance_id, instance_data, logs_by_instance_id
            )
            instance_items_by_id[item.id] = item
            if item.family not in instance_items_by_family:
                instance_items_by_family[item.family] = []
            instance_items_by_family[item.family].append(item)

        self.instance_items_by_id = instance_items_by_id
        self.instance_items_by_family = instance_items_by_family

        self.plugins_id_order = plugins_id_order
        self.plugins_items_by_id = plugins_items_by_id

        self.logs = logs

        self.crashed_plugin_paths = report_data["crashed_file_paths"]
