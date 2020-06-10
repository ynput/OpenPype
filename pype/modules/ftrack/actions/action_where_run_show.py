import platform
import socket
import getpass
from pype.modules.ftrack.lib import BaseAction


class ActionShowWhereIRun(BaseAction):
    """ Sometimes user forget where pipeline with his credentials is running.
    - this action shows on which PC, Username and IP is running
    - requirement action MUST be registered where we want to locate the PC:
    - - can't be used retrospectively...
    """
    #: Action identifier.
    identifier = 'show.where.i.run'
    #: Action label.
    label = 'Show where I run'
    #: Action description.
    description = 'Shows PC info where user have running Pype'

    def discover(self, session, entities, event):
        """ Hide by default - Should be enabled only if you want to run.
        - best practise is to create another action that triggers this one
        """

        return False

    def launch(self, session, entities, event):
        # Don't show info when was launch from this session
        if session.event_hub.id == event.get("data", {}).get("event_hub_id"):
            return True

        title = "Where Do I Run?"
        msgs = {}
        all_keys = ["Hostname", "IP", "Username", "System name", "PC name"]
        try:
            host_name = socket.gethostname()
            msgs["Hostname"] = host_name
            host_ip = socket.gethostbyname(host_name)
            msgs["IP"] = host_ip
        except Exception:
            pass

        try:
            system_name, pc_name, *_ = platform.uname()
            msgs["System name"] = system_name
            msgs["PC name"] = pc_name
        except Exception:
            pass

        try:
            msgs["Username"] = getpass.getuser()
        except Exception:
            pass

        for key in all_keys:
            if not msgs.get(key):
                msgs[key] = "-Undefined-"

        items = []
        first = True
        splitter = {'type': 'label', 'value': '---'}
        for key, value in msgs.items():
            if first:
                first = False
            else:
                items.append(splitter)
            self.log.debug("{}: {}".format(key, value))

            subtitle = {'type': 'label', 'value': '<h3>{}</h3>'.format(key)}
            items.append(subtitle)
            message = {'type': 'label', 'value': '<p>{}</p>'.format(value)}
            items.append(message)

        self.show_interface(items, title, event=event)

        return True


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    ActionShowWhereIRun(session, plugins_presets).register()
