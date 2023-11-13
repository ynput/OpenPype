import os

RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))


def get_options_image_path():
    return os.path.join(RESOURCES_DIR, "options.png")
