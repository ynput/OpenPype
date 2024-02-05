import traceback

from openpype.widgets import message_window


def open_template_ui(builder, main_window):
    """Open template from `builder`

    Asks user about overwriting current scene and feedsback exceptions.
    """

    result = message_window.message(
        title="Opening template",
        message="Caution! You will loose unsaved changes.\n"
        "Do you want to continue?",
        parent=main_window,
        level="question",
    )

    if result:
        try:
            builder.open_template()
        except Exception:
            message_window.message(
                title="Template Load Failed",
                message="".join(traceback.format_exc()),
                parent=main_window,
                level="critical"
            )
