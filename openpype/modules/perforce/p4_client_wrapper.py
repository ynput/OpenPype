from __future__ import annotations
import json
from P4 import P4, P4Exception
from openpype.settings import get_project_settings


class P4ClientWrapper(object):
    P4_connection = None

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

    def p4_run(self, command: str, args: list,
               client_required: bool = True):
        try:
            p4 = self.p4_connect()

            if client_required:
                p4.run(command, "-c", p4.client, *args)
            else:
                p4.run(command, *args)

        except P4Exception as e:
            raise Exception(e) from e
        finally:
            self.p4_disconnect()

    def p4_create_or_load_openpype_changelist(
            self, changelist_desc: str, changelist_identity: str | None,
            changelist_files: list[str] | None = None):
        try:
            p4 = self.p4_connect()
            change = p4.fetch_change()
            change._identity = changelist_identity
            change._description = changelist_desc
            change._files = changelist_files
            changelist = p4.save_change(change)[0].split(" ")
            return changelist[1]
        except P4Exception as e:
            raise Exception(e) from e
        finally:
            self.p4_disconnect()

    def p4_disconnect(self):
        try:
            p4 = self.P4_connection
            if p4 is not None:
                p4.disconnect()
        except P4Exception as e:
            raise P4Exception(e) from e

    def dict_arguments_to_string(self, args: dict):
        arguments_string = None

        for key, value in args.items():
            arguments_string += f"-{key} {value} "

        return arguments_string

    @staticmethod
    def is_json(string_to_check: str):
        try:
            json.loads(string_to_check)
            return True
        except ValueError:
            return False
