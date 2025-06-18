from pynput import keyboard

class ClassKeyEvent():
    def __init__(self, parent=None):
        self.mainWindow = parent
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char and key.char.lower() in self.mainWindow.keys_pressed:
                self.mainWindow.keys_pressed[key.char.lower()] = True
        except Exception as e:
            print(f"Key press error: {e}")

    def on_release(self, key):
        try:
            if hasattr(key, 'char') and key.char and key.char.lower() in self.mainWindow.keys_pressed:
                self.mainWindow.keys_pressed[key.char.lower()] = False
        except Exception as e:
            print(f"Key release error: {e}")
