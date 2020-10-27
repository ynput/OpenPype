import os
from avalon.tvpaint.communication_server import register_localization_file


def install():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    localization_file = os.path.join(current_dir, "avalon.loc")
    register_localization_file(localization_file)
