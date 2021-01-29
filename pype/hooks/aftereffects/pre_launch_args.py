import os

from pype.lib import PreLaunchHook


class AfterEffectsPrelaunchHook(PreLaunchHook):
    """Launch arguments preparation.

    Hook add python executable and execute python script of AfterEffects
    implementation before AfterEffects executable.
    """
    app_groups = ["aftereffects"]

    def execute(self):
        # Pop tvpaint executable
        aftereffects_executable = self.launch_context.launch_args.pop(0)

        # Pop rest of launch arguments - There should not be other arguments!
        remainders = []
        while self.launch_context.launch_args:
            remainders.append(self.launch_context.launch_args.pop(0))

        new_launch_args = [
            self.python_executable(),
            "-c",
            (
                "import avalon.aftereffects;"
                "avalon.aftereffects.launch(\"{}\")"
            ).format(aftereffects_executable.replace("\\", "\\\\"))
        ]

        # Append as whole list as these areguments should not be separated
        self.launch_context.launch_args.append(new_launch_args)

        if remainders:
            self.log.warning((
                "There are unexpected launch arguments "
                "in AfterEffects launch. {}"
            ).format(str(remainders)))
            self.launch_context.launch_args.extend(remainders)

    def python_executable(self):
        """Should lead to python executable."""
        # TODO change in Pype 3
        return os.environ["PYPE_PYTHON_EXE"]
