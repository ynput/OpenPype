# :coding: utf-8
# :copyright: Copyright (c) ftrack

import os
import sys

# Set the default ftrack server and API key variables to use if no matching
# environment variables are found.
os.environ.setdefault('FTRACK_SERVER', 'https://kredenc.ftrackapp.com')
os.environ.setdefault('FTRACK_APIKEY', '4fcae620-9fea-11e4-92c4-040121b9e701')

# Add ftrack core egg to path.
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'FTrackCore.egg'
    )
)

# Import core ftrack functionality from egg into top level namespace.
from FTrackCore import *
