import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Harmonic Oscillator Lab")
    app.setOrganizationName("Physics Education Simulator")
    project_root = Path(__file__).resolve().parent
    icon_path = project_root / "icon.ico"
    if not icon_path.exists():
        icon_path = project_root / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
