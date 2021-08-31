from .window import PublisherWindow


class _WindowCache:
    window = None


def show(parent=None):
    window = _WindowCache.window
    if window is None:
        window = PublisherWindow(parent)
        _WindowCache.window = window

    window.show()
    window.activateWindow()

    return window
