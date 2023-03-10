from __future__ import annotations
import json, time
from P4 import P4, P4Exception
from enum import Enum
from openpype.settings import get_project_settings


class P4Integrate:
    p4Connection = None
    p4OpenPypeChangelist = None

    def __init__(self, project_name: str):
        settings = get_project_settings(project_name)
        self.settings = settings["p4v"]["general"]
        self.client = self.settings["client"]
        self.port = self.settings["port"]
        self.user = self.settings["user"]
        self.project_name = project_name


    def P4VConnect(self):
        try:
            if self.p4Connection is None:
                p4 = P4()
                p4.client = self.client
                p4.port = self.port
                p4.user = self.user
                p4.connect()

                self.p4Connection = p4
            return self.p4Connection
        except P4Exception as e:
            raise P4Exception(e)

    def P4VCreateOrLoadOpenPypeChangelist(self, changeListDesc: str,
                                          changeListIdentity: str | None,
                                          changeListFiles: list[str] | None = None):
        try:
            p4 = self.P4VConnect()

            if changeListFiles is None:
                changeListFiles = []

            if changeListIdentity is not None:
                changelist = self.P4VGetChangelistByIdentity(changeListIdentity)
                self.p4OpenPypeChangelist = changelist

            if self.p4OpenPypeChangelist is None:
                existingChangelist = self.P4VGetChangelistForSourceAppAndTargetEnv(P4CustomIdentity.sourceApp,
                                                                                   P4CustomIdentity.targetEnv)

                if existingChangelist is not None:
                    self.p4OpenPypeChangelist = existingChangelist
                else:
                    currentTimestamp = round(time.time() * 1000)
                    customIdentity = P4CustomIdentity(self.project_name, str(currentTimestamp))

                    change = p4.fetch_change()
                    change._identity = customIdentity.getIdentityAsJson()
                    change._description = changeListDesc
                    change._files = changeListFiles
                    changeList = p4.save_change(change)[0].split(" ")

                    self.p4OpenPypeChangelist = changeList[1]
            return self.p4OpenPypeChangelist
        except Exception as e:
            raise Exception(e)

    def P4VDisconnect(self):
        try:
            p4 = self.p4Connection
            if p4 is not None:
                p4.disconnect()
        except P4Exception as e:
            raise P4Exception(e)

    def P4VGetChangelistByIdentity(self, identity: str):
        try:
            p4 = self.P4VConnect()
            for changelist in p4.run("changes", "-c", p4.client):
                if "changeIdentity" in changelist:
                    if changelist["changeIdentity"] == identity:
                        return changelist["change"]
            return None
        except P4Exception as P4E:
            print(P4E)

    def P4VGetChangelistForSourceAppAndTargetEnv(self, sourceAppName: str, targetEnv: str):
        p4 = self.P4VConnect()

        for changelist in p4.run("changes", "-c", p4.client, "-l"):
            if changelist['status'] != P4ChangelistStatusEnum.SUBMITTED.value:
                if self.IsJson(changelist["desc"]):
                    parsedJson = json.loads(changelist['desc'])
                    if "sourceApp" in parsedJson and "targetEnv" in parsedJson:
                        if parsedJson["sourceApp"] == sourceAppName and parsedJson["targetEnv"] == targetEnv:
                            return changelist["change"]
        return None

    @staticmethod
    def IsJson(stringToCheck: str):
        try:
            json.loads(stringToCheck)
            return True
        except ValueError:
            return False


class P4ChangelistStatusEnum(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    NEW = "new"
    SHELVED = "shelved"


class P4CustomIdentity:
    sourceApp: str = "OpenPype"
    targetEnv: str = "Unreal"

    def __init__(self, projectName, timestamp):
        self.projectName = projectName
        self.timestamp = timestamp

    def getIdHash(self):
        uniqueString = self.projectName + self.timestamp
        return hash(uniqueString)

    def getIdentityAsJson(self):
        jsonString = {
            "id": self.getIdHash(),
            "sourceApp": self.sourceApp,
            "targetEnv": self.targetEnv
        }

        return json.dumps(jsonString)
