"""같은 사용자 앱으로 파일 열기를 전달한다. 검증에서는 별도 이름을 쓴다."""
import hashlib
import json
import time
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QLockFile, QStandardPaths, QThread
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class InstanceServer(QObject):
    requested = Signal(list)

    def __init__(self, directory=None):
        super().__init__()
        self.directory = Path(directory or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        self.directory.mkdir(parents=True, exist_ok=True)
        self.name = "paperlight-" + hashlib.sha256(str(self.directory.resolve()).encode()).hexdigest()[:24]
        self.lock = QLockFile(str(self.directory / "instance.lock"))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self.accept)
        self.sockets = {}

    def start_or_forward(self, paths):
        if not self.lock.tryLock(0):
            socket = QLocalSocket()
            deadline = time.monotonic() + 20
            connected = False
            while time.monotonic() < deadline:
                socket.abort()
                socket.connectToServer(self.name)
                if socket.state() == QLocalSocket.LocalSocketState.ConnectedState or socket.waitForConnected(500):
                    connected = True
                    break
                QThread.msleep(100)
            if not connected:
                raise RuntimeError("실행 중인 Paperlight에 연결하지 못했습니다. 잠시 후 다시 열어 주세요.")
            socket.write(json.dumps([str(Path(p).resolve()) for p in paths]).encode() + b"\n")
            if socket.bytesToWrite() and not socket.waitForBytesWritten(3000):
                raise RuntimeError("열기 요청을 전달하지 못했습니다.")
            if not socket.bytesAvailable() and not socket.waitForReadyRead(20000):
                raise RuntimeError("열기 요청의 수신을 확인하지 못했습니다. 앱이 바쁘면 잠시 후 다시 시도하세요.")
            if bytes(socket.readAll()) != b"ok\n":
                raise RuntimeError("올바르지 않은 앱 응답입니다.")
            socket.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            self.lock.unlock()
            raise RuntimeError(self.server.errorString())
        return True

    def accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self.sockets[socket] = bytearray()
            socket.readyRead.connect(lambda s=socket: self.read(s))
            socket.disconnected.connect(lambda s=socket: self.release(s))
            self.read(socket)

    def read(self, socket):
        buffer = self.sockets.get(socket)
        if buffer is None:
            return
        buffer.extend(bytes(socket.readAll()))
        if len(buffer) > 1024 * 1024:
            socket.abort()
            return
        if b"\n" in buffer:
            try:
                paths = json.loads(bytes(buffer).split(b"\n", 1)[0])
                if isinstance(paths, list) and all(isinstance(p, str) for p in paths):
                    socket.write(b"ok\n")
                    socket.flush()
                    self.requested.emit(paths)
            except (ValueError, UnicodeError):
                pass
            socket.disconnectFromServer()

    def release(self, socket):
        self.sockets.pop(socket, None)
        socket.deleteLater()

    def close(self):
        self.server.close()
        self.lock.unlock()
