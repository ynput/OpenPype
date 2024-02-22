"""Install PySide2 python module to 3dequalizer's python.

If 3dequalizer doesn't have PySide2 module installed, it will try to install
it.

Note:
    This needs to be changed in the future so the UI is decoupled from the
    host application.

"""

import contextlib
import os
import subprocess
from pathlib import Path
from platform import system

from openpype.lib.applications import LaunchTypes, PreLaunchHook


class InstallPySide2(PreLaunchHook):
    """Install Qt binding to 3dequalizer's python packages."""

    app_groups = {"3dequalizer", "sdv_3dequalizer"}
    launch_types = {LaunchTypes.local}

    def execute(self):
        try:
            self._execute()
        except Exception:
            self.log.warning((
                f"Processing of {self.__class__.__name__} "
                "crashed."), exc_info=True
            )

    def _execute(self):
        platform = system().lower()
        executable = Path(self.launch_context.executable.executable_path)
        expected_executable = "3de4"
        if platform == "windows":
            expected_executable += ".exe"

        if not self.launch_context.env.get("TDE4_HOME"):
            if executable.name.lower() != expected_executable:
                self.log.warning((
                    f"Executable {executable.as_posix()} does not lead "
                    f"to {expected_executable} file. "
                    "Can't determine 3dequalizer's python to "
                    f"check/install PySide2. {executable.name}"
                ))
                return
            python_dir = executable.parent.parent / "sys_data" / "py37_inst"
        else:
            python_dir = Path(self.launch_context.env["TDE4_HOME"]) / "sys_data" / "py37_inst"  # noqa: E501

        if platform == "windows":
            python_executable = python_dir / "python.exe"
        else:
            python_executable = python_dir / "python"
            # Check for python with enabled 'pymalloc'
            if not python_executable.exists():
                python_executable = python_dir / "pythonm"

        if not python_executable.exists():
            self.log.warning(
                "Couldn't find python executable "
                f"for 3de4 {python_executable.as_posix()}"
            )

            return

        # Check if PySide2 is installed and skip if yes
        if self.is_pyside_installed(python_executable):
            self.log.debug("3Dequalizer has already installed PySide2.")
            return

        # Install PySide2 in 3de4's python
        if platform == "windows":
            result = self.install_pyside_windows(python_executable)
        else:
            result = self.install_pyside(python_executable)

        if result:
            self.log.info("Successfully installed PySide2 module to 3de4.")
        else:
            self.log.warning("Failed to install PySide2 module to 3de4.")

    def install_pyside_windows(self, python_executable: Path):
        """Install PySide2 python module to 3de4's python.

        Installation requires administration rights that's why it is required
        to use "pywin32" module which can execute command's and ask for
        administration rights.

        Note:
            This is asking for administrative right always, no matter if
            it is actually needed or not. Unfortunately getting
            correct permissions for directory on Windows isn't that trivial.
            You can either use `win32security` module or run `icacls` command
            in subprocess and parse its output.

        """
        try:
            import pywintypes
            import win32con
            import win32event
            import win32process
            from win32comext.shell import shellcon
            from win32comext.shell.shell import ShellExecuteEx
        except Exception:
            self.log.warning("Couldn't import 'pywin32' modules")
            return

        with contextlib.suppress(pywintypes.error):
            # Parameters
            # - use "-m pip" as module pip to install PySide2 and argument
            #   "--ignore-installed" is to force install module to 3de4's
            #   site-packages and make sure it is binary compatible
            parameters = "-m pip install --ignore-installed PySide2"

            # Execute command and ask for administrator's rights
            process_info = ShellExecuteEx(
                nShow=win32con.SW_SHOWNORMAL,
                fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                lpVerb="runas",
                lpFile=python_executable.as_posix(),
                lpParameters=parameters,
                lpDirectory=python_executable.parent.as_posix()
            )
            process_handle = process_info["hProcess"]
            win32event.WaitForSingleObject(
                process_handle, win32event.INFINITE)
            return_code = win32process.GetExitCodeProcess(process_handle)
            return return_code == 0

    def install_pyside(self, python_executable: Path):
        """Install PySide2 python module to 3de4's python."""

        args = [
            python_executable.as_posix(),
            "-m",
            "pip",
            "install",
            "--ignore-installed",
            "PySide2",
        ]

        try:
            # Parameters
            # - use "-m pip" as module pip to install PySide2 and argument
            #   "--ignore-installed" is to force install module to 3de4
            #   site-packages and make sure it is binary compatible

            process = subprocess.Popen(
                args, stdout=subprocess.PIPE, universal_newlines=True
            )
            process.communicate()
            return process.returncode == 0
        except PermissionError:
            self.log.warning(
                f'Permission denied with command:\"{" ".join(args)}\".')
        except OSError as error:
            self.log.warning(f"OS error has occurred: \"{error}\".")
        except subprocess.SubprocessError:
            pass

    @staticmethod
    def is_pyside_installed(python_executable: Path) -> bool:
        """Check if PySide2 module is in 3de4 python env.

        Args:
            python_executable (Path): Path to python executable.

        Returns:
            bool: True if PySide2 is installed, False otherwise.

        """
        # Get pip list from 3de4's python executable
        args = [python_executable.as_posix(), "-m", "pip", "list"]
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
            package_name = line[:package_len].strip()
            if package_name.lower() == "pyside2":
                return True
        return False
