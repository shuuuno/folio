import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from . import __version__
from .window import MainWindow


def main():
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
    window = MainWindow()
    window.show()
    def start():
        if not window.offer_recovery(startup=True) and len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
            window.open_file(sys.argv[1])
    QTimer.singleShot(0, start)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
