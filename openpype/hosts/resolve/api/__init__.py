"""
resolve api
"""
import os

bmdvr = None
bmdvf = None

API_DIR = os.path.dirname(os.path.abspath(__file__))
HOST_DIR = os.path.dirname(API_DIR)
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
