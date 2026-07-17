import logging
import threading
import tkinter as tk
from collections import deque
from tkinter.scrolledtext import ScrolledText


class BoundedLogHandler(logging.Handler):
    def __init__(self, capacity=5000):
        super().__init__()
        self.buffer = deque(maxlen=capacity)

    def emit(self, record):
        self.buffer.append(record)

    def snapshot(self):
        self.acquire()
        try:
            return tuple(self.buffer)
        finally:
            self.release()


log_buffer = BoundedLogHandler()
logging.getLogger().addHandler(log_buffer)


class TkinterLogHandler(logging.Handler):
    def __init__(self, text_widget, max_lines=5000):
        super().__init__()
        self.text_widget = text_widget
        self.max_lines = max_lines
        self._destroyed = False

    def emit(self, record):
        if self._destroyed:
            return
        msg = self.format(record)
        try:
            self.text_widget.after(0, self._append, msg)
        except tk.TclError:
            self._destroyed = True

    def _append(self, msg):
        if self._destroyed:
            return
        try:
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END)
            line_count = int(self.text_widget.index("end-1c").split(".")[0])
            if line_count > self.max_lines:
                self.text_widget.delete("1.0", f"{line_count - self.max_lines + 1}.0")
        except tk.TclError:
            self._destroyed = True


def open_log_window(title="Logger Window"):
    def tk_thread():
        root = tk.Tk()
        root.title(title)
        root.geometry("1600x1000")

        text = ScrolledText(
            root,
            wrap="word",
            font=("Consolas", 8),
            bg="#000", fg="#FFF",
            insertbackground="white",
            padx=8, pady=8, borderwidth=0
        )
        text.pack(fill="both", expand=True)

        base_formatter = None
        for h in logging.getLogger().handlers:
            if h.formatter:
                base_formatter = h.formatter
                break
        base_formatter = base_formatter or logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        for record in log_buffer.snapshot():
            text.insert(tk.END, base_formatter.format(record) + "\n")

        handler = TkinterLogHandler(text)
        handler.setFormatter(base_formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        def on_close():
            handler._destroyed = True
            root_logger.removeHandler(handler)
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()

    threading.Thread(target=tk_thread, daemon=True).start()
