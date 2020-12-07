from pype.lib import (
    PreLaunchHook,
    ApplicationLaunchFailed,
    _subprocess
)


class PreInstallPyWin(PreLaunchHook):
    """Hook makes sure there is installed python module pywin32 on windows."""
    # WARNING This hook will probably be deprecated in Pype 3 - kept for test
    order = 10
    app_groups = ["tvpaint"]
    platforms = ["windows"]

    def execute(self):
        installed = False
        try:
            from win32com.shell import shell
            self.log.debug("Python module `pywin32` already installed.")
            installed = True
        except Exception:
            pass

        if installed:
            return

        try:
            output = _subprocess(
                ["pip", "install", "pywin32==227"]
            )
            self.log.debug("Pip install pywin32 output:\n{}'".format(output))
        except RuntimeError:
            msg = "Installation of python module `pywin32` crashed."
            self.log.warning(msg, exc_info=True)
            raise ApplicationLaunchFailed(msg)
