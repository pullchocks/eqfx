from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from eqfx.core.engine import Engine
from eqfx.ui.icons import application_icon
from eqfx.ui.main_window import MainWindow
from eqfx.ui.theme import apply_app_theme

_INSTANCE = "eqfx-session"


def _handoff() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(_INSTANCE)
    if not socket.waitForConnected(150):
        return False
    socket.write(b"raise")
    socket.waitForBytesWritten(150)
    socket.flush()
    socket.disconnectFromServer()
    return True


def _listen(app: QApplication, window: MainWindow) -> QLocalServer:
    QLocalServer.removeServer(_INSTANCE)
    server = QLocalServer(app)
    server.listen(_INSTANCE)

    def incoming() -> None:
        sock = server.nextPendingConnection()
        if sock:
            sock.readyRead.connect(window._show_from_tray)
    server.newConnection.connect(incoming)
    return server


def main(argv: list[str] | None = None) -> int:
    QGuiApplication.setDesktopFileName("eqfx")
    raw = list(argv if argv is not None else sys.argv)
    tray = "--tray" in raw or "--background" in raw
    filtered = [item for item in raw if item not in {"--tray", "--background"}]
    if not filtered:
        filtered = ["eqfx"]
    else:
        filtered[0] = "eqfx"
    sys.argv = list(filtered)
    app = QApplication(filtered)
    app.setApplicationName("eqfx")
    app.setApplicationDisplayName("eqFX")
    app.setOrganizationName("eqFX")
    app.setDesktopFileName("eqfx")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(application_icon())
    apply_app_theme(app)

    if _handoff():
        return 0

    engine = Engine()
    window = MainWindow(engine)
    _listen(app, window)
    engine.start()
    start_hidden = tray or engine.settings.start_in_tray
    if start_hidden and QSystemTrayIcon.isSystemTrayAvailable():
        window.hide()
        window.tray.show()
    else:
        window.show()
    code = app.exec()
    engine.shutdown()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
