from __future__ import annotations
import json
import time
from P4 import P4, P4Exception
from enum import Enum
from openpype.settings import get_project_settings


class P4Integrate:
    P4_connection = None
    P4_openpype_changelist = None

    def __init__(self, project_name: str):
        settings = get_project_settings(project_name)
        self.settings = settings["p4v"]["general"]
        self.client = self.settings["client"]
        self.port = self.settings["port"]
        self.user = self.settings["user"]
        self.project_name = project_name

    def p4_connect(self):
        try:
            if self.P4_connection is None:
                p4 = P4()
                p4.client = self.client
                p4.port = self.port
                p4.user = self.user
                p4.connect()

                self.P4_connection = p4
            return self.P4_connection
        except P4Exception as e:
            raise P4Exception(e) from e

    def p4_create_or_load_openpype_changelist(
            self, changelist_desc: str, changelist_identity: str | None,
            changelist_files: list[str] | None = None):
        try:
            p4 = self.p4_connect()

            if changelist_files is None:
                changelist_files = []

            if changelist_identity is not None:
                changelist = self.p4_get_changelist_by_identity(changelist_identity)  # noqa: E501
                self.P4_openpype_changelist = changelist

            if self.P4_openpype_changelist is None:
                existing_changelist = self.p4_get_changelist_for_source_app_and_target_env(  # noqa: E501
                    P4CustomIdentity.source_app, P4CustomIdentity.target_env)

                if existing_changelist is not None:
                    self.P4_openpype_changelist = existing_changelist
                else:
                    current_timestamp = round(time.time() * 1000)
                    custom_identity = P4CustomIdentity(
                        self.project_name, str(current_timestamp))

                    change = p4.fetch_change()
                    change._identity = custom_identity.get_identity_as_json()
                    change._description = changelist_desc
                    change._files = changelist_files
                    changelist = p4.save_change(change)[0].split(" ")

                    self.P4_openpype_changelist = changelist[1]
            return self.P4_openpype_changelist
        except Exception as e:
            raise Exception(e) from e

    def p4_disconnect(self):
        try:
            p4 = self.P4_connection
            if p4 is not None:
                p4.disconnect()
        except P4Exception as e:
            raise P4Exception(e) from e

    def p4_get_changelist_by_identity(self, identity: str):
        try:
            p4 = self.p4_connect()
            for changelist in p4.run("changes", "-c", p4.client):
                if "changeIdentity" in changelist:
                    if changelist["changeIdentity"] == identity:
                        return changelist["change"]
            return None
        except P4Exception as P4E:
            print(P4E)

    def p4_get_changelist_for_source_app_and_target_env(
            self, source_app_name: str, target_env: str):
        p4 = self.p4_connect()

        for changelist in p4.run("changes", "-c", p4.client, "-l"):
            if changelist['status'] != P4ChangelistStatusEnum.SUBMITTED.value:
                if self.is_json(changelist["desc"]):
                    parsed_json = json.loads(changelist['desc'])
                    if "sourceApp" in parsed_json and "targetEnv" in parsed_json:
                        if parsed_json["sourceApp"] == source_app_name and parsed_json["targetEnv"] == target_env:  # noqa
                            return changelist["change"]
        return None

    @staticmethod
    def is_json(string_to_check: str):
        try:
            json.loads(string_to_check)
            return True
        except ValueError:
            return False


class P4ChangelistStatusEnum(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    NEW = "new"
    SHELVED = "shelved"


class P4CustomIdentity:
    source_app: str = "OpenPype"
    target_env: str = "Unreal"

    def __init__(self, project_name, timestamp):
        self.project_name = project_name
        self.timestamp = timestamp

    def get_id_hash(self):
        unique_str = self.project_name + self.timestamp
        return hash(unique_str)

    def get_identity_as_json(self):
        json_string = {
            "id": self.get_id_hash(),
            "sourceApp": self.source_app,
            "targetEnv": self.target_env
        }

        return json.dumps(json_string)
