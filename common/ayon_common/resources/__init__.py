import os

RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))


def get_resource_path(*args):
    path_items = list(args)
    path_items.insert(0, RESOURCES_DIR)
    return os.path.sep.join(path_items)


def get_icon_path():
    if os.environ.get("OPENPYPE_USE_STAGING") == "1":
        return get_resource_path("AYON_staging.png")
    return get_resource_path("AYON.png")


def load_stylesheet():
    stylesheet_path = get_resource_path("stylesheet.css")

    with open(stylesheet_path, "r") as stream:
        content = stream.read()
    return content
