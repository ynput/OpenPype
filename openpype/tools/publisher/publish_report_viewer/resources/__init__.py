import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_popup_icon_path():
    return os.path.join(CURRENT_DIR, "popup_icon.svg")
