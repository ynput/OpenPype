import os
import subprocess

from openpype.pipeline import load

MAYA_LOCATION = os.environ['MAYA_LOCATION']
MAYAPY = os.path.join(MAYA_LOCATION, 'bin', 'mayapy')
USD_LOCATION = os.getenv("USD_LOCATION")
USDVIEW = os.path.join(USD_LOCATION, 'bin', 'usdview')


class ShowInUsdview(load.LoaderPlugin):
    """Open USD file in usdview

    This requires `OpenGL` python package to be available to Maya. For more
    details also see the "Using Usdiew in Maya" section in maya documentation.

    See Also:
        https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=GUID-C452B331-7C4D-4B58-A1BA-D03775F266A8  # noqa

    """

    label = "Show in usdview"
    representations = ["*"]
    families = ["*"]
    extensions = {"usd", "usda", "usdlc", "usdnc", "abc"}
    order = 15

    icon = "code-fork"
    color = "white"

    # Enable if usd location is defined (which maya usd plugin does)
    enabled = USD_LOCATION and os.path.isdir(USD_LOCATION)

    def load(self, context, name=None, namespace=None, data=None):

        try:
            import OpenGL  # noqa: F403
        except ImportError:
            self.log.error(
                "usdview for maya requires to have `OpenGL` python library "
                "available. Please make sure to install it.\n"
                "The `OpenGL` library can be installed for maya using:\n"
                "mayapy -m pip install PyOpenGL==3.1.0"
            )
        filepath = self.filepath_from_context(context)
        filepath = os.path.normpath(filepath)
        filepath = filepath.replace("\\", "/")

        if not os.path.exists(filepath):
            self.log.error("File does not exist: %s" % filepath)
            return

        self.log.info("Start maya variant of usdview...")
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen([MAYAPY, USDVIEW, filepath],
                         creationflags=CREATE_NO_WINDOW,
                         # Set current working directory so that browsing
                         # from usdview itself starts from that folder too
                         cwd=os.path.dirname(filepath))
