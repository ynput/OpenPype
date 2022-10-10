"""

psutil 'process_iter' parameters:
'cmdline', 'connections', 'cpu_affinity', 'cpu_num', 'cpu_percent',
'cpu_times', 'create_time', 'cwd', 'environ', 'exe', 'gids', 'io_counters',
'ionice', 'memory_full_info', 'memory_info', 'memory_maps', 'memory_percent',
'name', 'nice', 'num_ctx_switches', 'num_fds', 'num_handles', 'num_threads',
'open_files', 'pid', 'ppid', 'status', 'terminal', 'threads', 'uids', 'username'

"""

import os
import click

import threading
import ctypes
import platform

#TODO: Move psutil to OpenPype (add to dependencies)?
# Or better to keep dependencies here as module is optional?
import sys
if sys.version_info.major == 3:
    from .vendor import psutil
else:
    from openpype.api import Logger
    log = Logger().get_logger("ProcessMonitor")
    log.warning("Module not supported in Python 2, operations will fail.")


from openpype.modules import (
    JsonFilesSettingsDef,
    OpenPypeAddOn,
    ModulesManager
)
from openpype_interfaces import (
    IPluginPaths,
    ITrayAction
)
######## PLUGINS_PATHS - MID
#from openpype.lib import get_plugins_path
######## PLUGINS_PATHS - END

from openpype.api import get_anatomy_settings, get_system_settings


#TODO: Add settings (?)
# Settings definition of this addon using `JsonFilesSettingsDef`
# - JsonFilesSettingsDef is prepared settings definition using json files
#   to define settings and store default values
class AddonSettingsDef(JsonFilesSettingsDef):
    # This will add prefixes to every schema and template from `schemas`
    #   subfolder.
    # - it is not required to fill the prefix but it is highly
    #   recommended as schemas and templates may have name clashes across
    #   multiple addons
    # - it is also recommended that prefix has addon name in it
    schema_prefix = "process_monitor"

    def get_settings_root_path(self):
        """Implemented abstract class of JsonFilesSettingsDef.

        Return directory path where json files defying addon settings are
        located.
        """
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "settings"
        )


class ProcessMonitor(OpenPypeAddOn, IPluginPaths, ITrayAction):
    """Addon to monitor running processes associated to tasks.
    """
    label = "Process Monitor"
    name = "process_monitor"

    def initialize(self, settings):
        module_settings = settings[self.name]
        self.enabled = module_settings.get("enabled", False)

        self._process_widget = None

        # TimersManager connection
        self.timers_manager_connector = None
        self._timers_manager_module = None

        self._running_processes = {}
        self._current_pid = None

        self._project_applications = []

    def tray_init(self):
        self._create_dialog()

        # Module is its own connector to TimersManager
        self.timers_manager_connector = self

    def stop_timers(self):
        """Stop all timers."""
        print("ProcessMonitor - stop_timers")
        if self._timers_manager_module is not None:
            self._timers_manager_module.last_task = None
            self._timers_manager_module.stop_timers()

    def _create_dialog(self):
        if self._process_widget is not None:
            return

        from .widgets import ProcessMonitorDialog
        self._process_widget = ProcessMonitorDialog(self)

    def show_dialog(self):
        """Show dialog.

        This can be called from anywhere but can also crash in headless mode.
        There is no way to prevent addon to do invalid operations if he's
        not handling them.
        """
        # Make sure dialog is created
        self._create_dialog()
        self._process_widget.open()

    def request_start_timer(self, pid):
        print("request_start_timer: {}".format(pid))

        #self. start_timer(self, project_name, asset_name, task_name)

        if pid is None:
            self._timers_manager_module.close_message()
            self.stop_timers()
            return

        #TODO: Can happen? Do what in this case?
        if not pid in self._running_processes:
            self.log.error((
                "Process ID '{}' not found in running processes!"
            ).format(pid))
            return

        if self._current_pid != pid:
            if self._timers_manager_module.is_running:
                self.timer_stopped()

                #TODO: needed?
                import time
                time.sleep(1)

            '''
            self._current_pid = pid
            self.timer_started(self._running_processes[pid]["data"])
            '''
            self.start_process_timer(pid)

        else:
            if not self._timers_manager_module.is_running:
                self.start_process_timer(pid)

    def on_action_trigger(self):
        """Implementation of abstract method for `ITrayAction`."""
        self.show_dialog()

    ######## PLUGINS_PATHS - BEGIN
    def get_plugin_paths(self):
        """Implementation of abstract method for `IPluginPaths`."""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        return {
            "publish": [os.path.join(current_dir, "plugins", "publish")]
        }
    ######## PLUGINS_PATHS - MID
    '''
    def get_plugin_paths(self):
        """Implementation of abstract method for `IPluginPaths`."""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        plugins_dir = get_plugins_path(self.name, current_dir)
        return {
            "publish": [os.path.join(plugins_dir, "publish")]
        }
    '''
    ######## PLUGINS_PATHS - END

    def cli(self, click_group):
        click_group.add_command(cli_main)

    def start_timer(self, data):
        #self.log.info("start_timer - data: {}".format(data))

        project_name = data["project_name"]
        #TODO: Avoid repeating process is same project as last time
        # => Keep track of project name, and don't call if same project
        self._project_applications = self._get_applications(project_name)
        self.log.info((
            "Registered Applications for '{}': {}"
        ).format(project_name, self._project_applications))

        self._add_running_process(data)

    def stop_timer(self):
        #self.log.info("stop_timer")

        #self._current_pid = None

        self._process_widget.signal_update_table.emit(self._running_processes,
                                                      None)

        # check if other running processes

        print("stop_timer - running processes '{}'".format(self._running_processes))
        #TODO: kill waiting threads? (find way to stop 'wait_proc' thread)
        #self.stop_waiting_thread(pid)

    def _get_applications(self, project_name):
        project_anatomy_settings = get_anatomy_settings(project_name)
        project_applications = project_anatomy_settings.get(
            "attributes",
            {}).get("applications", []
        )
        self.log.debug((
            "Project '{}' applications: {}"
        ).format(project_name, project_applications))

        application_variants = {}
        for project_application in project_applications:
            app_name, app_variant = project_application.split("/")
            if not app_name in application_variants:
                application_variants[app_name] = [ app_variant ]
            elif app_variant not in application_variants[app_name]:
                application_variants[app_name].append(app_variant)

        system_settings = get_system_settings()
        system_applications = system_settings.get("applications", {})

        current_platform = platform.system().lower()
        platform_executables = []
        for application_name in application_variants:
            if application_name not in system_applications:
                #TODO: Error?
                self.log.warning((
                    "Application '{}' not found in system settings!"
                ).format(application_name))
                continue

            variants = system_applications[application_name]["variants"]
            self.log.debug((
                "System '{}' variants: {}"
            ).format(application_name, list(variants.keys())))
            for variant in variants:
                if variant in application_variants[application_name]:
                    name = "{} {}".format(
                        system_applications[application_name]["label"],
                        variant
                    )
                    for executable in variants[variant]["executables"].get(current_platform):
                        platform_executables.append(
                            [name, executable]
                        )

        '''
        self.log.debug((
            "Platform executables: {}"
        ).format(platform_executables))
        '''
        return platform_executables

    def register_timers_manager(self, timer_manager_module):
        self._timers_manager_module = timer_manager_module

    def timer_started(self, data):
        #self.log.info("timer_started")
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_started(self.id, data)

    def timer_stopped(self):
        #self.log.info("timer_stopped")
        if self._timers_manager_module is not None:
            self._timers_manager_module.timer_stopped(self.id)

        #TODO: needed? (should remove from other locations in code)
        self._current_pid = None

    def _add_running_process(self, data):
        print("_add_running_process")

        # TODO: should also check "username" (e.g. if background task started by server)
        process_parameters = [
            "name", #TODO: remove?
            "environ",
            "cmdline"
        ]

        #self.log.info("_add_running_process - current pid: {}".format(self._current_pid))
        #TODO: keep current if none found?
        #self._current_pid = None

        new_pids = []
        for process in psutil.process_iter(process_parameters):

            pid = process.pid
            if pid == 0:
                continue

            cmdline  = process.info["cmdline"]
            #self.log.info("cmdline : {}".format(cmdline))
            if not cmdline:
                continue

            name = process.info["name"]
            for application_name, project_application \
                    in self._project_applications:
                if project_application == cmdline[0]:
                    process_cmd = cmdline[0]
                    self.log.info("Found process: {}".format(name))
                    break

                elif project_application in cmdline[1:]:
                    process_cmd = cmdline[1:].index(project_application)
                    #TODO: REMOVE! (temp windows hack)
                    name = project_application.split("\\")[-1].split("/")[-1]
                    #name = ".".join(name.split(".")[:-1])
                    self.log.info("Found subprocess: {}".format(name))
                    break

            else:
                continue
            #self.log.debug("PID: {}".format(pid))

            ####
            #TODO: get rid of 'name' stuff before?
            name = application_name
            ####

            #TODO: could be done at start
            # Check if parent process is running
            ppid = process.ppid()
            if ppid in self._running_processes:
                self.log.warning("ppid '{}' running => ignore".format(ppid))
                continue

            #TODO: ok with "openpype"?
            # => Not OK if started in CLI or via "run_tray" script
            parent = process.parent()
            if not parent or "openpype" not in parent.name():
                continue

            '''
            self.log.info("PID: {}".format(pid))
            self.log.info((
                "_running_processes: {}"
            ).format(self._running_processes))
            '''

            # Set current PID if matching context (can have more than 1 match)
            environ = process.info["environ"]
            if pid in self._running_processes:
                process_data = self._running_processes[pid]["data"]
                project_name = process_data["project_name"]
                task_name = process_data["task_name"]
                entity_name = process_data["hierarchy"][-1]

                if (
                    project_name == environ["AVALON_PROJECT"]
                    and task_name == environ["AVALON_TASK"]
                    and entity_name == environ["AVALON_ASSET"]
                ):
                    self.log.debug("Process '{}' already running".format(pid))
                    continue

                #TODO: can happen?
                # Process running but with different context => Kill thread
                self.log.warning((
                    "Process '{}' running but with different context"
                    " => Kill thread"
                ).format(pid))
                self.stop_waiting_thread(pid)
            """
            #?
            else:
                self._current_pid = pid
            """

            process_thread = StoppableThread(process, self.on_terminate)
            process_thread.start()

            self.log.info("Adding pid '{}' for '{}'".format(pid, name))
            self._running_processes[pid] = {"data": data,
                                            "name": name,
                                            "thread": process_thread,
                                            "cmdline": process_cmd}

            self._current_pid = pid
            new_pids.append(pid)

        #TODO: Can it be an issue? (if not => remove 'new_pids' as useless)
        if len(new_pids) > 1:
            self.log.warning("More than 1 new pid: {}".format(new_pids))

        #self.log.debug("Current PID: {}".format(self._current_pid))
        self._process_widget.signal_update_table.emit(self._running_processes,
                                                      self._current_pid)

    def on_terminate(self, proc):
        """Update timer depending on terminated process.

        If no remaining running processes, timers are stopped.

        Else, if the timer for the terminated process is currently running,
        it is stopped and another timer is started.
        Else, nothing is done (current timer kept running).

        The timer to start is determined by the remaining running processes:
        - no process: no timer started.
        - 1 process: start process timer.
        - >1 processes:
            - if all have same context: start timer for any (first found),
            - else: ask user to select task.
        """
        self.log.debug((
            "Process '{}' terminated with exit code '{}'"
        ).format(proc.pid, proc.returncode))

        #TODO: useless variable, same as 'proc' (?)
        terminated_process = None
        #TODO: warning if not found?
        if proc.pid in self._running_processes:
            terminated_process = self._running_processes.pop(proc.pid)

            process_parameters = [
                #"name",
                "cmdline"
            ]
            for process in psutil.process_iter(process_parameters):
                pid = process.pid
                if pid == 0:
                    continue

                #self.log.debug("name : {}".format(process.info["name"]))


                ppid = process.ppid()
                #self.log.debug("ppid : {}".format(ppid))
                if ppid != proc.pid:
                    continue

                # Check if have command line of parent
                # => To avoid children daemon processes spawned in background
                #  to be considered as running processes,
                #  such as 'ADPClientService' for Maya/3dsMax.
                cmdline  = process.info["cmdline"]
                if not cmdline:
                    continue

                process_cmd = terminated_process["cmdline"]
                #TODO: OK? (or should only check 'cmdline[0]'?
                if process_cmd not in cmdline:
                    continue

                self.log.info((
                    "ppid '{}' running => Replacing with child '{}'"
                ).format(ppid, pid))

                # Update current pid if was the terminated process
                if self._current_pid == ppid:
                    self._current_pid = pid

                # Start new thread
                process_thread = StoppableThread(process, self.on_terminate)
                process_thread.start()
                self.log.info((
                    "Adding pid '{}' for '{}'"
                ).format(pid, terminated_process["name"]))
                self._running_processes[pid] = {
                    "data": terminated_process["data"],
                    "name": terminated_process["name"],
                    "thread": process_thread,
                    "cmdline": process_cmd
                }

                # No change for running timer
                #TODO: Could be a problem if application not closed by user
                # => Timer activated in background without user knowing
                if self._current_pid != pid:
                    self.timer_stopped()

                    #TODO: need to check?
                    if self._timers_manager_module is not None:
                        #if not self._timers_manager_module._idle_stopped:
                        if self._timers_manager_module.is_running:
                            #TODO(derek): need timeout? (avoid if possible)
                            import time
                            time.sleep(1)
                            self.start_process_timer(pid)

                self._process_widget.signal_update_table.emit(
                    self._running_processes,
                    self._current_pid
                )
                return

        self._timers_manager_module.close_message()

        #TODO: Issue when closing OpenPype before the running process.
        # Problem: Ftrack action server has stopped => timer not stopped.
        # Solution: Stop timers when closing Ftrack (?)
        if not self._running_processes:
            self._current_pid = None
            self.stop_timers()

        else:
            if proc.pid == self._current_pid:
                if len(self._running_processes) == 1:
                    # Get ~first item in dictionary
                    for pid in self._running_processes:
                        data = self._running_processes[pid]["data"]
                        break

                    if (
                        terminated_process
                        and self._compare_data(data, terminated_process["data"])
                    ):
                        # Same context ('data'): no need to stop+start timers
                        # (only update 'pid')
                        self._current_pid = pid

                    else:
                        self._current_pid = None
                        self.timer_stopped()
                        #self._current_pid = pid

                        #TODO: need to check?
                        if self._timers_manager_module is not None:
                            #if not self._timers_manager_module._idle_stopped:
                            if self._timers_manager_module.is_running:
                                #TODO(derek): need timeout? (avoid if possible)
                                import time
                                time.sleep(1)
                                '''
                                self._current_pid = pid
                                self.timer_started(data)
                                '''
                                self.start_process_timer(pid)

                else:
                    # If all the running processes have same context ('data'),
                    # any timer can be started.
                    # Else, the user is asked to start a timer manually.
                    all_same = True
                    new_data = None
                    for pid in self._running_processes:
                        data = self._running_processes[pid]["data"]
                        if not new_data:
                            new_data = data
                            continue

                        if not self._compare_data(data, new_data):
                            all_same = False
                            break

                    if all_same:
                        if (terminated_process
                            and self._compare_data(new_data,
                                                   terminated_process["data"])
                        ):
                            self._current_pid = pid

                        else:
                            self._current_pid = None
                            self.timer_stopped()

                            #TODO: need to check?
                            if self._timers_manager_module is not None:
                                if self._timers_manager_module.is_running:
                                    #TODO(derek): need timeout? (avoid if possible)
                                    import time
                                    time.sleep(1)
                                    '''
                                    self._current_pid = pid
                                    self.timer_started(new_data)
                                    '''
                                    self.start_process_timer(pid)

                    else:
                        #?
                        #self.timer_stopped()
                        self.stop_timers()

                        self._process_widget.signal_select_task.emit()

        self._process_widget.signal_update_table.emit(self._running_processes,
                                                      self._current_pid)

    def start_process_timer(self, pid):
        #self.log.info("start_process_timer: {}".format(pid))

        if pid not in self._running_processes:
            self.log.warning("Process ID '{}' not found!".format(pid))
            return

        self._current_pid = pid
        self.timer_started(self._running_processes[pid]["data"])

    def stop_waiting_thread(self, pid):
        if pid not in self._running_processes:
            self.log.warning((
                "Waiting thread not found for pid '{}'"
            ).format(pid))
            return

        self.log.info("Killing waiting thread for pid '{}'".format(pid))

        running_process = self._running_processes.pop(pid)
        #self.log.debug("running_process: {}".format(running_process))

        wait_thread = running_process["thread"]
        # TODO: remove try/except?
        try:
            if wait_thread.isAlive():
                wait_thread.stop()
                wait_thread.join()
        except Exception as e:
            self.log.error("Error killing thread: {}".format(str(e)))

    @staticmethod
    def _compare_data(new, old):
        if (
            not "project_name" in new
            or new["project_name"] != old.get("project_name", None)
        ):
            return False

        if (
            not "task_name" in new
            or new["task_name"] != old.get("task_name", None)
        ):
            return False

        if (
            not "hierarchy" in new
            or new["hierarchy"][-1] != old.get("hierarchy", [])[-1]
        ):
            return False

        return True


#TODO: rewrite+rename
class StoppableThread(threading.Thread):
    def __init__(self, process, on_terminate):
        super(StoppableThread, self).__init__()
        self.process = process
        self.on_terminate = on_terminate

    def run(self):
        try:
            print("wait_proc: {}".format(self.process))
            gone, alive = psutil.wait_procs([self.process],
                                            timeout=None,
                                            callback=self.on_terminate)
            print("gone: {}, alive: {}".format(gone, alive))
        except Exception as e:
            print("ERROR: {}".format(str(e)))
        finally:
            print("thread ended")

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def stop(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                         ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')



#TODO: want cli?
@click.group(ProcessMonitor.name, help="Process Monitor dynamic cli commands.")
def cli_main():
    pass


@cli_main.command()
def nothing():
    """Does nothing but print a message."""
    print("You've triggered \"nothing\" command.")


@cli_main.command()
def show_dialog():
    """Show ProcessMonitor dialog.

    We don't have access to addon directly through cli so we have to create
    it again.
    """
    from openpype.tools.utils.lib import qt_app_context

    manager = ModulesManager()
    process_monitor = manager.modules_by_name[ProcessMonitor.name]
    with qt_app_context():
        process_monitor.show_dialog()
