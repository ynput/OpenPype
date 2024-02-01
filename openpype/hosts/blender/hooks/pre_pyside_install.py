import os
import re
import subprocess
from platform import system
from openpype.lib.applications import PreLaunchHook, LaunchTypes


class InstallPySideToBlender(PreLaunchHook):
    """Install Qt binding to blender's python packages.

    Prelaunch hook does 2 things:
    1.) Blender's python packages are pushed to the beginning of PYTHONPATH.
    2.) Check if blender has installed PySide2 and will try to install if not.

    For pipeline implementation is required to have Qt binding installed in
    blender's python packages.
    """

    app_groups = {"blender"}
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

    def inner_execute(self):
        # Get blender's python directory
        version_regex = re.compile(r"^[2-4]\.[0-9]+$")

        platform = system().lower()
        executable = self.launch_context.executable.executable_path
        expected_executable = "blender"
        if platform == "windows":
            expected_executable += ".exe"

        if os.path.basename(executable).lower() != expected_executable:
            self.log.info((
                f"Executable does not lead to {expected_executable} file."
                "Can't determine blender's python to check/install PySide2."
            ))
            return

        versions_dir = os.path.dirname(executable)
        if platform == "darwin":
            versions_dir = os.path.join(
                os.path.dirname(versions_dir), "Resources"
            )
        version_subfolders = []
        for dir_entry in os.scandir(versions_dir):
            if dir_entry.is_dir() and version_regex.match(dir_entry.name):
                version_subfolders.append(dir_entry.name)

        if not version_subfolders:
            self.log.info(
                "Didn't find version subfolder next to Blender executable"
            )
            return

        if len(version_subfolders) > 1:
            self.log.info((
                "Found more than one version subfolder next"
                " to blender executable. {}"
            ).format(", ".join([
                '"./{}"'.format(name)
                for name in version_subfolders
            ])))
            return

        version_subfolder = version_subfolders[0]

        python_dir = os.path.join(versions_dir, version_subfolder, "python")
        python_lib = os.path.join(python_dir, "lib")
        python_version = "python"

        if platform != "windows":
            for dir_entry in os.scandir(python_lib):
                if dir_entry.is_dir() and dir_entry.name.startswith("python"):
                    python_lib = dir_entry.path
                    python_version = dir_entry.name
                    break

        # Change PYTHONPATH to contain blender's packages as first
        python_paths = [
            python_lib,
            os.path.join(python_lib, "site-packages"),
        ]
        python_path = self.launch_context.env.get("PYTHONPATH") or ""
        for path in python_path.split(os.pathsep):
            if path:
                python_paths.append(path)

        self.launch_context.env["PYTHONPATH"] = os.pathsep.join(python_paths)

        # Get blender's python executable
        python_bin = os.path.join(python_dir, "bin")
        if platform == "windows":
            python_executable = os.path.join(python_bin, "python.exe")
        else:
            python_executable = os.path.join(python_bin, python_version)
            # Check for python with enabled 'pymalloc'
            if not os.path.exists(python_executable):
                python_executable += "m"

        if not os.path.exists(python_executable):
            self.log.warning(
                "Couldn't find python executable for blender. {}".format(
                    executable
                )
            )
            return

        # Check if PySide2 is installed and skip if yes
        if self.is_pyside_installed(python_executable):
            self.log.debug("Blender has already installed PySide2.")
            return

        # Install PySide2 in blender's python
        if platform == "windows":
            result = self.install_pyside_windows(python_executable)
        else:
            result = self.install_pyside(python_executable)

        if result:
            self.log.info("Successfully installed PySide2 module to blender.")
        else:
            self.log.warning("Failed to install PySide2 module to blender.")

    def install_pyside_windows(self, python_executable):
        """Install PySide2 python module to blender's python.

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
            #   "--ignore-installed" is to force install module to blender's
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
        """Install PySide2 python module to blender's python."""
        try:
            # Parameters
            # - use "-m pip" as module pip to install PySide2 and argument
            #   "--ignore-installed" is to force install module to blender's
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
        """Check if PySide2 module is in blender's pip list.

        Check that PySide2 is installed directly in blender's site-packages.
        It is possible that it is installed in user's site-packages but that
        may be incompatible with blender's python.
        """
        # Get pip list from blender's python executable
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
