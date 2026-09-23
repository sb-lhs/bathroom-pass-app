#!/usr/bin/env python3
"""hallpass-qt entry point."""
import sys
from pathlib import Path

# Ensure src on path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl

from hallpass.backend import Backend


class SplashStatus(QObject):
    statusChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "Starting…"

    @Property(str, notify=statusChanged)  # type: ignore
    def status(self) -> str:
        return self._status

    @Slot(str)
    def set(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()


def _pump(app: QGuiApplication, rounds: int = 4) -> None:
    import time
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("hallpass-qt")
    app.setOrganizationName("hallpass")

    engine = QQmlApplicationEngine()
    splash_state = SplashStatus()
    engine.rootContext().setContextProperty("splash", splash_state)

    qml_dir = Path(__file__).parent / "hallpass" / "qml"
    engine.load(QUrl.fromLocalFile(str(qml_dir / "Splash.qml")))
    if not engine.rootObjects():
        print("Failed to load splash", file=sys.stderr)
        return 1
    splash_root = engine.rootObjects()[0]
    _pump(app)

    splash_state.set("Loading settings…")
    _pump(app)
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    splash_state.set("Loading display…")
    _pump(app)
    engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))

    roots = [o for o in engine.rootObjects() if o is not splash_root]
    if not roots:
        print("Failed to load QML", file=sys.stderr)
        return 1
    try:
        splash_root.deleteLater()
    except Exception:
        pass
    _pump(app)

    # Fullscreen kiosk handled in QML ApplicationWindow.visibility
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
