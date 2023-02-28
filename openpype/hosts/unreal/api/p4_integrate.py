from P4 import P4, P4Exception


class P4Integrate:
    p4Connection = None
    p4OpenPypeChangelist = None
    client = "PLACE YOUR NAME OF EXISTING WORKSPACE"
    port = "PLACE YOUR ADDRESS WITH PORT"
    user = "PLACE YOUR USERNAME"


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

    def P4VCreateDefaultChangelist(self, changeListDesc: str, changeListFiles=None):

        p4 = self.P4VConnect()

        if changeListFiles is None:
            changeListFiles = []

        if p4 is None:
            p4 = self.P4VConnect()

        try:
            change = p4.fetch_change()
            change._identity = "openpype-changelist"
            change._description = changeListDesc
            change._files = changeListFiles
            changeList = p4.save_change(change)[0].split(" ")

            self.p4OpenPypeChangelist = changeList[1]

            return change
        except Exception as e:
            raise Exception(e)

    def P4VDisconnect(self):
        p4 = self.p4Connection
        try:
            if p4 is not None:
                p4.disconnect()
        except P4Exception as e:
            raise P4Exception(e)
