# main.py
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import HapticMonitor

def main():
    app = QApplication(sys.argv)
    window = HapticMonitor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()