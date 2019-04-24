import traceback

# activate nukestudio from pype
import avalon.api
import pype.nukestudio
avalon.api.install(pype.nukestudio)

try:
    __import__("pype.nukestudio")
    __import__("pyblish")

except ImportError as e:
    print traceback.format_exc()
    print("pyblish: Could not load integration: %s " % e)

else:
    # Setup integration
    import pype.nukestudio.lib
    pype.nukestudio.lib.setup()
