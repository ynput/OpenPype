from pynput import mouse, keyboard


class MouseThread(mouse.Listener):
    """Listens user's mouse movement."""

    def __init__(self, callback):
        super(MouseThread, self).__init__(on_move=self.on_move)
        self.callback = callback

    def on_move(self, posx, posy):
        self.callback()


class KeyboardThread(keyboard.Listener):
    """Listens user's keyboard input."""

    def __init__(self, callback):
        super(KeyboardThread, self).__init__(on_press=self.on_press)

        self.callback = callback

    def on_press(self, key):
        self.callback()
