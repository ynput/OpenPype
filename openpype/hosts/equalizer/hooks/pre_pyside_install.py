"""Install PySide python module to 3dequalizer's python.

If 3dequalizer doesn't have PySide module installed, it will try to install
it.

Note:
    This needs to be changed in the future so the UI is decoupled from the
    host application.

"""

import os
import subprocess
from pathlib import Path
from platform import system

from openpype.lib.applications import LaunchTypes, PreLaunchHook


class InstallPySide(PreLaunchHook):
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
                    f"check/install PySide. {executable.name}"
                ))
                return
            python_dir = executable.parent.parent / "sys_data" / "py27_inst"
        else:
            python_dir = Path(self.launch_context.env["TDE4_HOME"]) / "sys_data" / "py27_inst"  # noqa: E501

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

        # Check if PySide is installed and skip if yes
        if self.is_pyside_installed():
            self.log.debug("3Dequalizer has already installed PySide.")
            return

        # Install PySide in 3de4's python
        if platform == "windows":
            result = self.install_pyside_windows()
        else:
            result = self.install_pyside(python_executable)

        if result:
            self.log.info("Successfully installed PySide module to 3de4.")
        else:
            self.log.warning("Failed to install PySide module to 3de4.")

    def install_pyside_windows(self):
        """Install PySide python module to 3de4's python."""
        from openpype.hosts.equalizer import EQUALIZER_HOST_DIR
        try:
            target = os.path.join(EQUALIZER_HOST_DIR, "vendor")
            command = f"cd /D C:\\Python27\\Scripts && pip install --target {target} PySide==1.2.4"
            # Execute commands
            process = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process.returncode == 0
        except Exception as e:
            self.log.warning(f"Couldn't Install PySide, {e}")

    def install_pyside(self, python_executable: Path):
        """Install PySide2 python module to 3de4's python."""

        args = [
            python_executable.as_posix(),
            "-m",
            "pip",
            "install",
            "--ignore-installed",
            "PySide",
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

    def is_pyside_installed(self) -> bool:
        """Check if PySide module is in 3de4 python env.

        Args:
            python_executable (Path): Path to python executable.

        Returns:
            bool: True if PySide is installed, False otherwise.

        """
        global python_path
        import winreg
        from openpype.hosts.equalizer import EQUALIZER_HOST_DIR
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
        except FileNotFoundError:
            print("Error: Environment not found.")
        else:
            # Try to read the value of the PYTHONPATH environmental variable.
            try:
                python_path, _ = winreg.QueryValueEx(reg_key, 'PYTHONPATH')
                # print("PYTHONPATH:", python_path)
            except FileNotFoundError:
                print("PYTHONPATH is not set.")
                os.system("SETX {0} \"{1}\"".format("PYTHONPATH", os.path.join(EQUALIZER_HOST_DIR, "vendor")))
                print("PYTHONPATH is set automatically.\nType the resource attribute using \"sysdm.cpl\" "
                      "on Windows Run.")
            else:
                # Close the registry key
                winreg.CloseKey(reg_key)

        if os.path.exists(os.path.join(EQUALIZER_HOST_DIR, "vendor", "PySide")):
            self.log.info("PySide is already installed...")
            return True

        self.log.info("PySide weren't installed...")
        self.log.info("PySide is installing...")
        return False
