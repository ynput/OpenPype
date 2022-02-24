import os
import json


class HostContext:
    instances_json_path = None
    context_json_path = None

    @classmethod
    def get_context_title(cls):
        project_name = os.environ.get("AVALON_PROJECT")
        if not project_name:
            return "TestHost"

        asset_name = os.environ.get("AVALON_ASSET")
        if not asset_name:
            return project_name

        from avalon import io

        asset_doc = io.find_one(
            {"type": "asset", "name": asset_name},
            {"data.parents": 1}
        )
        parents = asset_doc.get("data", {}).get("parents") or []

        hierarchy = [project_name]
        hierarchy.extend(parents)
        hierarchy.append("<b>{}</b>".format(asset_name))
        task_name = os.environ.get("AVALON_TASK")
        if task_name:
            hierarchy.append(task_name)

        return "/".join(hierarchy)

    @classmethod
    def get_current_dir_filepath(cls, filename):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            filename
        )

    @classmethod
    def get_instances_json_path(cls):
        if cls.instances_json_path is None:
            cls.instances_json_path = cls.get_current_dir_filepath(
                "instances.json"
            )
        return cls.instances_json_path

    @classmethod
    def get_context_json_path(cls):
        if cls.context_json_path is None:
            cls.context_json_path = cls.get_current_dir_filepath(
                "context.json"
            )
        return cls.context_json_path

    @classmethod
    def add_instance(cls, instance):
        instances = cls.get_instances()
        instances.append(instance)
        cls.save_instances(instances)

    @classmethod
    def save_instances(cls, instances):
        json_path = cls.get_instances_json_path()
        with open(json_path, "w") as json_stream:
            json.dump(instances, json_stream, indent=4)

    @classmethod
    def get_instances(cls):
        json_path = cls.get_instances_json_path()
        if not os.path.exists(json_path):
            instances = []
            with open(json_path, "w") as json_stream:
                json.dump(json_stream, instances)
        else:
            with open(json_path, "r") as json_stream:
                instances = json.load(json_stream)
        return instances

    @classmethod
    def get_context_data(cls):
        json_path = cls.get_context_json_path()
        if not os.path.exists(json_path):
            data = {}
            with open(json_path, "w") as json_stream:
                json.dump(data, json_stream)
        else:
            with open(json_path, "r") as json_stream:
                data = json.load(json_stream)
        return data

    @classmethod
    def save_context_data(cls, data):
        json_path = cls.get_context_json_path()
        with open(json_path, "w") as json_stream:
            json.dump(data, json_stream, indent=4)


def ls():
    return []


def list_instances():
    return HostContext.get_instances()


def update_instances(update_list):
    updated_instances = {}
    for instance, _changes in update_list:
        updated_instances[instance.id] = instance.data_to_store()

    instances = HostContext.get_instances()
    for instance_data in instances:
        instance_id = instance_data["instance_id"]
        if instance_id in updated_instances:
            new_instance_data = updated_instances[instance_id]
            old_keys = set(instance_data.keys())
            new_keys = set(new_instance_data.keys())
            instance_data.update(new_instance_data)
            for key in (old_keys - new_keys):
                instance_data.pop(key)

    HostContext.save_instances(instances)


def remove_instances(instances):
    if not isinstance(instances, (tuple, list)):
        instances = [instances]

    current_instances = HostContext.get_instances()
    for instance in instances:
        instance_id = instance.data["instance_id"]
        found_idx = None
        for idx, _instance in enumerate(current_instances):
            if instance_id == _instance["instance_id"]:
                found_idx = idx
                break

        if found_idx is not None:
            current_instances.pop(found_idx)
    HostContext.save_instances(current_instances)


def get_context_data():
    return HostContext.get_context_data()


def update_context_data(data, changes):
    HostContext.save_context_data(data)


def get_context_title():
    return HostContext.get_context_title()
