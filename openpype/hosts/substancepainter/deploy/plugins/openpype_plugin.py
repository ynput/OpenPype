

def cleanup_openpype_qt_widgets():
    """
        Workaround for Substance failing to shut down correctly
        when a Qt window was still open at the time of shutting down.

        This seems to work sometimes, but not all the time.

    """
    # TODO: Create a more reliable method to close down all OpenPype Qt widgets
    from PySide2 import QtWidgets
    import substance_painter.ui

    # Kill OpenPype Qt widgets
    print("Killing OpenPype Qt widgets..")
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.__module__.startswith("openpype."):
            print(f"Deleting widget: {widget.__class__.__name__}")
            substance_painter.ui.delete_ui_element(widget)


def start_plugin():
    from openpype.pipeline import install_host
    from openpype.hosts.substancepainter.api import SubstanceHost
    install_host(SubstanceHost())


def close_plugin():
    from openpype.pipeline import uninstall_host
    cleanup_openpype_qt_widgets()
    uninstall_host()


if __name__ == "__main__":
    start_plugin()
