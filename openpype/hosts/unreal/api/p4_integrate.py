from __future__ import annotations
import json
import time
from P4 import P4, P4Exception
from enum import Enum
from openpype.settings import get_project_settings
import asyncio
from aiohttp_json_rpc import JsonRpcClientContext
from openpype.modules import ModulesManager
from openpype.pipeline import get_current_project_name


class P4Integrate:
    P4_openpype_changelist = None

    def __init__(self, project_name: str):
        settings = get_project_settings(project_name)
        self.settings = settings["p4v"]["general"]
        self.client = self.settings["client"]
        self.port = self.settings["port"]
        self.user = self.settings["user"]
        self.project_name = project_name

    async def p4_run(self, command: P4AvailableCommandsEnum.value, args: list, client_required: bool = True):
        manager = ModulesManager()
        perforce_module = manager.modules_by_name["perforce"]

        port = perforce_module.port
        project_name = get_current_project_name()

        async with JsonRpcClientContext(f"ws://localhost:{port}/rpc") as jrpc:
            method_res = await jrpc.p4_run(project_name, command, *args, client_required)

        return method_res

    async def p4_get_default_changelist(self, changelist_desc: str, changelist_identity: str | None,
                                        changelist_files: list[str] | None = None):

        manager = ModulesManager()
        perforce_module = manager.modules_by_name["perforce"]
        port = perforce_module.port
        project_name = get_current_project_name()

        async with JsonRpcClientContext(f"ws://localhost:{port}/rpc") as jrpc:
            method_res = await jrpc.p4_create_or_load_openpype_changelist(
                project_name, changelist_desc,
                changelist_identity, changelist_files
            )
        return method_res




    def p4_create_or_load_openpype_changelist(
            self, changelist_desc: str, changelist_identity: str | None,
            changelist_files: list[str] | None = None):

        try:
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

                    new_changelist = asyncio.get_event_loop().run_until_complete(
                        self.p4_get_default_changelist(
                            changelist_desc,
                            custom_identity.get_identity_as_json(),
                            changelist_files

                        )
                    )

                    self.P4_openpype_changelist = new_changelist
            return self.P4_openpype_changelist
        except Exception as e:
            raise Exception(e) from e

    def p4_get_changelist_by_identity(self, identity: str):
        try:
            changelists = asyncio.get_event_loop().run_until_complete(
                self.p4_run(P4AvailableCommandsEnum.CHANGES.value, [])
            )
            for changelist in changelists:
                if "changeIdentity" in changelist:
                    if changelist["changeIdentity"] == identity:
                        return changelist["change"]
            return None
        except P4Exception as e:
            raise P4Exception(e) from e

    def p4_get_changelist_for_source_app_and_target_env(
            self, source_app_name: str, target_env: str):
        try:

            loop = asyncio.get_event_loop()


            for changelist in loop.run_until_complete(
                self.p4_run("changes", [])
            ):
                if changelist['status'] != P4ChangelistStatusEnum.SUBMITTED.value:
                    if self.is_json(changelist["changeIdentity"]):
                        parsed_json = json.loads(changelist['changeIdentity'])
                        if "sourceApp" in parsed_json and "targetEnv" in parsed_json:
                            if parsed_json["sourceApp"] == source_app_name and parsed_json[
                                "targetEnv"] == target_env:  # noqa
                                return changelist["change"]
            return None
        except Exception as e:
            raise Exception(e) from e

    @staticmethod
    def is_json(string_to_check: str):
        try:
            json.loads(string_to_check)
            return True
        except ValueError:
            return False


class P4AvailableCommandsEnum(Enum):
    CHANGES = "changes"
    CHANGE = "change"
    CLIENTS = "clients"
    SUBMIT = "submit"
    ADD = "add"
    EDIT = "edit"
    REVERT = "revert"
    FILES = "files"


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
