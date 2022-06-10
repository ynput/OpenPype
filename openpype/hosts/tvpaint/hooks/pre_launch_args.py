from openpype.lib import (
    PreLaunchHook,
    get_openpype_execute_args
)


class TvpaintPrelaunchHook(PreLaunchHook):
    """Launch arguments preparation.

    Hook add python executable and script path to tvpaint implementation before
    tvpaint executable and add last workfile path to launch arguments.

    Existence of last workfile is checked. If workfile does not exists tries
    to copy templated workfile from predefined path.
    """
    app_groups = ["tvpaint"]

    def execute(self):
        # Pop tvpaint executable
        executable_path = self.launch_context.launch_args.pop(0)

        # Pop rest of launch arguments - There should not be other arguments!
        remainders = []
        while self.launch_context.launch_args:
            remainders.append(self.launch_context.launch_args.pop(0))

        new_launch_args = get_openpype_execute_args(
            "run", self.launch_script_path(), executable_path
        )

        # Append as whole list as these areguments should not be separated
        self.launch_context.launch_args.append(new_launch_args)

        if remainders:
            self.log.warning((
                "There are unexpected launch arguments in TVPaint launch. {}"
            ).format(str(remainders)))
            self.launch_context.launch_args.extend(remainders)

    def launch_script_path(self):
        from openpype.hosts.tvpaint import get_launch_script_path

        return get_launch_script_path()
