import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from . import __version__
from .window import MainWindow


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--convert-worker":
        from .conversion import worker
        sys.exit(worker(Path(sys.argv[2]), Path(sys.argv[3])))
    if len(sys.argv) == 3 and sys.argv[1] in ("--verify-workspace", "--verify-workspace-native"):
        from .verify_workspace import verify
        sys.exit(verify(Path(sys.argv[2]), native=sys.argv[1] == "--verify-workspace-native"))
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-recovery-worker":
        from .verify_recovery import worker
        sys.exit(worker(Path(sys.argv[2])))
    if len(sys.argv) == 3 and sys.argv[1] in ("--verify-recovery", "--verify-recovery-native"):
        from .verify_recovery import verify
        sys.exit(verify(Path(sys.argv[2]), native=sys.argv[1] == "--verify-recovery-native"))
    if len(sys.argv) == 3 and sys.argv[1] in ("--verify-build", "--verify-build-native"):
        from .verify_build import verify
        sys.exit(verify(Path(sys.argv[2]), native=sys.argv[1] == "--verify-build-native"))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Paperlight")
    app.setOrganizationName("Paperlight")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "assets" / "paperlight.ico")))
    from .instance import InstanceServer
    from .workspace import Workspace
    from PySide6.QtWidgets import QMessageBox
    paths = [p for p in sys.argv[1:] if not p.startswith("--")]
    instance = InstanceServer()
    try:
        if not instance.start_or_forward(paths):
            return
    except Exception as exc:
        QMessageBox.warning(None, "Paperlight 실행", str(exc))
        return
    window = Workspace()
    instance.requested.connect(window.open_files)
    app.aboutToQuit.connect(instance.close)
    window.show()
    def start():
        window.current.offer_recovery(startup=True)
        if paths:
            window.open_files(paths)
        elif "--tray" in sys.argv and window.tray:
            window.hide_to_tray()
    QTimer.singleShot(0, start)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
