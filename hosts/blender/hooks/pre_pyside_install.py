import os
import re
import subprocess
from openpype.lib import PreLaunchHook


class InstallPySideToBlender(PreLaunchHook):
    """Install Qt binding to blender's python packages.

    Prelaunch hook does 2 things:
    1.) Blender's python packages are pushed to the beginning of PYTHONPATH.
    2.) Check if blender has installed PySide2 and will try to install if not.

    For pipeline implementation is required to have Qt binding installed in
    blender's python packages.

    Prelaunch hook can work only on Windows right now.
    """

    app_groups = ["blender"]
    platforms = ["windows"]

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
        version_regex = re.compile(r"^[2-3]\.[0-9]+$")

        executable = self.launch_context.executable.executable_path
        if os.path.basename(executable).lower() != "blender.exe":
            self.log.info((
                "Executable does not lead to blender.exe file. Can't determine"
                " blender's python to check/install PySide2."
            ))
            return

        executable_dir = os.path.dirname(executable)
        version_subfolders = []
        for name in os.listdir(executable_dir):
            fullpath = os.path.join(name, executable_dir)
            if not os.path.isdir(fullpath):
                continue

            if not version_regex.match(name):
                continue

            version_subfolders.append(name)

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

        pythond_dir = os.path.join(
            os.path.dirname(executable),
            version_subfolder,
            "python"
        )

        # Change PYTHONPATH to contain blender's packages as first
        python_paths = [
            os.path.join(pythond_dir, "lib"),
            os.path.join(pythond_dir, "lib", "site-packages"),
        ]
        python_path = self.launch_context.env.get("PYTHONPATH") or ""
        for path in python_path.split(os.pathsep):
            if path:
                python_paths.append(path)

        self.launch_context.env["PYTHONPATH"] = os.pathsep.join(python_paths)

        # Get blender's python executable
        python_executable = os.path.join(pythond_dir, "bin", "python.exe")
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
        self.install_pyside_windows(python_executable)

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
            obj = win32event.WaitForSingleObject(
                process_handle, win32event.INFINITE
            )
            returncode = win32process.GetExitCodeProcess(process_handle)
            if returncode == 0:
                self.log.info(
                    "Successfully installed PySide2 module to blender."
                )
                return
        except pywintypes.error:
            pass

        self.log.warning("Failed to install PySide2 module to blender.")

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
        lines = stdout.decode().split("\r\n")
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
