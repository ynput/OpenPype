import os


def get_plugin_files_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "plugin_files")
