import os


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

OP4_TEST_ENABLED = os.environ.get("OP4_TEST") == "1"
