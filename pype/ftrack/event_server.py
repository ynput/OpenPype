import sys
from pype.ftrack import credentials, login_dialog as login_dialog
from FtrackServer import FtrackServer
from app.vendor.Qt import QtWidgets
from pype import api

log = api.Logger.getLogger(__name__, "ftrack-event-server")


class EventServer:
    def __init__(self):
        self.login_widget = login_dialog.Login_Dialog_ui(self)
        self.event_server = FtrackServer('event')

        cred = credentials._get_credentials()

        if 'username' in cred and 'apiKey' in cred:
            self.login_widget.user_input.setText(cred['username'])
            self.login_widget.api_input.setText(cred['apiKey'])

        self.login_widget.setError("Credentials should be for API User")

        self.login_widget.show()

    def loginChange(self):
        log.info("Logged successfully")
        self.login_widget.close()
        self.event_server.run_server()


def main():
    app = QtWidgets.QApplication(sys.argv)
    event = EventServer()
    sys.exit(app.exec_())


if (__name__ == ('__main__')):
    main()
