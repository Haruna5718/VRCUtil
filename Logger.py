import logging
import queue
import threading
import sys
from logging.handlers import MemoryHandler

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QVBoxLayout, QWidget


log_buffer = MemoryHandler(capacity=5000)
logging.getLogger().addHandler(log_buffer)
_dispatcher = None

class QtLogHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]):
        super().__init__()
        self.log_queue = log_queue
        self._destroyed = False

    def emit(self, record):
        if self._destroyed:
            return
        self.log_queue.put(self.format(record))


class LogWindow(QWidget):
    def __init__(self, title: str, formatter: logging.Formatter, quit_on_close: bool = True):
        super().__init__()
        if not quit_on_close:
            self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle(title)
        self.resize(1600, 1000)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        self.text.setStyleSheet(
            """
            QPlainTextEdit {
                background: #000;
                color: #FFF;
                border: none;
                padding: 8px;
            }
            """
        )
        layout.addWidget(self.text)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.handler = QtLogHandler(self.log_queue)
        self.handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.handler)

        for record in log_buffer.buffer:
            self.text.appendPlainText(formatter.format(record))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.flush_logs)
        self.timer.start(100)

    def flush_logs(self):
        messages = []
        while True:
            try:
                messages.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        if not messages:
            return

        scrollbar = self.text.verticalScrollBar()
        should_follow = scrollbar.value() >= max(0, scrollbar.maximum() - 4)

        for message in messages:
            self.text.appendPlainText(message)

        if should_follow:
            scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        self.handler._destroyed = True
        logging.getLogger().removeHandler(self.handler)
        self.timer.stop()
        super().closeEvent(event)


class _LogWindowDispatcher(QObject):
    show_window = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.windows = []
        self.show_window.connect(self._create_window)

    def _create_window(self, title, formatter):
        window = LogWindow(title, formatter, quit_on_close=False)
        self.windows.append(window)
        window.destroyed.connect(lambda *_: self._discard_window(window))
        window.show()

    def _discard_window(self, window):
        if window in self.windows:
            self.windows.remove(window)


def open_log_window(title="Logger Window"):
    global _dispatcher
    base_formatter = None
    for handler in logging.getLogger().handlers:
        if handler.formatter:
            base_formatter = handler.formatter
            break
    base_formatter = base_formatter or logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    app = QApplication.instance()
    if app is not None:
        if _dispatcher is None:
            _dispatcher = _LogWindowDispatcher()
            _dispatcher.moveToThread(app.thread())
        _dispatcher.show_window.emit(title, base_formatter)
        return

    def qt_thread():
        qt_app = QApplication(sys.argv[:1])
        window = LogWindow(title, base_formatter)
        window.show()
        qt_app.exec()

    threading.Thread(target=qt_thread, daemon=True).start()
