import os
import sys
import types
import importlib
from pype.vendor import ftrack_api
import time
import logging
from pypeapp import Logger

log = Logger().get_logger(__name__)

"""
# Required - Needed for connection to Ftrack
FTRACK_SERVER # Ftrack server e.g. "https://myFtrack.ftrackapp.com"
FTRACK_API_KEY # Ftrack user's API key "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
FTRACK_API_USER # Ftrack username e.g. "user.name"

# Required - Paths to folder with actions
FTRACK_ACTIONS_PATH # Paths to folders where are located actions
    - EXAMPLE: "M:/FtrackApi/../actions/"
FTRACK_EVENTS_PATH # Paths to folders where are located actions
    - EXAMPLE: "M:/FtrackApi/../events/"

# Required - Needed for import included modules
PYTHONPATH # Path to ftrack_api and paths to all modules used in actions
    - path to ftrack_action_handler, etc.
"""


class FtrackServer():
    def __init__(self, type='action'):
        """
            - 'type' is by default set to 'action' - Runs Action server
            - enter 'event' for Event server

            EXAMPLE FOR EVENT SERVER:
                ...
                server = FtrackServer('event')
                server.run_server()
                ..
        """
        # set Ftrack logging to Warning only - OPTIONAL
        ftrack_log = logging.getLogger("ftrack_api")
        ftrack_log.setLevel(logging.WARNING)

        self.type = type
        self.actionsAvailable = True
        self.eventsAvailable = True
        # Separate all paths
        if "FTRACK_ACTIONS_PATH" in os.environ:
            all_action_paths = os.environ["FTRACK_ACTIONS_PATH"]
            self.actionsPaths = all_action_paths.split(os.pathsep)
        else:
            self.actionsAvailable = False

        if "FTRACK_EVENTS_PATH" in os.environ:
            all_event_paths = os.environ["FTRACK_EVENTS_PATH"]
            self.eventsPaths = all_event_paths.split(os.pathsep)
        else:
            self.eventsAvailable = False

    def stop_session(self):
        if self.session.event_hub.connected is True:
            self.session.event_hub.disconnect()
        self.session.close()
        self.session = None

    def set_files(self, paths):
        # Iterate all paths
        functions = []
        for path in paths:
            # add path to PYTHON PATH
            if path not in sys.path:
                sys.path.append(path)

            # Get all modules with functions
            for file in os.listdir(path):
                # Get only .py files with action functions
                try:
                    if '.pyc' in file or '.py' not in file:
                        continue

                    mod = importlib.import_module(os.path.splitext(file)[0])
                    importlib.reload(mod)
                    mod_functions = dict(
                        [
                            (name, function)
                            for name, function in mod.__dict__.items()
                            if isinstance(function, types.FunctionType)
                        ]
                    )

                    # separate files by register function
                    if 'register' not in mod_functions:
                        msg = (
                            '"{0}" - Missing register method'
                        ).format(file, self.type)
                        log.warning(msg)
                        continue

                    functions.append({
                        'name': file,
                        'register': mod_functions['register']
                    })
                except Exception as e:
                    msg = 'Loading of file "{}" failed ({})'.format(
                        file, str(e)
                    )
                    log.warning(msg)

        if len(functions) < 1:
            raise Exception

        function_counter = 0
        for function in functions:
            try:
                function['register'](self.session)
                if function_counter%7 == 0:
                    time.sleep(0.1)
                function_counter += 1
            except Exception as e:
                msg = '"{}" - register was not successful ({})'.format(
                    function['name'], str(e)
                )
                log.warning(msg)

    def run_server(self):
        self.session = ftrack_api.Session(auto_connect_event_hub=True,)

        if self.type.lower() == 'event':
            if self.eventsAvailable is False:
                msg = (
                    'FTRACK_EVENTS_PATH is not set'
                    ', event server won\'t launch'
                )
                log.error(msg)
                return
            self.set_files(self.eventsPaths)
        else:
            if self.actionsAvailable is False:
                msg = (
                    'FTRACK_ACTIONS_PATH is not set'
                    ', action server won\'t launch'
                )
                log.error(msg)
                return
            self.set_files(self.actionsPaths)

        log.info(60*"*")
        log.info('Registration of actions/events has finished!')

        # keep event_hub on session running
        self.session.event_hub.wait()
