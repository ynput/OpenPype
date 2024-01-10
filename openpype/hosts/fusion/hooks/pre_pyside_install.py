import os
import subprocess
import platform
import uuid

from openpype.lib.applications import PreLaunchHook, LaunchTypes


class InstallPySideToFusion(PreLaunchHook):
    """Automatically installs Qt binding to fusion's python packages.

    Check if fusion has installed PySide2 and will try to install if not.

    For pipeline implementation is required to have Qt binding installed in
    fusion's python packages.
    """

    app_groups = {"fusion"}
    order = 2
    launch_types = {LaunchTypes.local}

    def execute(self):
        # Prelaunch hook is not crucial
        try:
            settings = self.data["project_settings"][self.host_name]
            if not settings["hooks"]["InstallPySideToFusion"]["enabled"]:
                return
            self.inner_execute()
        except Exception:
            self.log.warning(
                "Processing of {} crashed.".format(self.__class__.__name__),
                exc_info=True
            )

    def inner_execute(self):
        self.log.debug("Check for PySide2 installation.")

        fusion_python3_home = self.data.get("fusion_python3_home")
        if not fusion_python3_home:
            self.log.warning("'fusion_python3_home' was not provided. "
                             "Installation of PySide2 not possible")
            return

        if platform.system().lower() == "windows":
            exe_filenames = ["python.exe"]
        else:
            exe_filenames = ["python3", "python"]

        for exe_filename in exe_filenames:
            python_executable = os.path.join(fusion_python3_home, exe_filename)
            if os.path.exists(python_executable):
                break

        if not os.path.exists(python_executable):
            self.log.warning(
                "Couldn't find python executable for fusion. {}".format(
                    python_executable
                )
            )
            return

        # Check if PySide2 is installed and skip if yes
        if self._is_pyside_installed(python_executable):
            self.log.debug("Fusion has already installed PySide2.")
            return

        self.log.debug("Installing PySide2.")
        # Install PySide2 in fusion's python
        if self._windows_require_permissions(
                os.path.dirname(python_executable)):
            result = self._install_pyside_windows(python_executable)
        else:
            result = self._install_pyside(python_executable)

        if result:
            self.log.info("Successfully installed PySide2 module to fusion.")
        else:
            self.log.warning("Failed to install PySide2 module to fusion.")

    def _install_pyside_windows(self, python_executable):
        """Install PySide2 python module to fusion's python.

        Installation requires administration rights that's why it is required
        to use "pywin32" module which can execute command's and ask for
        administration rights.
        """
        try:
            import win32api
            import win32con
            import win32process
            import win32event
            import pywintypes
            from win32comext.shell.shell import ShellExecuteEx
            from win32comext.shell import shellcon
        except Exception:
            self.log.warning("Couldn't import \"pywin32\" modules")
            return False

        try:
            # Parameters
            # - use "-m pip" as module pip to install PySide2 and argument
            #   "--ignore-installed" is to force install module to fusion's
            #   site-packages and make sure it is binary compatible
            parameters = "-m pip install --ignore-installed PySide2"

            # Execute command and ask for administrator's rights
            process_info = ShellExecuteEx(
                nShow=win32con.SW_SHOWNORMAL,
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",
                lpFile=python_executable,
                lpParameters=parameters,
                lpDirectory=os.path.dirname(python_executable)
            )
            process_handle = process_info["hProcess"]
            win32event.WaitForSingleObject(process_handle,
                                           win32event.INFINITE)
            returncode = win32process.GetExitCodeProcess(process_handle)
            return returncode == 0
        except pywintypes.error:
            return False

    def _install_pyside(self, python_executable):
        """Install PySide2 python module to fusion's python."""
        try:
            # Parameters
            # - use "-m pip" as module pip to install PySide2 and argument
            #   "--ignore-installed" is to force install module to fusion's
            #   site-packages and make sure it is binary compatible
            env = dict(os.environ)
            del env['PYTHONPATH']
            args = [
                python_executable,
                "-m",
                "pip",
                "install",
                "--ignore-installed",
                "PySide2",
            ]
            process = subprocess.Popen(
                args, stdout=subprocess.PIPE, universal_newlines=True,
                env=env
            )
            process.communicate()
            return process.returncode == 0
        except PermissionError:
            self.log.warning(
                "Permission denied with command:"
                "\"{}\".".format(" ".join(args))
            )
        except OSError as error:
            self.log.warning(f"OS error has occurred: \"{error}\".")
        except subprocess.SubprocessError:
            pass

    def _is_pyside_installed(self, python_executable):
        """Check if PySide2 module is in fusion's pip list."""
        args = [python_executable, "-c", "from qtpy import QtWidgets"]
        process = subprocess.Popen(args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        stderr = stderr.decode()
        if stderr:
            return False
        return True

    def _windows_require_permissions(self, dirpath):
        if platform.system().lower() != "windows":
            return False

        try:
            # Attempt to create a temporary file in the folder
            temp_file_path = os.path.join(dirpath, uuid.uuid4().hex)
            with open(temp_file_path, "w"):
                pass
            os.remove(temp_file_path)  # Clean up temporary file
            return False

        except PermissionError:
            return True

        except BaseException as exc:
            print(("Failed to determine if root requires permissions."
                   "Unexpected error: {}").format(exc))
            return False
