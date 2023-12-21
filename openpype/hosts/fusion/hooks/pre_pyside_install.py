import os
import sys
import re
import subprocess
from platform import system
from openpype.lib.applications import PreLaunchHook, LaunchTypes


class InstallPySideToFusion(PreLaunchHook):
    """Install Qt binding to fusion's python packages.

    Prelaunch hook does 2 things:
    1.) Fusion's python packages are pushed to the beginning of PYTHONPATH.
    2.) Check if fusion has installed PySide2 and will try to install if not.

    For pipeline implementation is required to have Qt binding installed in
    fusion's python packages.
    """

    app_groups = {"fusion"}
    order = 2
    launch_types = {LaunchTypes.local}

    def execute(self):
        # Prelaunch hook is not crucial
        try:
            self.inner_execute()
        except Exception:
            self.log.warning(
                "Processing of {} crashed.".format(self.__class__.__name__),
                exc_info=True
            )

    def inner_execute(self, fusion_python3_home):
        self.log.debug("Check for PySide2 installation.")

        fusion_python3_home = self.data.get("fusion_python3_home")
        if not fusion_python3_home:
            self.log.warning("'fusion_python3_home' was not provided. "
                             "Installation of PySide2 not possible")
            return

        exe = "python.exe" if os.name == 'nt' else "python"
        python_executable = os.path.join(fusion_python3_home, exe)

        if not os.path.exists(python_executable):
            self.log.warning(
                "Couldn't find python executable for fusion. {}".format(
                    pip_executable
                )
            )
            return

        # Check if PySide2 is installed and skip if yes
        if self.is_pyside_installed(python_executable):
            self.log.debug("Fusion has already installed PySide2.")
            return

        # Install PySide2 in fusion's python
        if platform == "windows":
            result = self.install_pyside_windows(python_executable)
        else:
            result = self.install_pyside(python_executable)

        if result:
            self.log.info("Successfully installed PySide2 module to fusion.")
        else:
            self.log.warning("Failed to install PySide2 module to fusion.")

    def install_pyside_windows(self, python_executable):
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
            return

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
            win32event.WaitForSingleObject(process_handle, win32event.INFINITE)
            returncode = win32process.GetExitCodeProcess(process_handle)
            return returncode == 0
        except pywintypes.error:
            pass

    def install_pyside(self, python_executable):
        """Install PySide2 python module to fusion's python."""
        try:
            # Parameters
            # - use "-m pip" as module pip to install PySide2 and argument
            #   "--ignore-installed" is to force install module to fusion's
            #   site-packages and make sure it is binary compatible
            args = [
                python_executable,
                "-m",
                "pip",
                "install",
                "--ignore-installed",
                "PySide2",
            ]
            process = subprocess.Popen(
                args, stdout=subprocess.PIPE, universal_newlines=True
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

    def is_pyside_installed(self, python_executable):
        """Check if PySide2 module is in fusion's pip list.

        Check that PySide2 is installed directly in fusion's site-packages.
        It is possible that it is installed in user's site-packages but that
        may be incompatible with fusion's python.
        """
        # Get pip list from fusion's python executable
        args = [python_executable, "-m", "pip", "list"]
        process = subprocess.Popen(args, stdout=subprocess.PIPE)
        stdout, _ = process.communicate()
        lines = stdout.decode().split(os.linesep)
        # Second line contain dashes that define maximum length of module name.
        #   Second column of dashes define maximum length of module version.
        package_dashes, *_ = lines[1].split(" ")
        package_len = len(package_dashes)

        # Got through printed lines starting at line 3
        for idx in range(2, len(lines)):
            line = lines[idx]
            if not line:
                continue
            package_name = line[0:package_len].strip()
            if package_name.lower() == "pyside2":
                return True
        return False
