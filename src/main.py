#!/usr/bin/env python3
"""hallpass-qt entry point."""
import sys
from pathlib import Path

# Ensure src on path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl

from hallpass.backend import Backend


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("hallpass-qt")
    app.setOrganizationName("hallpass")

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_path = Path(__file__).parent / "hallpass" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        print("Failed to load QML", file=sys.stderr)
        return 1

    # Fullscreen kiosk handled in QML ApplicationWindow.visibility
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
