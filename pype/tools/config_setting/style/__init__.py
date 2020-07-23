import os


def load_stylesheet():
    style_path = os.path.join(os.path.dirname(__file__), "style.css")
    with open(style_path, "r") as style_file:
        stylesheet = style_file.read()
    return stylesheet


def app_icon_path():
    return os.path.join(os.path.dirname(__file__), "pype_icon.png")
