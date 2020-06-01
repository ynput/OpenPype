import traceback

# activate nukestudio from pype
import avalon.api
import pype.hosts.nukestudio
avalon.api.install(pype.hosts.nukestudio)

try:
    __import__("pype.hosts.nukestudio")
    __import__("pyblish")

except ImportError as e:
    print traceback.format_exc()
    print("pyblish: Could not load integration: %s " % e)

else:
    # Setup integration
    import pype.hosts.nukestudio.lib
    pype.hosts.nukestudio.lib.setup()
