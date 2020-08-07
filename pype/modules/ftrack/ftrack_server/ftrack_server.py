import os
import sys
import types
import importlib
import ftrack_api
import time
import logging
import inspect
from pype.api import Logger, config


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


class FtrackServer:
    def __init__(self, server_type='action'):
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

        env_key = "FTRACK_ACTIONS_PATH"
        if server_type.lower() == 'event':
            env_key = "FTRACK_EVENTS_PATH"

        self.server_type = server_type
        self.env_key = env_key

    def stop_session(self):
        if self.session.event_hub.connected is True:
            self.session.event_hub.disconnect()
        self.session.close()
        self.session = None

    def set_files(self, paths):
        # Iterate all paths
        register_functions_dict = []
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
                        msg = ('"{}" - Missing register method').format(file)
                        log.warning(msg)
                        continue

                    register_functions_dict.append({
                        'name': file,
                        'register': mod_functions['register']
                    })
                except Exception as e:
                    msg = 'Loading of file "{}" failed ({})'.format(
                        file, str(e)
                    )
                    log.warning(msg, exc_info=e)

        if len(register_functions_dict) < 1:
            log.warning((
                "There are no events with `register` function"
                " in registered paths: \"{}\""
            ).format("| ".join(paths)))

        # Load presets for setting plugins
        key = "user"
        if self.server_type.lower() == "event":
            key = "server"
        plugins_presets = config.get_presets().get(
            "ftrack", {}
        ).get("plugins", {}).get(key, {})

        function_counter = 0
        for function_dict in register_functions_dict:
            register = function_dict["register"]
            try:
                if len(inspect.signature(register).parameters) == 1:
                    register(self.session)
                else:
                    register(self.session, plugins_presets=plugins_presets)

                if function_counter % 7 == 0:
                    time.sleep(0.1)
                function_counter += 1
            except Exception as exc:
                msg = '"{}" - register was not successful ({})'.format(
                    function_dict['name'], str(exc)
                )
                log.warning(msg, exc_info=True)

    def run_server(self, session=None, load_files=True):
        if not session:
            session = ftrack_api.Session(auto_connect_event_hub=True)

        self.session = session

        if load_files:
            paths_str = os.environ.get(self.env_key)
            if paths_str is None:
                log.error((
                    "Env var \"{}\" is not set, \"{}\" server won\'t launch"
                ).format(self.env_key, self.server_type))
                return

            paths = paths_str.split(os.pathsep)
            self.set_files(paths)

            log.info(60*"*")
            log.info('Registration of actions/events has finished!')

        # keep event_hub on session running
        self.session.event_hub.wait()
