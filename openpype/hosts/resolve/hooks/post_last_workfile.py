from pathlib import Path
from openpype.lib import PostLaunchHook
from openpype.lib.execute import run_subprocess


SCRIPT = r"""
from openpype.pipeline import install_host, registered_host
import DaVinciResolveScript as bmd

def main():
    import openpype.hosts.resolve.api as bmdvr

    # activate resolve from openpype
    install_host(bmdvr)

    # Open last workfile
    workfile_path = r"{workfile_path}"
    if workfile_path:
        host = registered_host()
        host.open_file(workfile_path)

    # Launch the OpenPype menu inside the host
    menu_script_path = r"{openpype_menu_path}"
    print(f"Running script {{menu_script_path}}")
    resolve = bmd.scriptapp("Resolve")
    fusion = resolve.Fusion()
    fusion.RunScript(menu_script_path)

if __name__ == "__main__":
    tried = 0
    resolve = None
    while tried < {try_count}:
        print("Waiting for Resolve to start ...")
        try:
            resolve = bmd.scriptapp("Resolve")
            main()
            break
        except:
            pass

        tried += 1

"""


class ResolvePostLaunch(PostLaunchHook):
    """
    This hook will run a background script against Resolve directly after
    launch to try and automatically open the last workfile.

    Additionally it will try to auto launch the OpenPype menu directly.
    """
    app_groups = ["resolve"]

    def execute(self):

        if not self.data.get("start_last_workfile"):
            self.log.info("It is set to not start last workfile on start.")
            return

        last_workfile = self.data.get("last_workfile_path")
        if not last_workfile:
            self.log.warning("Last workfile was not collected.")
            return

        utility_scripts_dir = (
            self.launch_context.env["RESOLVE_UTILITY_SCRIPTS_DIR"])
        openpype_menu_path = Path(
            utility_scripts_dir) / "__OpenPype__Menu__.py"

        self.log.info(f"Menu path: {openpype_menu_path}")
        self.log.info(f"Found last workfile: {last_workfile}")

        script = SCRIPT.format(
            workfile_path=last_workfile,
            openpype_menu_path=openpype_menu_path,
            try_count=5
        )

        executable = str(self.launch_context.executable)
        # executable = "C:/Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe"
        fuscript_executable = Path(executable).parent / "fuscript"
        self.log.info(script)

        output = run_subprocess([
            fuscript_executable, "-l", "py3", "-x", script
        ], env=self.launch_context.env, logger=self.log)

        self.log.info(output)
