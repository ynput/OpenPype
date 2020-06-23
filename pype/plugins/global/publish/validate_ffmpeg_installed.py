import pyblish.api
import os
import subprocess
import pype.lib
try:
    import os.errno as errno
except ImportError:
    import errno


class ValidateFFmpegInstalled(pyblish.api.ContextPlugin):
    """Validate availability of ffmpeg tool in PATH"""

    order = pyblish.api.ValidatorOrder
    label = 'Validate ffmpeg installation'
    optional = True

    def is_tool(self, name):
        try:
            devnull = open(os.devnull, "w")
            subprocess.Popen(
                [name], stdout=devnull, stderr=devnull
            ).communicate()
        except OSError as e:
            if e.errno == errno.ENOENT:
                return False
        return True

    def process(self, context):
        ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")
        self.log.info("ffmpeg path: `{}`".format(ffmpeg_path))
        if self.is_tool(ffmpeg_path) is False:
            self.log.error("ffmpeg not found in PATH")
            raise RuntimeError('ffmpeg not installed.')
