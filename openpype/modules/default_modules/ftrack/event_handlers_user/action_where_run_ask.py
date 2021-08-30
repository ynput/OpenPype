import platform
import socket
import getpass

from openpype_modules.ftrack.lib import BaseAction


class ActionWhereIRun(BaseAction):
    """Show where same user has running OpenPype instances."""

    identifier = "ask.where.i.run"
    show_identifier = "show.where.i.run"
    label = "OpenPype Admin"
    variant = "- Where I run"
    description = "Show PC info where user have running OpenPype"

    def _discover(self, _event):
        return {
            "items": [{
                "label": self.label,
                "variant": self.variant,
                "description": self.description,
                "actionIdentifier": self.discover_identifier,
                "icon": self.icon,
            }]
        }

    def _launch(self, event):
        self.trigger_action(self.show_identifier, event)

    def register(self):
        # Register default action callbacks
        super(ActionWhereIRun, self).register()

        # Add show identifier
        show_subscription = (
            "topic=ftrack.action.launch"
            " and data.actionIdentifier={}"
            " and source.user.username={}"
        ).format(
            self.show_identifier,
            self.session.api_user
        )
        self.session.event_hub.subscribe(
            show_subscription,
            self._show_info
        )

    def _show_info(self, event):
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
        separator = {"type": "label", "value": "---"}
        for key, value in msgs.items():
            if first:
                first = False
            else:
                items.append(separator)
            self.log.debug("{}: {}".format(key, value))

            subtitle = {"type": "label", "value": "<h3>{}</h3>".format(key)}
            items.append(subtitle)
            message = {"type": "label", "value": "<p>{}</p>".format(value)}
            items.append(message)

        self.show_interface(items, title, event=event)


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    ActionWhereIRun(session).register()
