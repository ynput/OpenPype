import os
import json
import collections


class HostContext:
    json_path = None

    @classmethod
    def add_instance(cls, instance):
        instances = cls.get_instances()
        instances.append(instance)
        cls.save_instances(instances)

    @classmethod
    def save_instances(cls, instances):
        json_path = cls.get_json_path()
        with open(json_path, "w") as json_stream:
            json.dump(instances, json_stream, indent=4)

    @classmethod
    def get_json_path(cls):
        if cls.json_path is None:
            cls.json_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "instances.json"
            )
        return cls.json_path

    @classmethod
    def get_instances(cls):
        json_path = cls.get_json_path()
        if not os.path.exists(json_path):
            instances = []
            with open(json_path, "w") as json_stream:
                json.dump(json_stream, instances)
        else:
            with open(json_path, "r") as json_stream:
                instances = json.load(json_stream)
        return instances


def ls():
    return []


def list_instances():
    return HostContext.get_instances()


def update_instances(update_list):
    current_instances = HostContext.get_instances()

    for instance, _changes in update_list:
        instance_id = instance.data["uuid"]

        found_idx = None
        for idx, current_instance in enumerate(current_instances):
            if instance_id == current_instance["uuid"]:
                found_idx = idx
                break

        if found_idx is None:
            return

        current_instances[found_idx] = instance.data_to_store()
    HostContext.save_instances(current_instances)


def remove_instances(instances):
    if not isinstance(instances, (tuple, list)):
        instances = [instances]

    current_instances = HostContext.get_instances()
    for instance in instances:
        instance_id = instance.data["uuid"]
        found_idx = None
        for idx, _instance in enumerate(current_instances):
            if instance_id == _instance["uuid"]:
                found_idx = idx
                break

        if found_idx is not None:
            current_instances.pop(found_idx)
    HostContext.save_instances(current_instances)
